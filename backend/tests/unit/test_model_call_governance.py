"""Model-call constraints observed through the graph and the shared interface."""
from tests.fakes.providers import ScriptedModel
from app.core.model_call import (
    CallContext,
    ModelCallRunner,
    input_tokens,
    CallSpec,
    build_model_budget,
    summarize_usage,
)
from app.core.model_provider import ModelResult
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from dataclasses import FrozenInstanceError


def active_context(settings, *, branch_id=None):
    budget = build_model_budget(settings)
    budget.start("request")
    return CallContext.shared(budget, "request", branch_id=branch_id)


@pytest.mark.parametrize("fault", ["capacity", "expired", "finished", "exhausted", "lease_reused"])
def test_rejected_call_does_not_send_or_add_usage(settings, fault):
    context = active_context(settings)
    provider = ScriptedModel(ModelResult("ok", "fake", "scripted"))
    messages = [{"role": "user", "content": "question"}]
    reason = "budget_exceeded"
    if fault == "capacity":
        messages[0]["content"] = "x" * 30_000
        reason = "context_budget_exceeded"
    elif fault == "expired":
        from dataclasses import replace
        context = replace(context, request_deadline=time.monotonic() - 1)
        reason = "timeout"
    elif fault == "finished":
        context.budget.finish(context.request_id)
    elif fault == "lease_reused":
        context.budget.finish(context.request_id)
        context.budget.start(context.request_id)
    else:
        for _ in range(settings.max_simple_llm_calls):
            assert context.budget.reserve(context.request_id, "orchestrator", preserve_answer_slot=False)
    before = context.budget.snapshot(context.request_id)["model_calls"]
    outcome = ModelCallRunner(settings, provider).invoke(CallSpec("orchestrator", messages), context)
    assert outcome.result is None and outcome.reason == reason
    assert not outcome.record.attempted and not provider.calls
    assert context.budget.snapshot(context.request_id)["model_calls"] == before
    usage = summarize_usage([outcome.record.to_trace()], {}, {}, 0)
    assert usage["total_tokens"] == usage["model_calls"] == 0


def test_legacy_provider_failure_is_charged_once_and_exception_text_is_private(settings):
    class Broken:
        def complete(self, messages, *, tools=None):
            raise OSError("PRIVATE_PROMPT sk-synthetic /private/data")

    context = active_context(settings)
    outcome = ModelCallRunner(settings, Broken()).invoke(CallSpec("orchestrator", [{"role": "user", "content": "q"}]), context)
    assert outcome.outcome == "failed" and outcome.reason == "model_unavailable"
    assert outcome.record.attempted and outcome.record.input_tokens is None
    assert context.budget.snapshot(context.request_id)["model_calls"] == 1
    assert "PRIVATE_PROMPT" not in str(outcome.record.to_trace())


def test_success_preserves_first_raw_reply_without_business_repair(settings):
    context = active_context(settings)
    provider = ScriptedModel(ModelResult("invalid first reply", "fake", "script", 12, 3))
    messages = [{"role": "user", "content": "question"}]
    outcome = ModelCallRunner(settings, provider).invoke(CallSpec("collect_answer", messages), context)
    assert outcome.outcome == "completed" and outcome.result.content == "invalid first reply"
    assert len(provider.calls) == 1 and outcome.record.input_tokens_estimate == input_tokens(messages)
    assert outcome.record.input_tokens == 12 and outcome.record.output_tokens == 3
    with pytest.raises(FrozenInstanceError):
        outcome.reason = "mutated"


def test_queued_call_expires_without_ever_getting_send_permission(settings):
    from dataclasses import replace
    occupied, release = Event(), Event()
    context = replace(active_context(settings), request_deadline=time.monotonic() + 0.05)
    provider = ScriptedModel(ModelResult("late", "fake", "script"))
    with ThreadPoolExecutor(max_workers=1) as executor:
        blocker = executor.submit(lambda: (occupied.set(), release.wait(5)))
        assert occupied.wait(1)
        try:
            outcome = ModelCallRunner(settings, provider, executor=executor).invoke(
                CallSpec("orchestrator", [{"role": "user", "content": "q"}]), context)
            assert outcome.reason == "timeout" and not outcome.record.attempted
            frozen = outcome.record.to_trace()
        finally:
            release.set()
        blocker.result()
    assert not provider.calls and outcome.record.to_trace() == frozen
    assert context.budget.snapshot(context.request_id)["model_calls"] == 0


def test_closed_guard_denies_late_adapter_send_and_does_not_mutate_outcome(settings):
    from dataclasses import replace
    from app.core.model_provider import PreparedAttempt
    entered, release, finished = Event(), Event(), Event()
    sent = []

    class DelayedPreparation:
        def complete(self, messages, *, before_attempt=None):
            entered.set()
            assert release.wait(5)
            try:
                before_attempt(PreparedAttempt(messages))
                sent.append(True)
                return ModelResult("late", "fake", "late")
            finally:
                finished.set()

    context = replace(active_context(settings), request_deadline=time.monotonic() + 0.05)
    try:
        outcome = ModelCallRunner(settings, DelayedPreparation()).invoke(
            CallSpec("orchestrator", [{"role": "user", "content": "q"}]), context)
        assert entered.is_set() and outcome.reason == "timeout" and not outcome.record.attempted
        frozen = outcome.record.to_trace()
        context.budget.finish(context.request_id)
        context.budget.start(context.request_id)
    finally:
        release.set()
    assert finished.wait(2)
    assert not sent and outcome.record.to_trace() == frozen
    assert context.budget.snapshot(context.request_id)["model_calls"] == 0


