"""Phase-A engineering checks; scripted outputs are not real semantic validation."""
from dataclasses import replace
import json
from pathlib import Path
from threading import Event
from time import monotonic

import pytest
from pydantic import ValidationError
from app.core.conversation import PreparedQuery
from app.core.model_call import BoundedCache, ModelCallBudget
from app.core.model_provider import ModelResult
from app.core.legacy_schemas import QueryAnalysis
from app.core.query_analysis import QueryAnalyzer, _literal_constraints_preserved
from tests.fakes.providers import ScriptedQueryProvider, query_analysis_payload


CASES = json.loads((Path(__file__).parents[1] / "fixtures/query_rewrite_v1_cases.json").read_text(encoding="utf-8"))
CASES_BY_ID = {case["id"]: case for case in CASES["cases"]}


def prepared(**changes):
    return PreparedQuery("", [], "unused legacy rewrite", True, **changes)


def analyzer(settings, question="问题？", **kwargs):
    provider = ScriptedQueryProvider(query_analysis_payload([question]))
    return QueryAnalyzer(settings, provider, **kwargs), provider


def test_strict_three_fields_and_internal_whitespace_preserved():
    payload = query_analysis_payload(["  Guide_V1.PDF  中 PX-200 的启动电压是多少？  "])
    value = QueryAnalysis.model_validate(payload)
    assert value.questions == ["Guide_V1.PDF  中 PX-200 的启动电压是多少？"]
    assert set(value.model_dump()) == {"is_clear", "questions", "clarification_needed"}
    with pytest.raises(ValidationError):
        QueryAnalysis.model_validate({**payload, "relation": "new_question"})


@pytest.mark.parametrize("case", CASES["cases"][:6], ids=lambda item: item["id"])
def test_fixed_complete_questions_are_carried_without_normalization(settings, case):
    query, provider = analyzer(settings, case["question"])
    result = query.analyze(case["question"], prepared())
    assert result.questions == [case["question"]] and result.source == "model"
    assert result.model_trace["original_conditions"] == case["question"]
    assert case["question"] in provider.calls[0][-1]["content"]
    assert len(provider.calls) == 1


@pytest.mark.parametrize("other", ["guide_v1.pdf  中 PX-200 的启动电压是多少？", "Guide_V1.PDF 中 PX-200 的启动电压是多少？"])
def test_case_or_internal_spacing_must_not_hit_another_question_cache(settings, other):
    first = CASES["cases"][2]["question"]
    provider = ScriptedQueryProvider(query_analysis_payload([first]), query_analysis_payload([other]))
    query = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: "v1")
    assert query.analyze(first, prepared(), thread_id="t").source == "model"
    assert query.analyze(first, prepared(), thread_id="t").source == "cache"
    assert query.analyze(other, prepared(), thread_id="t").questions == [other]
    assert len(provider.calls) == 2


def test_single_contextual_completion_is_not_restored_to_unresolved_input(settings):
    provider = ScriptedQueryProvider(query_analysis_payload(["PN8733 的恢复条件是什么？"]))
    result = QueryAnalyzer(settings, provider).analyze("它的恢复条件是什么？", replace(prepared(),
        history_messages=[{"role": "user", "content": "PN8733 的启动电压是多少？"}]))
    assert result.questions == ["PN8733 的恢复条件是什么？"]
    assert len(provider.calls) == 1


def test_unique_history_reference_fallback_repairs_model_clarification(settings):
    provider = ScriptedQueryProvider(query_analysis_payload([], clear=False, clarification="请说明它指哪个设备。"))
    result = QueryAnalyzer(settings, provider).analyze("它的恢复条件是什么？", replace(prepared(),
        history_messages=[{"role": "user", "content": "PN8733 的启动电压是多少？"}]))
    assert result.is_clear and result.questions == ["PN8733 的恢复条件是什么？"]
    assert result.source == "model"
    assert result.model_trace["reference_fallback"]["source"] == "unique_history_model_id"
    assert len(provider.calls) == 1


