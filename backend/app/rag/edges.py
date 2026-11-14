from typing import Literal
from langgraph.types import Send
from .graph_state import State, AgentState
from .graph_state import MAX_ITERATIONS, MAX_TOOL_CALLS

def route_after_rewrite(state: State) -> Literal["request_clarification", "agent"]:
    if not state.get("questionIsClear", False):
        decision = "request_clarification"
    else:
        decision = [
                Send("agent", {"question": query, "question_index": idx, "messages": []})
                for idx, query in enumerate(state["rewrittenQuestions"])
            ]
    return decision
    
def route_after_orchestrator_call(state: AgentState) -> Literal["tools", "fallback_response", "collect_answer"]:
    iteration = state.get("iteration_count", 0)
    tool_count = state.get("tool_call_count", 0)

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []

    if not tool_calls:
        decision = "collect_answer"
        return decision

    # The counters already include the current LLM response. Allow a final
    # answer at the iteration boundary, but do not execute tool calls that
    # would exceed the configured research budget.
    if iteration >= MAX_ITERATIONS or tool_count > MAX_TOOL_CALLS:
        decision = "fallback_response"
        return decision
    
    decision = "tools"
    return decision
