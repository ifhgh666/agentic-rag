"""Reference model observations account for real native calls without governance."""
from app.core.reference_observation import RequestObservation
from tests.fakes.reference_helpers import make_service, run_turn

def test_native_calls_are_observed_once_without_a_model_call_limit(settings):
    service, model, _ = make_service(settings)
    observation = RequestObservation(settings)
    final, frames = run_turn(service, callbacks=[observation])
    usage = observation.usage()
    assert not final["pending"] and usage["model_calls"] == len(model.calls) == 5
    assert usage["model_call_limit"] is None and not usage["budget_exceeded"]
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
    assert usage["calls_by_node"] == {"select_tool": 1, "rewrite_query": 1, "orchestrator": 2, "aggregate_answers": 1}
    assert observation.records and observation.tool_trace
    custom = [f["data"] for f in frames if f["kind"] == "custom"]
    assert custom and all(e["replayed"] is False for e in custom)
    assert len({r["model_call_id"] for r in observation.model_trace}) == usage["model_calls"]

def test_history_summary_is_a_real_extra_native_call(settings):
    service, model, _ = make_service(settings)
    run_turn(service, "one")
    run_turn(service, "two")
    observation = RequestObservation(settings)
    final, _ = run_turn(service, "three", callbacks=[observation])
    assert [call["node"] for call in observation.model_trace][:2] == ["select_tool", "summarize_history"]
    assert observation.usage()["calls_by_node"]["summarize_history"] == 1
    assert final["state"]["conversation_summary"] == "Previous conversation summary."
    assert len(final["state"]["agent_answers"]) == 1