def test_unique_history_reference_fallback_stays_conservative_with_multiple_objects(settings):
    provider = ScriptedQueryProvider(query_analysis_payload([], clear=False, clarification="请说明它指哪个设备。"))
    result = QueryAnalyzer(settings, provider).analyze("它的恢复条件是什么？", replace(prepared(),
        history_messages=[
            {"role": "user", "content": "PN8733 的启动电压是多少？"},
            {"role": "user", "content": "PX-200 的维护周期是什么？"},
        ]))
    assert not result.is_clear and result.questions == []
    assert "reference_fallback" not in result.model_trace


@pytest.mark.parametrize("payload", [
    "not-json", "```json\n{}\n```", {}, [],
    {"is_clear": True, "questions": ["问题？"]},
    {**query_analysis_payload(["问题？"]), "is_clear": "true"},
    {**query_analysis_payload(["问题？"]), "is_clear": 1},
    {**query_analysis_payload(["问题？"]), "clarification_needed": None},
    {**query_analysis_payload(["问题？"]), "source": "model"},
    {**query_analysis_payload(["问题？"]), "requires_procedure": True},
    query_analysis_payload([]), query_analysis_payload(["  "]),
    query_analysis_payload(["A  B", "a b"]), query_analysis_payload(["A", "B", "C", "D"]),
    query_analysis_payload([1]), query_analysis_payload(["a" * 2001]),
    {**query_analysis_payload(["问题？"]), "clarification_needed": "请补充"},
    query_analysis_payload([], clear=False), query_analysis_payload(["问题？"], clear=False, clarification="请补充"),
])
def test_invalid_structure_fails_once_without_fallback_or_tools(settings, payload):
    provider = ScriptedQueryProvider(payload)
    result = QueryAnalyzer(settings, provider).analyze("问题？", prepared())
    assert result.failure_reason == "invalid_model_output" and not result.is_clear and result.questions == []
    assert len(provider.calls) == 1


@pytest.mark.parametrize("error, reason", [(TimeoutError("private timeout"), "timeout"), (RuntimeError("private secret"), "model_unavailable")])
def test_provider_failure_is_one_attempt_and_keeps_sensitive_exception_private(settings, error, reason):
    provider = ScriptedQueryProvider(error)
    result = QueryAnalyzer(settings, provider).analyze("问题？", prepared())
    assert result.failure_reason == reason and len(provider.calls) == 1
    assert "private" not in repr(result) and result.questions == []


@pytest.mark.parametrize("change", [
    {"conversation_summary": "new summary"},
    {"history_messages": [{"role": "user", "content": "new context"}]},
    {"action": "new_question"},
    {"action": "continue_clarification", "pending_query": "原题", "pending_clarifications": ["补充"]},
])
def test_changed_context_or_action_invalidates_cache(settings, change):
    provider = ScriptedQueryProvider(query_analysis_payload(["问题？"]), query_analysis_payload(["问题？"]))
    query = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: "v1")
    query.analyze("问题？", prepared(), thread_id="t")
    value = query.analyze("问题？", replace(prepared(), **change), thread_id="t")
    assert value.source == "model" and len(provider.calls) == 2


def test_cache_isolates_thread_index_model_and_policy_version(settings, monkeypatch):
    version = ["v1"]
    provider = ScriptedQueryProvider(*[query_analysis_payload(["问题？"])] * 6)
    query = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: version[0])
    query.analyze("问题？", prepared(), thread_id="t")
    cached = query.analyze("问题？", prepared(), thread_id="t")
    assert cached.source == "cache" and cached.model_trace is None
    cached.questions.append("caller mutation")
    assert query.analyze("问题？", prepared(), thread_id="t").questions == ["问题？"]
    query.analyze("问题？", prepared(), thread_id="another")
    version[0] = "v2"
    query.analyze("问题？", prepared(), thread_id="t")
    query.settings = settings.model_copy(update={"ollama_model": "different-model"})
    query.analyze("问题？", prepared(), thread_id="t")
    monkeypatch.setattr("app.core.query_analysis.QUERY_REWRITE_POLICY_VERSION", "v-next")
    query.analyze("问题？", prepared(), thread_id="t")
    query.provider = ScriptedQueryProvider(query_analysis_payload(["问题？"]))
    query.analyze("问题？", prepared(), thread_id="t")
    assert len(provider.calls) == 5 and len(query.provider.calls) == 1


