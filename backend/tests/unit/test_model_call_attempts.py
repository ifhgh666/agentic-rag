from types import SimpleNamespace
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
import time
import json
import pytest

from app.core.model_provider import OpenAICompatibleProvider
from app.core.legacy_schemas import QueryAnalysis
from app.core.model_call import CallContext, ModelCallRunner, input_tokens, CallSpec
from tests.unit.test_model_call_governance import active_context


class FormatRejected(Exception):
    status_code = 400


class Unauthorized(Exception):
    status_code = 401


def cloud_settings(settings):
    return settings.model_copy(update={"llm_provider": "openai_compatible", "llm_model": "scripted",
        "llm_base_url": "https://fake.invalid/v1", "llm_api_key": "synthetic-test-key"})


def reply(content='{"is_clear":true,"questions":["question"],"clarification_needed":""}'):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=[]))],
                           usage=SimpleNamespace(prompt_tokens=9, completion_tokens=4))


def test_adapter_rechecks_before_format_fallback_and_does_not_send_rejected_input(settings):
    client = Mock()
    client.chat.completions.create.side_effect = [FormatRejected("response_format unavailable"), reply()]
    provider = OpenAICompatibleProvider(cloud_settings(settings), client=client)
    admitted = []

    def guard(prepared):
        admitted.append(prepared)
        if len(admitted) == 2:
            raise ValueError("context_budget_exceeded")
        return 1.0

    try:
        provider.complete([{"role": "user", "content": "question"}], response_schema=QueryAnalysis, before_attempt=guard)
    except ValueError as exc:
        assert str(exc) == "context_budget_exceeded"
    assert client.chat.completions.create.call_count == 1
    assert len(admitted) == 2


@pytest.mark.parametrize("fallback", [False, True])
def test_strict_or_fallback_share_one_logical_call_and_preserve_usage(settings, fallback):
    settings = cloud_settings(settings).model_copy(update={"max_context_tokens": 12000, "model_context_window": 16000})
    client = Mock()
    client.chat.completions.create.side_effect = ([FormatRejected("response_format unsupported")] if fallback else []) + [reply()]
    context = active_context(settings)
    outcome = ModelCallRunner(settings, OpenAICompatibleProvider(settings, client=client)).invoke(
        CallSpec("query_analysis", [{"role": "user", "content": "question"}], response_schema=QueryAnalysis), context)
    assert outcome.outcome == "completed" and outcome.result.structured_output is not None
    assert context.budget.snapshot(context.request_id)["model_calls"] == 1
    assert len(outcome.record.attempts) == (2 if fallback else 1)
    assert client.chat.completions.create.call_count == len(outcome.record.attempts)
    assert outcome.record.input_tokens == 9 and outcome.record.output_tokens == 4
    assert outcome.record.usage_source == ("mixed" if fallback else "provider")
    assert outcome.record.input_tokens_estimate == outcome.record.attempts[-1].input_tokens_estimate
    if fallback:
        assert outcome.record.attempts[0].status == "format_rejected"
        assert "schema" not in str([attempt.__dict__ for attempt in outcome.record.attempts]).replace("json_schema", "")


def test_fallback_full_input_can_exceed_the_same_limit_that_admitted_strict(settings, tmp_path):
    prepared = []
    client = Mock()
    client.chat.completions.create.side_effect = [FormatRejected("response_format unsupported"), reply()]
    OpenAICompatibleProvider(cloud_settings(settings), client=client).complete(
        [{"role": "user", "content": "question"}], response_schema=QueryAnalysis,
        before_attempt=lambda value: (prepared.append(value) or 1.0))
    costs = [input_tokens(value.messages, value.tools, value.response_format) for value in prepared]
    assert costs[1] > costs[0]
    settings = cloud_settings(settings).model_copy(update={"max_context_tokens": costs[0], "model_context_window": 20000})
    client = Mock()
    client.chat.completions.create.side_effect = [FormatRejected("response_format unsupported"), reply()]
    context = active_context(settings)
    outcome = ModelCallRunner(settings, OpenAICompatibleProvider(settings, client=client)).invoke(
        CallSpec("query_analysis", [{"role": "user", "content": "question"}], response_schema=QueryAnalysis), context)
    assert outcome.reason == "context_budget_exceeded" and outcome.record.attempted
    assert client.chat.completions.create.call_count == 1
    assert outcome.record.input_tokens_estimate == costs[0]
    assert outcome.record.attempts[-1].input_tokens_estimate == costs[1]
    assert outcome.record.attempts[-1].status == "rejected"
    assert context.budget.snapshot(context.request_id)["model_calls"] == 1
    (tmp_path / "schema-boundary.json").write_text(json.dumps({"request_id": context.request_id,
        "strict_input_estimate": costs[0], "fallback_input_estimate": costs[1], "input_limit": costs[0],
        "actual_transport_sends": client.chat.completions.create.call_count,
        "logical_calls": context.budget.snapshot(context.request_id)["model_calls"],
        "outcome": outcome.outcome, "reason": outcome.reason}, indent=2), encoding="utf-8")


