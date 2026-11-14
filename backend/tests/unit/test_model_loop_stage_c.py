"""Model failures propagate; fallback is only the reference research limit route."""
import pytest
from langchain_core.messages import AIMessage
from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, analysis_reply

def test_model_exception_does_not_become_a_successful_partial_answer(settings):
    def broken(*_):
        raise ConnectionError("PRIVATE_MODEL_EXCEPTION")
    service, model, _ = make_service(settings, resolver=resolver_for(research=broken))
    with pytest.raises(ConnectionError, match="PRIVATE_MODEL_EXCEPTION"):
        run_turn(service)
    assert not any("final-answer synthesizer" in c["messages"][0].content for c in model.calls)
    assert not any(getattr(m, "content", "") == "Final answer: 230 V." for m in service.get_state("test").values["messages"])
    with service.request("test"):
        assert "test" in service._active

def test_pending_original_conditions_are_sent_to_synthesis(settings):
    count = [0]
    def rewrite(*_):
        count[0] += 1
        return analysis_reply() if count[0] == 1 else analysis_reply(["protection", "recovery"])
    service, model, _ = make_service(settings, resolver=resolver_for(rewrite=rewrite))
    first, _ = run_turn(service, "245 V for 400 ms; protect and recover?")
    assert first["pending"]
    final, _ = run_turn(service, "Equipment PX-200", action="auto")
    text = model.calls[-1]["messages"][-1].content
    assert all(s in text for s in ("245 V", "400 ms", "PX-200"))
    assert not final["pending"] and len(final["state"]["agent_answers"]) == 2

def test_no_tool_research_gap_is_a_model_answer_without_runtime_replacement(settings):
    service, model, _ = make_service(settings, resolver=resolver_for(research=lambda *_: AIMessage(content="Missing recovery conditions.")))
    final, _ = run_turn(service)
    assert final["state"]["agent_answers"][0]["answer"] == "Missing recovery conditions."
    assert len(model.calls) == 3 and not service.retriever.calls
