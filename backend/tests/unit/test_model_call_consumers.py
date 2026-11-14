"""All service purposes obey the same request constraints without real models."""
import json
import time
from threading import Event, Thread

import pytest

from app.core.conversation import PreparedQuery
from app.core.legacy_summary import summarize_conversation
from app.core.model_call import build_model_budget
from app.core.answering import AnswerGenerator
from app.core.model_provider import ModelResult
from app.core.query_analysis import QueryAnalyzer
from app.core.legacy_rag import ModelQueryGenerator
from tests.unit.test_v4_conversation_summary import history


PURPOSES = ("analysis", "generation", "rewrite", "summary")


class ConsumerProvider:
    def __init__(self, purpose, *, error=None):
        self.purpose, self.error = purpose, error
        self.calls = []

    def complete(self, messages, *, tools=None, response_schema=None):
        self.calls.append(messages)
        if self.error:
            raise self.error
        content = {
            "analysis": json.dumps({"is_clear": True, "questions": ["question"], "clarification_needed": ""}),
            "generation": "supported ordinary answer", "rewrite": "different retrieval query",
            "summary": json.dumps({"summary": "用户讨论 PX-200 阈值 16 A，仅为对话。"}, ensure_ascii=False),
        }[self.purpose]
        return ModelResult(content, "fake", "scripted-consumer", 20, 8)


def consumer_case(settings, purpose, *, fault="success"):
    local = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "synthetic",
        "max_context_tokens": 1 if fault == "capacity" else 16000, "model_context_window": 20000})
    budget = build_model_budget(local)
    if fault != "missing":
        budget.start("request", deadline=time.monotonic() - 1 if fault == "expired" else None)
    if fault == "exhausted":
        for _ in range(local.max_simple_llm_calls):
            assert budget.reserve("request", "orchestrator", preserve_answer_slot=False)
    provider = ConsumerProvider(purpose, error=OSError("PRIVATE_CONSUMER_ERROR") if fault == "provider_failed" else None)
    memory = history()

    def invoke():
        if purpose == "analysis":
            return QueryAnalyzer(local, provider, budget=budget).analyze(
                "question", PreparedQuery("", [], "question", True), request_id="request")
        if purpose == "generation":
            generator = AnswerGenerator(local, provider, budget)
            return generator.generate_with_result("question", "evidence", request_id="request")
        if purpose == "rewrite":
            return ModelQueryGenerator(local, provider, budget=budget).generate_with_result("question", [], request_id="request")
        return summarize_conversation(memory, "t", "request", local, budget, lambda: provider)

    return invoke, provider, budget, memory


@pytest.mark.parametrize("purpose", PURPOSES)
@pytest.mark.parametrize("fault", ["capacity", "missing", "expired", "exhausted"])
def test_all_consumers_reject_before_transport_and_leave_usage_unchanged(settings, purpose, fault):
    invoke, provider, budget, memory = consumer_case(settings, purpose, fault=fault)
    previous = memory.thread_state("t")
    before = budget.snapshot("request")["model_calls"]
    try:
        invoke()
    except RuntimeError:
        # Ordinary generation keeps its exception-shaped failure interface.
        assert purpose == "generation"
    assert not provider.calls
    assert budget.snapshot("request")["model_calls"] == before
    assert memory.thread_state("t") == previous


@pytest.mark.parametrize("purpose", PURPOSES)
@pytest.mark.parametrize("fault", ["success", "provider_failed"])
def test_consumer_success_or_provider_failure_has_one_logical_record(settings, purpose, fault):
    invoke, provider, budget, memory = consumer_case(settings, purpose, fault=fault)
    previous = memory.thread_state("t")
    try:
        value = invoke()
    except RuntimeError as exc:
        assert purpose == "generation" and fault == "provider_failed"
        assert "PRIVATE_CONSUMER_ERROR" not in str(exc)
        value = None
    assert len(provider.calls) == budget.snapshot("request")["model_calls"] == 1
    assert budget.exists("request"), "A consumer must not finish its borrowed request"
    if fault == "provider_failed":
        assert memory.thread_state("t") == previous
        if purpose == "analysis":
            assert value.failure_reason == "model_unavailable"
        elif purpose == "summary":
            assert value["status"] == "deferred"
        elif purpose == "rewrite":
            assert value[0] == ""
    elif purpose == "analysis":
        assert value.is_clear and value.questions == ["question"]
        assert value.model_trace["attempted"] is True
    elif purpose == "summary":
        assert value["status"] == "completed" and not memory.thread_state("t").summary_backlog
    else:
        assert value[0] and value[1]["attempted"] is True
        assert "input_messages" not in value[1] and "candidate_content" not in value[1]


@pytest.mark.parametrize("purpose", ["analysis", "rewrite"])
def test_cache_hit_does_not_enter_runner_or_spend_a_call(settings, purpose):
    from app.core.model_call import BoundedCache
    from app.core.legacy_cache import RequestToolCache
    provider = ConsumerProvider(purpose)
    budget = build_model_budget(settings)
    budget.start("request")
    cache = BoundedCache()
    hits = RequestToolCache()
    if purpose == "analysis":
        service = QueryAnalyzer(settings, provider, budget=budget, cache=cache, index_version=lambda: "v1", request_cache=hits)
        invoke = lambda: service.analyze("question", PreparedQuery("", [], "question", True), request_id="request", thread_id="t")
    else:
        service = ModelQueryGenerator(settings, provider, budget=budget, cache=cache, index_version=lambda: "v1", request_cache=hits)
        invoke = lambda: service.generate_with_result("question", [], request_id="request", thread_id="t")
    first, second = invoke(), invoke()
    assert len(provider.calls) == budget.snapshot("request")["model_calls"] == 1
    assert hits.stats("request")["query_analysis" if purpose == "analysis" else "query_rewrite"] == 1
    if purpose == "analysis":
        assert first.source == "model" and second.source == "cache" and second.model_trace is None
    else:
        assert first[0] == second[0] and second[1] is None


