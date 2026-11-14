"""Structured entrance checks use real wrappers with fake transports, never inference."""
import json
from threading import Event
from unittest.mock import Mock

import pytest
from langchain_ollama import ChatOllama
from ollama import ChatResponse, Message
from jsonschema import Draft202012Validator
from app.core.conversation import PreparedQuery
from app.core.model_call import BoundedCache, ModelCallBudget
from app.core.model_provider import (
    ModelResult,
    OllamaProvider,
    OpenAICompatibleProvider,
    complete_model,
)
from app.core.legacy_schemas import QueryAnalysis
from app.core.legacy_prompts import get_rewrite_query_prompt
from app.core.query_analysis import QueryAnalyzer
from tests.fakes.providers import ScriptedQueryProvider, query_analysis_payload


def prepared():
    return PreparedQuery("", [], "unused", True)


def transport_provider(settings, payload):
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "local-test"})
    content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    client = Mock()
    client.chat.return_value = iter([ChatResponse(
        model="local-test", message=Message(role="assistant", content=content), done=True,
        prompt_eval_count=34, eval_count=12,
    )])
    model = ChatOllama(model="local-test", reasoning=False)
    model._client = client
    return OllamaProvider(settings, model=model), client, content


@pytest.mark.parametrize("payload", [
    query_analysis_payload(["PX-200 的阈值是多少？"]),
    query_analysis_payload([], clear=False, clarification="请说明‘它’指哪个设备。"),
])
def test_real_langchain_wrapper_sends_schema_and_returns_fields_with_raw_usage(settings, payload):
    provider, client, raw = transport_provider(settings, payload)
    messages = [{"role": "system", "content": get_rewrite_query_prompt()}, {"role": "user", "content": "问题？"}]
    result = complete_model(provider, messages, response_schema=QueryAnalysis, timeout_seconds=1)

    sent = client.chat.call_args.kwargs
    assert sent["format"] == QueryAnalysis.model_json_schema()
    assert sent["format"]["additionalProperties"] is False
    assert sent["format"]["properties"]["questions"]["maxItems"] == 3
    # The transmitted schema itself must constrain state, even if a provider
    # does not run Pydantic's custom model validators during generation.
    schema_validator = Draft202012Validator(sent["format"])
    assert schema_validator.is_valid(payload)
    assert not schema_validator.is_valid(query_analysis_payload(["问题？"], clarification="无"))
    assert not schema_validator.is_valid(query_analysis_payload([], clear=False))
    assert sent["messages"][0]["content"] == get_rewrite_query_prompt()
    assert isinstance(result.structured_output, QueryAnalysis)
    assert result.structured_output.model_dump() == payload
    assert result.content == raw
    assert (result.prompt_tokens, result.completion_tokens) == (34, 12)
    assert client.chat.call_count == 1


def test_query_analyzer_uses_schema_separately_from_business_prompt(settings):
    provider, client, raw = transport_provider(settings, query_analysis_payload(["PX-200 的阈值？"]))
    result = QueryAnalyzer(provider.settings, provider).analyze("PX-200 的阈值？", prepared())
    assert result.is_clear and result.questions == ["PX-200 的阈值？"]
    assert result.model_trace["candidate_content"] == raw
    assert result.model_trace["input_tokens"] == 34
    assert client.chat.call_args.kwargs["format"] == QueryAnalysis.model_json_schema()
    prompt = client.chat.call_args.kwargs["messages"][0]["content"]
    assert prompt == get_rewrite_query_prompt()
    assert all(word not in prompt for word in ("JSON", "is_clear", "questions", "clarification_needed"))
    assert all(field["description"] for field in QueryAnalysis.model_json_schema()["properties"].values())


@pytest.mark.parametrize("payload", [
    "not JSON", {}, query_analysis_payload(["A", "B", "C", "D"]),
    {**query_analysis_payload(["A"]), "is_clear": "true"},
    {**query_analysis_payload(["A"]), "clarification_needed": None},
    {**query_analysis_payload(["A"]), "unexpected": 1},
    query_analysis_payload([], clear=True),
    query_analysis_payload(["A"], clear=False, clarification="请补充所指对象"),
])
def test_nonconforming_transport_output_fails_once_and_retains_first_output(settings, payload):
    provider, client, raw = transport_provider(settings, payload)
    result = QueryAnalyzer(provider.settings, provider).analyze("问题？", prepared())
    assert not result.is_clear and result.failure_reason == "invalid_model_output"
    assert result.model_trace["candidate_content"] == raw
    assert result.questions == [] and client.chat.call_count == 1


def test_rejected_binding_never_invokes_plain_model_or_cloud(settings, monkeypatch):
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "local-test"})
    model = Mock()
    model.with_structured_output.side_effect = ValueError("private unsupported schema")
    monkeypatch.setattr("app.core.model_provider.OpenAICompatibleProvider", lambda *_: pytest.fail("cloud fallback"))
    outcome = QueryAnalyzer(settings, OllamaProvider(settings, model=model)).analyze("问题？", prepared())
    assert outcome.failure_reason == "model_unavailable"
    model.with_structured_output.assert_called_once_with(QueryAnalysis, method="json_schema", include_raw=True)
    model.invoke.assert_not_called()
    assert "private" not in repr(outcome)


def test_provider_without_schema_parameter_is_not_silently_called_plain(settings):
    class PlainOnly:
        def complete(self, messages):
            pytest.fail("a schema request must never use a plain-only provider")
    outcome = QueryAnalyzer(settings, PlainOnly()).analyze("问题？", prepared())
    assert outcome.failure_reason == "model_unavailable" and not outcome.is_clear


