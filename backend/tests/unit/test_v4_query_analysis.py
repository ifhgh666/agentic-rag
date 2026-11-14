import json

import pytest

from app.core.conversation import PreparedQuery
from app.core.model_call import BoundedCache, ModelCallBudget
from app.core.model_provider import ModelResult
from app.core.query_analysis import QueryAnalyzer


class StubProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete(self, messages, *, tools=None, response_schema=None):
        self.calls.append(messages)
        if isinstance(self.payload, Exception):
            raise self.payload
        content = json.dumps(self.payload, ensure_ascii=False) if isinstance(self.payload, dict) else self.payload
        return ModelResult(content, "ollama", "stub", 20, 8)


def prepared(history=None, summary=""):
    return PreparedQuery(summary, history or [], "legacy rewrite must be ignored", False)


def decision(questions, *, clear=True, clarification=""):
    return {
        "is_clear": clear,
        "questions": questions, "clarification_needed": clarification,
    }


def test_clear_standalone_query_keeps_original_text_and_conditions(settings):
    question = "PX-200 的过流阈值是多少？"
    provider = StubProvider(decision([question]))
    outcome = QueryAnalyzer(settings, provider).analyze(question, prepared(), thread_id="t")
    assert outcome.is_clear and outcome.questions == [question]
    assert question in outcome.model_trace["original_conditions"]
    assert outcome.source == "model" and len(provider.calls) == 1
    assert provider.calls[0][-1]["content"].find(question) >= 0
    assert "legacy rewrite" not in provider.calls[0][-1]["content"]


def test_reference_uses_history_in_single_model_call(settings):
    provider = StubProvider(decision(["PX-200 多久维护一次？"]))
    history = [{"role": "user", "content": "PX-200 的参数是什么？"}]
    outcome = QueryAnalyzer(settings, provider).analyze("它多久维护一次？", prepared(history))
    assert outcome.questions == ["PX-200 多久维护一次？"]
    assert len(provider.calls) == 1
    assert "PX-200" in provider.calls[0][-1]["content"]


def test_context_prompt_limits_history_and_preserves_unconfirmed_conditions(settings):
    question = "那恢复条件呢？"
    provider = StubProvider(decision(["如果触发保护，PX-200 的恢复条件是什么？"]))
    outcome = QueryAnalyzer(settings, provider).analyze(question, prepared([
        {"role": "user", "content": "PX-200 输入电压为 245 V，持续 400 ms，是否触发保护？"},
    ]))
    assert outcome.is_clear
    system_prompt = provider.calls[0][0]["content"]
    assert "只使用必要历史" in system_prompt
    assert "当前原题和已确认补充优先于旧历史" in system_prompt
    assert "不把假设写成已发生" in system_prompt


def test_two_questions_are_kept_separate(settings):
    provider = StubProvider(decision(["PX-200 的过流阈值是多少？", "PX-200 的记录保留多久？"]))
    question = "PX-200 的过流阈值是多少，以及记录保留多久？"
    outcome = QueryAnalyzer(settings, provider).analyze(question, prepared())
    assert len(outcome.questions) == 2 and outcome.is_clear
    assert len(provider.calls) == 1


@pytest.mark.parametrize("payload", [
    "not-json", "{}", decision(["A?", "B?", "C?", "D?"]),
    decision(["重复问题？", "重复问题？"]),
    {**decision(["请分析这两个问题"]), "failure_reason": "model_failed"},
])
def test_invalid_or_out_of_bounds_output_never_becomes_clear(settings, payload):
    outcome = QueryAnalyzer(settings, StubProvider(payload)).analyze("请分析这两个问题", prepared())
    assert not outcome.is_clear and outcome.questions == []
    assert outcome.failure_reason == "invalid_model_output"


def test_model_exception_is_reported_without_inventing_answer(settings):
    outcome = QueryAnalyzer(settings, StubProvider(TimeoutError("secret timeout"))).analyze("PX-200 的阈值？", prepared())
    assert not outcome.is_clear and outcome.questions == []
    assert outcome.failure_reason == "timeout"
    assert "secret" not in str(outcome)


def test_invalid_semantics_are_not_hidden_by_a_new_entrance_guard(settings):
    question = "PX-200 在低于 16 A 时是否不能恢复？"
    provider = StubProvider(decision(["PX-300 在高于 20 A 时如何恢复？"]))
    outcome = QueryAnalyzer(settings, provider).analyze(question, prepared())
    assert outcome.is_clear and outcome.failure_reason is None
    assert outcome.model_trace["original_conditions"] == question
    # The scripted semantic error is deliberately admitted by the protocol;
    # this test cannot establish numerical or negative-condition correctness.


def test_cache_is_scoped_to_history_and_index(settings):
    provider = StubProvider(decision(["PX-200 的阈值是多少？"]))
    version = ["v1"]
    analyzer = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: version[0])
    question = "PX-200 的阈值是多少？"
    analyzer.analyze(question, prepared(), thread_id="t")
    cached = analyzer.analyze(question, prepared(), thread_id="t")
    assert cached.source == "cache" and len(provider.calls) == 1
    analyzer.analyze(question, prepared(summary="old topic"), thread_id="t")
    version[0] = "v2"
    analyzer.analyze(question, prepared(), thread_id="t")
    assert len(provider.calls) == 3


def test_budget_exhaustion_is_not_treated_as_success(settings):
    budget = ModelCallBudget(0, 0, {"query_analysis": 0})
    budget.start("r")
    outcome = QueryAnalyzer(settings, StubProvider(decision(["PX-200 的阈值？"])), budget=budget).analyze(
        "PX-200 的阈值？", prepared(), request_id="r",
    )
    assert outcome.failure_reason == "budget_exceeded" and not outcome.is_clear
    assert budget.finish("r")["model_calls"] == 0


@pytest.mark.parametrize("field", ["conversation_summary", "pending_query", "pending_clarifications"])
def test_large_memory_or_pending_never_calls_model(settings, field):
    provider = StubProvider(decision(["问题？"]))
    value = "较长的历史信息" * 100
    values = {"conversation_summary": "", "history_messages": [], "rewritten_query": "问题？", "question_is_clear": True}
    values[field] = [value] if field == "pending_clarifications" else value
    if field in {"pending_query", "pending_clarifications"}:
        values["action"] = "continue_clarification"
        values.setdefault("pending_query", "原待办")
    memory = PreparedQuery(**values)
    settings = settings.model_copy(update={"main_history_input_token_limit": 100})
    outcome = QueryAnalyzer(settings, provider).analyze("问题？", memory)
    assert outcome.failure_reason == "history_budget_exceeded" and not outcome.is_clear
    assert provider.calls == []


def test_simple_budget_keeps_last_slot_for_grounded_answer():
    budget = ModelCallBudget(2, 4, {
        "query_analysis": 1, "query_rewrite": 1,
        "conversation_summary": 0, "collect_answer": 1,
    })
    budget.start("r")
    assert budget.reserve("r", "query_analysis")
    assert not budget.reserve("r", "query_rewrite")
    assert not budget.reserve("r", "answer_repair")
    assert not budget.reserve("r", "conversation_summary")
    assert budget.reserve("r", "collect_answer")
    snapshot = budget.finish("r")
    assert snapshot["model_calls"] == 2
    assert snapshot["by_node"] == {"query_analysis": 1, "collect_answer": 1}