def test_parallel_first_reservations_are_atomic_and_keep_branch_slots(settings):
    context = active_context(settings, branch_id="B1")
    context.budget.configure_branches(context.request_id, 3)
    provider = ScriptedModel(*[ModelResult("ok", "fake", "script") for _ in range(20)])
    spec = CallSpec("orchestrator", [{"role": "user", "content": "q"}])
    with ThreadPoolExecutor(10) as pool:
        outcomes = list(pool.map(lambda _: ModelCallRunner(settings, provider).invoke(spec, context), range(20)))
    assert sum(item.record.attempted for item in outcomes) == len(provider.calls) == 3
    assert context.budget.branch_remaining(context.request_id, "B2") == 3
    assert context.budget.reserve(context.request_id, "final_synthesis")


def test_old_lease_cannot_release_or_spend_the_replacement_requests_slots(settings):
    context = active_context(settings, branch_id="B1")
    context.budget.finish(context.request_id)
    context.budget.start(context.request_id)
    context.budget.configure_branches(context.request_id, 3)
    before = context.budget.snapshot(context.request_id)
    context.budget.release_branch(context.request_id, "B1", lease_id=context.lease_id)
    assert not context.budget.reserve_tool(context.request_id, "B1", lease_id=context.lease_id)
    context.budget.finish(context.request_id, lease_id=context.lease_id)
    after = context.budget.snapshot(context.request_id)
    assert after == before and context.budget.branch_remaining(context.request_id, "B1") == 3


def test_grounded_repair_shares_one_owned_operation_and_retains_the_first_reply(settings):
    from app.core.answering import AnswerGenerator
    from tests.unit.test_prompt_consumers import evidence, terminal
    provider = ScriptedModel(ModelResult("FIRST_INVALID_REPLY", "fake", "script"), ModelResult(terminal(), "fake", "script"))
    budget = build_model_budget(settings)
    answer, ids, trace = AnswerGenerator(settings, provider, budget).generate_grounded_with_result("question", evidence())
    assert ids == ["E1"] and len(provider.calls) == 2
    assert trace["candidate_content"] == "FIRST_INVALID_REPLY"
    repair = trace["repair_calls"][0]
    assert trace["request_id"] == repair["request_id"] and trace["model_call_id"] != repair["model_call_id"]
    assert trace["node"] == "collect_answer" and repair["node"] == "answer_repair"
    assert not budget.exists(trace["request_id"])


def test_explicit_inactive_synthesis_request_is_rejected_without_creating_a_new_owner(settings):
    from app.core.answering import AnswerGenerator
    from tests.unit.test_prompt_consumers import evidence, terminal
    provider = ScriptedModel(ModelResult(terminal(), "fake", "script"))
    budget = build_model_budget(settings)
    result = AnswerGenerator(settings, provider, budget).synthesize_branch_answers("q", [], evidence(), "inactive")
    assert result[3:] == ("failed", "timeout")
    assert not provider.calls and not budget.exists("inactive")


def test_optional_summary_rejection_does_not_take_the_answer_slot(settings):
    context = active_context(settings)
    assert context.budget.reserve(context.request_id, "query_analysis")
    context.budget.configure_branches(context.request_id, 3)
    provider = ScriptedModel(ModelResult("summary", "fake", "script"))
    outcome = ModelCallRunner(settings, provider).invoke(CallSpec("conversation_summary", [{"role": "user", "content": "q"}]), context)
    assert outcome.outcome == "skipped" and not outcome.record.attempted
    assert not provider.calls and not context.budget.snapshot(context.request_id)["budget_exceeded"]


def test_tools_and_schema_cannot_mix(settings):
    from app.core.legacy_schemas import QueryAnalysis
    with pytest.raises(ValueError, match="cannot_mix"):
        ModelCallRunner(settings, ScriptedModel()).invoke(CallSpec("orchestrator", [],
            tools=[{"type": "function"}], response_schema=QueryAnalysis), active_context(settings))


def test_native_observations_retain_input_estimates_without_admission(settings):
    from app.core.reference_observation import RequestObservation
    from app.rag.tools import estimate_context_tokens
    from tests.fakes.reference_helpers import make_service, run_turn
    service, model, _ = make_service(settings)
    observation = RequestObservation(settings)
    run_turn(service, callbacks=[observation])
    assert len(observation.model_trace) == len(model.calls) == 5
    for trace, sent in zip(observation.model_trace, model.calls):
        assert trace["input_tokens"] == estimate_context_tokens(sent["messages"])
        assert "input_messages" not in trace and "tool_definitions" not in trace
    assert observation.usage()["model_call_limit"] is None