def test_schema_is_sent_to_explicit_compatible_api(settings):
    from types import SimpleNamespace
    settings = settings.model_copy(update={"llm_provider": "openai_compatible", "llm_base_url": "https://cloud.example/v1",
                                           "llm_api_key": "test-only", "llm_model": "mock-model"})
    payload = query_analysis_payload(["问题？"])
    raw = json.dumps(payload, ensure_ascii=False)
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=raw, tool_calls=[]))],
        usage=SimpleNamespace(prompt_tokens=9, completion_tokens=4),
    )
    result = complete_model(OpenAICompatibleProvider(settings, client), [{"role": "user", "content": "问题？"}],
                            response_schema=QueryAnalysis, timeout_seconds=1)
    assert client.chat.completions.create.call_args.kwargs["response_format"] == {
        "type": "json_schema", "json_schema": {"name": "QueryAnalysis", "schema": QueryAnalysis.model_json_schema(), "strict": True}}
    assert result.structured_output.model_dump() == payload and result.content == raw
    assert (result.prompt_tokens, result.completion_tokens) == (9, 4)
    assert client.chat.completions.create.call_count == 1


def test_compatible_rejection_is_one_call_without_downgrade(settings):
    settings = settings.model_copy(update={"llm_provider": "openai_compatible", "llm_base_url": "https://cloud.example/v1",
                                           "llm_api_key": "test-only", "llm_model": "mock-model"})
    client = Mock()
    client.chat.completions.create.side_effect = ValueError("private unsupported format")
    result = QueryAnalyzer(settings, OpenAICompatibleProvider(settings, client)).analyze("问题？", prepared())
    assert result.failure_reason == "model_unavailable" and client.chat.completions.create.call_count == 1
    assert "private" not in repr(result)


def test_structured_call_cannot_mix_entrance_schema_with_retrieval_tools(settings):
    provider, client, _ = transport_provider(settings, query_analysis_payload(["问题？"]))
    with pytest.raises(ValueError):
        complete_model(provider, [], tools=[{"type": "function"}], response_schema=QueryAnalysis)
    client.chat.assert_not_called()


def test_late_structured_result_obeys_whole_wait_and_is_not_cached(settings):
    release, finished = Event(), Event()
    class DelayedProvider:
        def __init__(self):
            self.schemas = []
        def complete(self, messages, *, response_schema=None, timeout_seconds=None):
            self.schemas.append(response_schema)
            try:
                release.wait(1)
                return ModelResult(json.dumps(query_analysis_payload(["问题？"])), "fake", "delayed")
            finally:
                finished.set()
    provider = DelayedProvider()
    settings = settings.model_copy(update={"llm_timeout_seconds": 0.02})
    cache = BoundedCache()
    analyzer = QueryAnalyzer(settings, provider, cache=cache, index_version=lambda: "v1")
    try:
        result = analyzer.analyze("问题？", prepared(), thread_id="late")
        assert result.failure_reason == "timeout" and result.questions == []
    finally:
        release.set()
    assert finished.wait(1) and provider.schemas == [QueryAnalysis]
    next_result = analyzer.analyze("问题？", prepared(), thread_id="late")
    assert next_result.is_clear and next_result.source == "model"
    assert provider.schemas == [QueryAnalysis, QueryAnalysis]


def test_schema_and_prompt_versions_isolate_cached_entrance_results(settings, monkeypatch):
    provider = ScriptedQueryProvider(*[query_analysis_payload(["问题？"])] * 3)
    analyzer = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: "v1")
    assert analyzer.analyze("问题？", prepared(), thread_id="t").source == "model"
    assert analyzer.analyze("问题？", prepared(), thread_id="t").source == "cache"
    monkeypatch.setattr("app.core.query_analysis.REWRITE_PROMPT_VERSION", "test-next")
    assert analyzer.analyze("问题？", prepared(), thread_id="t").source == "model"
    original_schema = QueryAnalysis.model_json_schema
    monkeypatch.setattr(QueryAnalysis, "model_json_schema", classmethod(lambda cls: {**original_schema(), "title": "ChangedQueryAnalysis"}))
    assert analyzer.analyze("问题？", prepared(), thread_id="t").source == "model"
    assert len(provider.calls) == 3


def test_schema_counts_toward_window_before_any_provider_call(settings, monkeypatch):
    monkeypatch.setattr("app.core.query_analysis.get_rewrite_query_prompt", lambda: "保留原句")
    settings = settings.model_copy(update={"max_context_tokens": 300, "model_context_window": 300,
                                           "llm_max_output_tokens": 16, "model_context_safety_tokens": 0})
    provider = ScriptedQueryProvider(query_analysis_payload(["问题？"]))
    result = QueryAnalyzer(settings, provider).analyze("问题？", prepared())
    assert result.failure_reason == "context_budget_exceeded" and provider.calls == []


def test_structured_entrance_still_reserves_only_one_model_call(settings):
    provider = ScriptedQueryProvider(query_analysis_payload(["问题？"]))
    budget = ModelCallBudget(1, 1, {"query_analysis": 1})
    budget.start("r")
    result = QueryAnalyzer(settings, provider, budget=budget).analyze("问题？", prepared(), request_id="r")
    assert result.is_clear and len(provider.calls) == 1
    assert budget.finish("r")["model_calls"] == 1
