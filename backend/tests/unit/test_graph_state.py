from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages
from app.rag.graph_state import (AgentState, accumulate_or_reset, set_union, append_unique,
    MAX_TOOL_CALLS, MAX_ITERATIONS, GRAPH_RECURSION_LIMIT, MAIN_HISTORY_MESSAGES_TO_KEEP,
    BASE_TOKEN_THRESHOLD, TOKEN_GROWTH_FACTOR)
from app.core.legacy_state import Evidence
from uuid import uuid4
import pytest

def test_reference_state_uses_resettable_branch_answers_and_native_messages():
    first = {"index": 0, "answer": "first"}
    assert accumulate_or_reset([first], []) == [first]
    assert accumulate_or_reset([first], [{"__reset__": True}]) == []
    assert accumulate_or_reset([], [first]) == [first]
    left = [HumanMessage(content="q", id="q")]
    assert add_messages(left, [AIMessage(content="a", id="a")])[0].id == "q"
    assert "call_lease_id" not in AgentState.__annotations__

def test_reference_retrieval_reducers_preserve_unique_provenance():
    assert set_union({"search::q"}, {"search::q", "parent::p"}) == {"search::q", "parent::p"}
    assert append_unique(["one", "two"], ["two", "three"]) == ["one", "two", "three"]

def test_reference_limits_are_fixed_and_separate_from_legacy_limits():
    assert (MAX_TOOL_CALLS, MAX_ITERATIONS, GRAPH_RECURSION_LIMIT) == (8, 10, 50)
    assert (MAIN_HISTORY_MESSAGES_TO_KEEP, BASE_TOKEN_THRESHOLD, TOKEN_GROWTH_FACTOR) == (4, 2000, .9)

def test_evidence_validates_retrieval_mode_and_content():
    evidence = Evidence(child_id=uuid4(), parent_id=uuid4(), document_id=uuid4(), source="guide.pdf",
                        section={}, content="voltage", score=.8, retrieval_mode="hybrid")
    assert evidence.content == "voltage"
    with pytest.raises(ValueError):
        Evidence.model_validate({**evidence.model_dump(), "retrieval_mode": "invalid"})
