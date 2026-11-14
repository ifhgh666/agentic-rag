"""Explicit frozen interfaces remain independent of the reference graph."""
from itertools import product
import json
import pytest
from app.core.model_call import BoundedCache
from tests.fakes.providers import ScriptedModel, terminal_answer
from tests.fakes.reference_helpers import make_service, run_turn
QUESTION = "What is the current threshold?"
QUOTE = "The current threshold is 16 A."

def test_reference_service_preserves_explicit_native_model_identity(settings):
    service, model, _ = make_service(settings)
    assert service.model is model
    run_turn(service)
    assert len(model.calls) == 5
    assert not any(hasattr(service, name) for name in ("memory", "query_analyzer", "model_budget", "generator"))


@pytest.mark.parametrize("action", ["cancel", "new_question"])
def test_pending_clear_preserves_completed_checkpoint_history(settings, action):
    from tests.fakes.reference_helpers import resolver_for, analysis_reply, conversation
    service, model, _ = make_service(settings)
    run_turn(service, "Completed question")
    model.resolver = resolver_for(rewrite=lambda *_: analysis_reply())
    pending, _ = run_turn(service, "UNRESOLVED_SENTINEL")
    assert pending["pending"]
    previous_calls = len(model.calls)
    model.resolver = resolver_for(questions=["NEW_QUESTION"])
    final, _ = run_turn(service, "NEW_QUESTION" if action == "new_question" else "", action=action)
    assert not final["pending"]
    assert any(m.content == "Completed question" for m in conversation(service))
    assert all("UNRESOLVED_SENTINEL" not in str(m.content) for m in final["state"]["messages"])
    if action == "cancel":
        assert final["cancelled"] and len(model.calls) == previous_calls
    else:
        assert all("UNRESOLVED_SENTINEL" not in str(m.content)
                   for call in model.calls[previous_calls:] for m in call["messages"])


def test_thread_action_guards_have_no_model_calls_and_cross_thread_is_independent(settings):
    service, model, _ = make_service(settings)
    with pytest.raises(ValueError, match="NO_PENDING_QUERY"):
        run_turn(service, action="continue_clarification")
    with pytest.raises(RuntimeError, match="THREAD_NOT_FOUND"):
        run_turn(service, action="cancel")
    assert not model.calls
    with service.request("locked"):
        with pytest.raises(RuntimeError, match="THREAD_BUSY"):
            run_turn(service, thread="locked")
        final, _ = run_turn(service, thread="other")
        assert not final["pending"]

@pytest.mark.parametrize("scenario", ["valid", "repair", "rejected", "empty"])
def test_legacy_generation_flags_leave_input_and_grounded_result_unchanged(settings, scenario):
    from app.core.answering import format_evidence_records
    from app.core.answering import AnswerGenerator
    from app.core.answering import INSUFFICIENT_ANSWER

    records = format_evidence_records([{"record_id": "one", "source": "guide.pdf", "raw_text": QUOTE}])
    accepted = terminal_answer("The threshold is 16 A.", QUOTE, citation_id="E1")
    invalid = terminal_answer("The threshold is 16 A.", "This quote is absent.", citation_id="E1")
    projections = []
    for required, citations in product((False, True), repeat=2):
        outputs = {"valid": [accepted], "repair": [invalid, accepted],
                   "rejected": [invalid, invalid], "empty": []}[scenario]
        provider = ScriptedModel(*outputs)
        result = AnswerGenerator(settings, provider).generate_grounded_with_result(
            QUESTION, [] if scenario == "empty" else records,
            procedure_required=required, include_fact_citations=citations)
        assert isinstance(result, tuple) and len(result) == 3
        answer, ids, trace = result
        projection = {"answer": answer, "ids": ids, "messages": provider.calls,
            "calls": len(provider.calls), "validation": trace.get("validation_status") if trace else None,
            "reason": trace.get("stop_reason") if trace else None,
            "repair": [r["validation_status"] for r in trace.get("repair_calls", [])] if trace else []}
        projections.append(projection)
        if scenario == "empty":
            assert result == (INSUFFICIENT_ANSWER, [], None) and not provider.calls
        elif scenario == "valid":
            assert ids == ["E1"] and len(provider.calls) == 1
        elif scenario == "repair":
            assert ids == ["E1"] and len(provider.calls) == 2
            assert trace["validation_status"] == "verification_failed"
            assert trace["repair_calls"][0]["validation_status"] == "accepted"
            assert provider.calls[1][-2]["content"] == invalid.content
        else:
            assert ids == [] and len(provider.calls) == 2 and trace["stop_reason"] == "verification_failed"
    (settings.data_dir / "generation-flags.json").write_text(json.dumps(projections, ensure_ascii=False, indent=2), encoding="utf-8")
    assert all(value == projections[0] for value in projections)


def test_outcome_procedure_default_and_cached_entrance_keep_three_field_schema(settings):
    from app.core.conversation import ConversationMemory
    from app.core.legacy_state import AgentState
    from app.core.legacy_state import MainState
    from app.core.query_analysis import AnalysisOutcome
    from app.core.query_analysis import QueryAnalyzer
    from app.core.legacy_schemas import QueryAnalysis
    from tests.fakes.providers import ScriptedQueryProvider, query_analysis_payload

    question = "What is the threshold?"
    provider = ScriptedQueryProvider(query_analysis_payload([question]))
    analyzer = QueryAnalyzer(settings.model_copy(update={"llm_provider": "ollama"}), provider,
        cache=BoundedCache(), index_version=lambda: "v1")
    prepared = ConversationMemory().prepare("compat", question)
    first = analyzer.analyze(question, prepared, thread_id="compat")
    cached = analyzer.analyze(question, prepared, thread_id="compat")
    assert first.is_clear and cached.is_clear and first.questions == cached.questions == [question]
    assert first.source == "model" and cached.source == "cache" and len(provider.calls) == 1
    assert AnalysisOutcome(True, [question]).requires_procedure is False
    assert first.requires_procedure is cached.requires_procedure is False
    assert set(QueryAnalysis.model_fields) == {"is_clear", "questions", "clarification_needed"}
    assert {"procedure_required", "procedure_only"} <= AgentState.__optional_keys__
    assert "procedure_required" in MainState.__optional_keys__


def test_old_parent_setting_keeps_default_and_environment_parsing(monkeypatch):
    from app.config import Settings
    monkeypatch.delenv("AGENT_PARENT_THRESHOLD_CHARS", raising=False)
    assert Settings(_env_file=None).agent_parent_threshold_chars == 240
    monkeypatch.setenv("AGENT_PARENT_THRESHOLD_CHARS", "1234")
    assert Settings(_env_file=None).agent_parent_threshold_chars == 1234