def invoke_consumer(settings, purpose, provider, budget, memory, **scope):
    if purpose == "analysis":
        return QueryAnalyzer(settings, provider, budget=budget).analyze("question", PreparedQuery("", [], "question", True), **scope)
    if purpose == "generation":
        return AnswerGenerator(settings, provider, budget).generate_with_result("question", "evidence", **scope)
    if purpose == "rewrite":
        return ModelQueryGenerator(settings, provider, budget=budget).generate_with_result("question", [], **scope)
    return summarize_conversation(memory, "t", scope.pop("request_id", ""), settings, budget, lambda: provider, **scope)


def trace_of(purpose, value):
    return value.model_trace if purpose == "analysis" else value if purpose == "summary" else value[1]


@pytest.mark.parametrize("purpose", PURPOSES)
def test_absent_scope_creates_one_owned_operation_and_finishes_it(settings, purpose):
    settings = settings.model_copy(update={"llm_provider": "ollama", "model_context_window": 20000, "max_context_tokens": 16000})
    budget = build_model_budget(settings)
    provider = ConsumerProvider(purpose)
    result = invoke_consumer(settings, purpose, provider, budget, history())
    trace = trace_of(purpose, result)
    assert trace["request_id"] and trace["attempted"] and len(provider.calls) == 1
    assert not budget.exists(trace["request_id"])


@pytest.mark.parametrize("purpose", PURPOSES)
@pytest.mark.parametrize("reuse", [False, True])
def test_supplied_ended_context_cannot_become_a_new_operation(settings, purpose, reuse):
    from app.core.model_call import CallContext
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    budget = build_model_budget(settings)
    budget.start("request")
    context = CallContext.shared(budget, "request")
    budget.finish("request")
    if reuse:
        budget.start("request")
    provider = ConsumerProvider(purpose)
    memory = history()
    previous = memory.thread_state("t")
    try:
        invoke_consumer(settings, purpose, provider, budget, memory, call_context=context)
    except RuntimeError:
        assert purpose == "generation"
    assert not provider.calls and budget.snapshot("request")["model_calls"] == 0
    assert budget.exists("request") is reuse and memory.thread_state("t") == previous


@pytest.mark.parametrize("purpose", PURPOSES)
def test_timeout_late_reply_cannot_publish_a_candidate_or_change_summary(settings, purpose):
    settings = settings.model_copy(update={"llm_provider": "ollama", "llm_timeout_seconds": 0.1})
    entered, release, finished = Event(), Event(), Event()

    class Blocked(ConsumerProvider):
        def complete(self, messages, *, tools=None, response_schema=None):
            entered.set()
            try:
                assert release.wait(5)
                return super().complete(messages, tools=tools, response_schema=response_schema)
            finally:
                finished.set()

    budget = build_model_budget(settings)
    budget.start("request")
    provider, memory = Blocked(purpose), history()
    previous = memory.thread_state("t")
    try:
        try:
            result = invoke_consumer(settings, purpose, provider, budget, memory, request_id="request")
        except RuntimeError as exc:
            assert purpose == "generation" and "timeout" in str(exc)
            result = None
        assert entered.is_set() and not release.is_set()
        assert memory.thread_state("t") == previous
        assert budget.snapshot("request")["model_calls"] == 1
        if purpose == "analysis":
            assert result.failure_reason == "timeout" and not result.questions
        elif purpose == "summary":
            assert result["status"] == "deferred" and result["failure_reason"] == "timeout"
        elif purpose == "rewrite":
            assert result[0] == ""
        frozen = repr(result)
        budget.finish("request")
    finally:
        release.set()
    assert finished.wait(2)
    assert memory.thread_state("t") == previous and repr(result) == frozen


def test_summary_version_conflict_keeps_the_original_backlog(settings):
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    memory = history()
    before = memory.thread_state("t")
    entered, release = Event(), Event()

    class Concurrent(ConsumerProvider):
        def complete(self, messages, *, tools=None, response_schema=None):
            entered.set()
            assert release.wait(5)
            return super().complete(messages, tools=tools, response_schema=response_schema)

    def update_history():
        if entered.wait(3):
            memory.set_pending("t", "new pending question")
        release.set()

    updater = Thread(target=update_history)
    updater.start()
    try:
        trace = summarize_conversation(memory, "t", "", settings, None, lambda: Concurrent("summary"))
        assert trace["status"] == "deferred"
        after = memory.thread_state("t")
        assert after.summary_backlog == before.summary_backlog and after.conversation_summary == before.conversation_summary
        assert after.pending_query == "new pending question"
    finally:
        release.set()
        updater.join(2)


def test_reference_request_does_not_claim_a_legacy_budget_operation(settings):
    from tests.fakes.reference_helpers import make_service, run_turn
    budget = build_model_budget(settings)
    budget.start("legacy")
    before = budget.snapshot("legacy")
    service, model, _ = make_service(settings)
    final, _ = run_turn(service)
    assert not final["pending"] and len(model.calls) == 5
    assert budget.snapshot("legacy") == before

def test_checkpoint_threads_do_not_share_another_requests_history(settings):
    from tests.fakes.reference_helpers import make_service, run_turn, conversation
    service, model, _ = make_service(settings)
    run_turn(service, "first-private-thread", thread="one")
    run_turn(service, "second-thread", thread="two")
    assert all("first-private-thread" not in str(m.content) for m in conversation(service, "two"))
    assert any(m.content == "first-private-thread" for m in conversation(service, "one"))
