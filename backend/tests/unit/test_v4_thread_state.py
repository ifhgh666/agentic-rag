import pytest
from pydantic import ValidationError
from app.core.conversation import ConversationMemory, ConversationTurn, ThreadState


def test_idle_thread_has_no_pending_and_accepts_plain_recent_messages():
    state = ThreadState(
        thread_id="thread-1",
        recent_messages=[ConversationTurn(role="user", content="问题"), ConversationTurn(role="assistant", content="回答")],
    )

    assert state.phase == "idle"
    assert state.state_version == 0
    assert state.pending_query == ""
    assert [message.role for message in state.recent_messages] == ["user", "assistant"]


def test_awaiting_clarification_requires_pending_and_keeps_supplements():
    state = ThreadState(
        thread_id="thread-1",
        phase="awaiting_clarification",
        pending_query="过流后如何恢复？",
        pending_clarifications=["PX-200"],
    )
    assert state.pending_query == "过流后如何恢复？"
    assert state.pending_clarifications == ["PX-200"]

    with pytest.raises(ValidationError):
        ThreadState(thread_id="thread-1", phase="awaiting_clarification")
    with pytest.raises(ValidationError):
        ThreadState(thread_id="thread-1", pending_query="不应存在")
    with pytest.raises(ValidationError):
        ThreadState(thread_id="thread-1", phase="answering", pending_query="不应存在")
    with pytest.raises(ValidationError):
        ThreadState(thread_id="thread-1", pending_clarifications=["孤立补充"])


def test_thread_id_phase_and_message_roles_are_validated():
    with pytest.raises(ValidationError):
        ThreadState(thread_id="  ")
    with pytest.raises(ValidationError):
        ThreadState(thread_id="thread-1", phase="paused")
    with pytest.raises(ValidationError):
        ThreadState(thread_id="thread-1", state_version=-1)
    with pytest.raises(ValidationError):
        ConversationTurn(role="tool", content="检索结果")
    with pytest.raises(ValidationError):
        ConversationTurn(role="user", content="问题", name="clarification_response")


def test_state_evolution_increments_version_and_rejects_stale_updates():
    initial = ThreadState(thread_id="thread-1")
    waiting = initial.advance(
        expected_version=0,
        phase="awaiting_clarification",
        pending_query="过流后如何恢复？",
    )

    assert initial.state_version == 0
    assert waiting.state_version == 1
    with pytest.raises(ValueError):
        waiting.advance(expected_version=0, phase="idle", pending_query="")


def test_memory_stores_one_validated_state_and_rejects_internal_messages():
    memory = ConversationMemory()
    assert memory.thread_state("thread-1").state_version == 0

    memory.append("thread-1", "PX-200 是什么？", "是设备。")
    memory.set_pending("thread-1", "过流后如何恢复？")
    assert isinstance(memory._threads["thread-1"], ThreadState)
    with pytest.raises(ValidationError):
        memory.update("thread-1", expected_version=2, recent_messages=[{"role": "tool", "content": "内部检索内容"}])
    with pytest.raises(ValidationError):
        memory.update("thread-1", expected_version=2, recent_messages=[{"role": "user", "name": "clarification_response", "content": "内部澄清"}])

    state = memory.thread_state("thread-1")
    assert state.phase == "awaiting_clarification"
    assert state.state_version == 2
    assert [message.content for message in state.recent_messages] == ["PX-200 是什么？", "是设备。"]

    memory.clear_pending("thread-1")
    assert memory.thread_state("thread-1").state_version == 3
    assert memory.thread_state("thread-1").pending_query == ""


def test_store_rejects_stale_write_and_returned_lists_are_detached():
    memory = ConversationMemory()
    previous = memory.thread_state("t")
    memory.set_pending("t", "待澄清题")
    with pytest.raises(ValueError, match="stale"):
        memory.update("t", expected_version=previous.state_version, phase="idle", pending_query="")
    snapshot = memory.thread_state("t")
    snapshot.pending_clarifications.append("不能写进存储")
    assert memory.thread_state("t").pending_clarifications == []
