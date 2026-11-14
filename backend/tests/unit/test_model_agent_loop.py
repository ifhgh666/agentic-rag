"""Reference research routes replace ModelAgentLoop and terminal JSON."""
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.rag.edges import route_after_orchestrator_call
from app.rag.nodes import collect_answer, fallback_response
from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, tool_reply, research_calls
from tests.fakes.reference_model import ScriptedReferenceModel

@pytest.mark.parametrize("iteration,count", [(0, 0), (10, 8), (99, 99)])
def test_no_tool_answer_is_collectable_even_at_iteration_boundary(iteration, count):
    state = {"messages": [AIMessage(content="Model conclusion")], "iteration_count": iteration,
             "tool_call_count": count, "question": "q", "question_index": 0}
    assert route_after_orchestrator_call(state) == "collect_answer"
    assert collect_answer(state)["agent_answers"][0]["answer"] == "Model conclusion"

@pytest.mark.parametrize("iteration,count,expected", [(9, 8, "tools"), (10, 8, "fallback_response"),
                                                     (1, 9, "fallback_response")])
def test_tool_batches_observe_reference_limits(iteration, count, expected):
    state = {"messages": [tool_reply(("search_child_chunks", {"query": "q"}))],
             "iteration_count": iteration, "tool_call_count": count}
    assert route_after_orchestrator_call(state) == expected

@pytest.mark.parametrize("text", ["No sufficient evidence.", "Conclusion: 245 V exceeds 242 V.",
                                  '{"unstructured": "not a BranchAnswer"}'])
def test_model_text_is_not_repaired_or_replaced_by_citation_gate(settings, text):
    service, model, _ = make_service(settings, resolver=resolver_for(research=lambda *_: AIMessage(content=text)))
    final, _ = run_turn(service)
    assert final["state"]["agent_answers"][0]["answer"] == text
    assert len(research_calls(model)) == 1 and not service.retriever.calls

def test_fallback_synthesizes_deduplicated_real_tool_context_without_tools():
    model = ScriptedReferenceModel(resolver=lambda *_: AIMessage(content="Best supported conclusion"))
    state = {"question": "q", "context_summary": "prior summary", "messages": [HumanMessage(content="q"),
        ToolMessage(content="real excerpt", tool_call_id="one"), ToolMessage(content="real excerpt", tool_call_id="two")]}
    update = fallback_response(state, model)
    assert update["messages"][0].content == "Best supported conclusion"
    sent = model.calls[0]
    assert sent["messages"][-1].content.count("real excerpt") == 1
    assert "prior summary" in sent["messages"][-1].content and "tools" not in sent["kwargs"]

def test_invalid_terminal_message_reports_generation_gap():
    state = {"question": "q", "question_index": 0,
             "messages": [tool_reply(("search_child_chunks", {"query": "q"}))]}
    assert collect_answer(state)["final_answer"] == "Unable to generate an answer."