@pytest.mark.parametrize("error", [OSError("PRIVATE_TRANSPORT"), TimeoutError("PRIVATE_TIMEOUT"),
                                  Unauthorized("PRIVATE_AUTH response_format unsupported")])
def test_transport_and_timeout_errors_never_trigger_format_fallback(settings, error):
    client = Mock()
    client.chat.completions.create.side_effect = error
    context = active_context(settings)
    outcome = ModelCallRunner(settings, OpenAICompatibleProvider(cloud_settings(settings), client=client)).invoke(
        CallSpec("query_analysis", [{"role": "user", "content": "q"}], response_schema=QueryAnalysis), context)
    assert client.chat.completions.create.call_count == 1
    assert outcome.reason in ("model_unavailable", "timeout")
    assert "PRIVATE" not in str(outcome.record.to_trace())


def test_invalid_schema_reply_stays_raw_and_does_not_trigger_an_adapter_retry(settings):
    client = Mock()
    client.chat.completions.create.return_value = reply("FIRST_INVALID_SCHEMA_REPLY")
    outcome = ModelCallRunner(settings, OpenAICompatibleProvider(cloud_settings(settings), client=client)).invoke(
        CallSpec("query_analysis", [{"role": "user", "content": "q"}], response_schema=QueryAnalysis),
        active_context(settings))
    assert outcome.outcome == "completed" and outcome.result.structured_output is None
    assert outcome.result.content == outcome.record.to_trace()["candidate_content"] == "FIRST_INVALID_SCHEMA_REPLY"
    assert client.chat.completions.create.call_count == 1


def test_late_format_rejection_cannot_send_a_fallback_or_change_returned_record(settings):
    entered, release = Event(), Event()
    client = Mock()

    def first(**kwargs):
        entered.set()
        assert release.wait(5)
        raise FormatRejected("response_format unsupported")

    client.chat.completions.create.side_effect = first
    context = replace(active_context(settings), request_deadline=time.monotonic() + 0.05)
    with ThreadPoolExecutor(1) as executor:
        try:
            outcome = ModelCallRunner(settings, OpenAICompatibleProvider(cloud_settings(settings), client=client),
                                      executor=executor).invoke(
                CallSpec("query_analysis", [{"role": "user", "content": "q"}], response_schema=QueryAnalysis), context)
            assert entered.is_set() and outcome.reason == "timeout" and outcome.record.attempted
            frozen = outcome.record.to_trace()
            context.budget.finish(context.request_id)
            context.budget.start(context.request_id)
        finally:
            release.set()
    assert client.chat.completions.create.call_count == 1
    assert outcome.record.to_trace() == frozen
    assert context.budget.snapshot(context.request_id)["model_calls"] == 0


def test_ollama_schema_input_is_checked_before_fake_model_invoke(settings):
    from langchain_core.messages import AIMessage
    from app.core.model_provider import OllamaProvider
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "fake-local"})
    model = Mock()
    model.with_structured_output.return_value = model
    model.invoke.return_value = {"raw": AIMessage(content='{"is_clear":true,"questions":["q"],"clarification_needed":""}'), "parsed": None}
    prepared = []
    result = OllamaProvider(settings, model=model).complete([{"role": "user", "content": "q"}],
        response_schema=QueryAnalysis, before_attempt=lambda value: (prepared.append(value) or 1.0))
    assert model.invoke.call_count == 1 and prepared[0].response_format == QueryAnalysis.model_json_schema()
    assert result.provider == "ollama"


def test_ollama_slow_binding_cannot_send_after_the_outer_call_closes(settings):
    from app.core.model_provider import OllamaProvider
    entered, release = Event(), Event()
    settings = settings.model_copy(update={"ollama_model": "fake-local"})
    model = Mock()

    def bind(tools):
        entered.set()
        assert release.wait(5)
        return model

    model.bind_tools.side_effect = bind
    context = replace(active_context(settings), request_deadline=time.monotonic() + 0.05)
    with ThreadPoolExecutor(1) as executor:
        try:
            outcome = ModelCallRunner(settings, OllamaProvider(settings, model=model), executor=executor).invoke(
                CallSpec("orchestrator", [{"role": "user", "content": "q"}], tools=[{"type": "function"}]), context)
            assert entered.is_set() and outcome.reason == "timeout" and not outcome.record.attempted
        finally:
            release.set()
    model.invoke.assert_not_called()