def test_each_confirmed_pending_component_has_its_own_cache_identity(settings):
    provider = ScriptedQueryProvider(*[query_analysis_payload(["完整问题？"])] * 3)
    query = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: "v1")
    initial = prepared(action="continue_clarification", pending_query="原待办一", pending_clarifications=["补充一"])
    query.analyze("当前补充", initial, thread_id="t")
    assert query.analyze("当前补充", initial, thread_id="t").source == "cache"
    assert query.analyze("当前补充", replace(initial, pending_query="原待办二"), thread_id="t").source == "model"
    assert query.analyze("当前补充", replace(initial, pending_clarifications=["补充二"]), thread_id="t").source == "model"
    assert len(provider.calls) == 3


def test_invalid_output_is_never_reused_as_successful_cache(settings):
    provider = ScriptedQueryProvider("invalid-json", query_analysis_payload(["问题？"]))
    query = QueryAnalyzer(settings, provider, cache=BoundedCache(), index_version=lambda: "v1")
    assert query.analyze("问题？", prepared(), thread_id="t").failure_reason == "invalid_model_output"
    assert query.analyze("问题？", prepared(), thread_id="t").source == "model"
    assert query.analyze("问题？", prepared(), thread_id="t").source == "cache"
    assert len(provider.calls) == 2


def test_oversize_original_is_rejected_instead_of_silently_truncated(settings):
    query, provider = analyzer(settings)
    assert query.analyze("a" * 2001, prepared()).failure_reason == "context_budget_exceeded"
    assert provider.calls == []


@pytest.mark.parametrize("action, pending, reason", [("auto", "原待办", None), ("cancel", "原待办", None), ("continue_clarification", "", "NO_PENDING_QUERY")])
def test_explicit_action_guards_take_zero_model_calls(settings, action, pending, reason):
    query, provider = analyzer(settings)
    result = query.analyze("任意回复", prepared(action=action, pending_query=pending))
    assert not result.is_clear and result.questions == [] and result.failure_reason == reason
    assert provider.calls == [] and result.source == "safe_fallback"


def test_new_question_does_not_leak_old_pending_in_model_input(settings):
    query, provider = analyzer(settings)
    result = query.analyze("问题？", prepared(action="new_question", pending_query="旧待办秘密", pending_clarifications=["旧补充秘密"]))
    assert result.relation == "new_question"
    assert "旧待办秘密" not in provider.calls[0][-1]["content"] and "旧补充秘密" not in provider.calls[0][-1]["content"]


@pytest.mark.parametrize("guard", ["model", "window", "history"])
def test_budget_window_and_history_guards_never_call_provider(settings, guard):
    provider = ScriptedQueryProvider(query_analysis_payload(["问题？"]))
    budget = ModelCallBudget(0, 0, {"query_analysis": 0}) if guard == "model" else None
    if budget:
        budget.start("r")
    values = prepared()
    if guard == "window":
        settings = settings.model_copy(update={"model_context_window": 100})
    elif guard == "history":
        settings = settings.model_copy(update={"main_history_input_token_limit": 10})
        values = replace(values, conversation_summary="历史信息" * 100)
    result = QueryAnalyzer(settings, provider, budget=budget).analyze("问题？", values, request_id="r" if budget else "")
    assert result.failure_reason == {"model": "budget_exceeded", "window": "context_budget_exceeded", "history": "history_budget_exceeded"}[guard]
    assert provider.calls == []
    if budget:
        assert budget.finish("r")["model_calls"] == 0


def test_reference_rewrite_keeps_original_in_checkpoint_and_aggregate_input(settings):
    from langchain_core.messages import AIMessage
    from tests.fakes.reference_helpers import make_service, resolver_for, run_turn
    original = "245 V for 400 ms, what protection?"
    wrong = "245 V for 40 ms, what protection?"
    service, model, _ = make_service(settings, resolver=resolver_for(questions=[wrong],
        research=lambda *_: AIMessage(content="model conclusion")))
    final, _ = run_turn(service, original)
    assert final["state"]["rewrittenQuestions"] == [wrong]
    assert final["state"]["originalQuery"] == original
    assert original in model.calls[-1]["messages"][-1].content

