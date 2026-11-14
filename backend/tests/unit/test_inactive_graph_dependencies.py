"""The normal reference graph must never call the frozen legacy stack."""
import pytest
from app.rag.edges import route_after_rewrite
from app.core import answering, query_analysis, legacy_rag, model_call
from tests.fakes.reference_helpers import make_service, run_turn

@pytest.mark.parametrize("owner,name", [(answering, "AnswerGenerator"), (answering, "AnswerEvaluator"),
    (query_analysis, "QueryAnalyzer"), (legacy_rag, "EvidenceSelector"), (legacy_rag, "ModelQueryGenerator"),
    (model_call, "ModelCallBudget"), (model_call, "ModelCallRunner")])
def test_normal_graph_never_constructs_legacy_services(settings, monkeypatch, owner, name):
    def forbidden(*args, **kwargs):
        pytest.fail("Reference online execution entered frozen legacy service " + name)
    monkeypatch.setattr(getattr(owner, name), "__init__", forbidden)
    service, model, _ = make_service(settings)
    final, _ = run_turn(service)
    assert not final["pending"] and len(model.calls) == 5

def test_reference_branch_dispatch_contains_no_legacy_lease_or_procedure_policy():
    sends = route_after_rewrite({"questionIsClear": True, "rewrittenQuestions": ["a", "b"],
                                "procedure_required": True, "call_lease_id": "legacy"})
    assert [s.arg for s in sends] == [
        {"question": "a", "question_index": 0, "messages": []},
        {"question": "b", "question_index": 1, "messages": []}]
    assert all(s.node == "agent" for s in sends)

@pytest.mark.parametrize("threshold", [1, 100000])
def test_old_parent_setting_does_not_force_a_parent_tool(settings, threshold):
    service, model, _ = make_service(settings.model_copy(update={"agent_parent_threshold_chars": threshold}))
    run_turn(service)
    assert len(service.retriever.calls) == 1
    assert all("retrieve_parent_chunks" not in str(c["messages"]) for c in model.calls)
