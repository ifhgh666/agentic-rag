from uuid import uuid4

import pytest

from app.rag.graph_state import Evidence, new_agent_state, new_main_state


def test_graph_states_have_explicit_defaults_and_budget_fields():
    state = new_agent_state("如何上电？", thread_id="thread-1")
    main = new_main_state("如何上电？", thread_id="thread-1")

    assert state["question"] == "如何上电？"
    assert state["tool_call_count"] == 0
    assert state["iteration_count"] == 0
    assert state["retrieval_keys"] == set()
    assert state["context_summary"] == ""
    assert state["context_compressed"] is False
    assert state["context_messages"] == []
    assert main["thread_id"] == "thread-1"
    assert main["question_is_clear"] is True
    assert main["conversation_summary"] == ""
    assert main["history_messages"] == []
    assert main["clarification"] == ""
    assert main["context_summary"] == ""
    assert main["context_compressed"] is False
    assert main["context_messages"] == []


def test_evidence_validates_retrieval_mode_and_content():
    evidence = Evidence(
        child_id=uuid4(),
        parent_id=uuid4(),
        document_id=uuid4(),
        source="guide.pdf",
        section={"title": "上电"},
        content="系统先检查输入电压。",
        score=0.8,
        retrieval_mode="hybrid",
    )

    assert evidence.content
    assert evidence.retrieval_mode == "hybrid"
    with pytest.raises(ValueError):
        Evidence.model_validate({**evidence.model_dump(), "retrieval_mode": "invalid"})