def test_reference_confirmed_supplements_reach_aggregate_without_old_history_copy(settings):
    from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, analysis_reply
    count = [0]
    def rewrite(*_):
        count[0] += 1
        return analysis_reply() if count[0] < 3 else analysis_reply(["MN-42 checks"])
    service, model, _ = make_service(settings, resolver=resolver_for(rewrite=rewrite))
    run_turn(service, "What checks before power on?")
    run_turn(service, "Use manual V1", action="continue_clarification")
    final, _ = run_turn(service, "MN-42", action="continue_clarification")
    assert not final["pending"] and not final["state"]["pendingQuery"]
    text = model.calls[-1]["messages"][-1].content
    assert all(item in text for item in ("What checks before power on?", "Use manual V1", "MN-42"))
    assert not hasattr(service, "memory")

def test_reference_pending_auto_resumes_and_calls_model(settings):
    from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, analysis_reply
    count = [0]
    def rewrite(*_):
        count[0] += 1
        return analysis_reply() if count[0] == 1 else analysis_reply(["PX-200 recovery"])
    service, model, _ = make_service(settings, resolver=resolver_for(rewrite=rewrite))
    pending, _ = run_turn(service, "How does it recover?")
    assert pending["pending"]
    final, _ = run_turn(service, "PX-200", action="auto")
    assert final["continued"] and not final["pending"] and count[0] == 2

def test_reference_transport_failure_releases_thread_and_keeps_pending_query(settings):
    from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, analysis_reply
    count = [0]
    def rewrite(*_):
        count[0] += 1
        if count[0] == 1:
            return analysis_reply()
        raise TimeoutError("private transport timeout")
    service, model, _ = make_service(settings, resolver=resolver_for(rewrite=rewrite))
    run_turn(service, "How does it recover?")
    with pytest.raises(TimeoutError):
        run_turn(service, "PX-200", action="auto")
    assert service.get_state("test").values["pendingQuery"] == "How does it recover?"
    assert count[0] == 2
    with service.request("test"):
        assert "test" in service._active


def test_summary_literal_guard_remains_active():
    assert not _literal_constraints_preserved("245 V 持续400 ms", ["245 V 持续40 ms"], "")


@pytest.mark.parametrize("case_id", ["RW11", "RW12", "RW13", "RW14"], ids=lambda value: value)
def test_stage_c_split_contract_preserves_expected_subquestions(settings, case_id):
    case = CASES_BY_ID[case_id]
    expected = case["expected"]["questions"]
    provider = ScriptedQueryProvider(query_analysis_payload(expected))
    result = QueryAnalyzer(settings, provider).analyze(case["question"], prepared())

    assert result.is_clear is True
    assert result.questions == expected
    assert len(result.questions) <= 3
    assert len(provider.calls) == 1


def test_stage_c_four_question_case_requires_user_choice(settings):
    case = CASES_BY_ID["RW15"]
    clarification = case["expected"]["clarification_needed"]
    provider = ScriptedQueryProvider(query_analysis_payload([], clear=False, clarification=clarification))
    result = QueryAnalyzer(settings, provider).analyze(case["question"], prepared())

    assert result.is_clear is False
    assert result.questions == []
    assert result.clarification == clarification
    assert len(provider.calls) == 1


def test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity(settings):
    provider = ScriptedQueryProvider(query_analysis_payload(["问题一？", "问题二？"]))
    QueryAnalyzer(settings, provider).analyze("问题一和问题二？", prepared())
    prompt = provider.calls[0][0]["content"]

    assert "共享型号、电压、持续时间" in prompt
    assert "保留“是否”“如果触发”的前提" in prompt
    assert "比较意图留给原题和最终回答" in prompt
    assert "超过三个" in prompt and "不能静默删掉需求" in prompt

