from langgraph.checkpoint.memory import InMemorySaver

from app.core.conversation import ConversationMemory


def test_memory_is_thread_scoped_and_preserves_overflow_for_budgeted_summary():
    memory = ConversationMemory(history_messages_to_keep=2)

    memory.append("thread-a", "PN8733 是什么？", "它是一款电源管理芯片。")
    memory.append("thread-a", "它的输入电压呢？", "资料显示输入电压范围为 5V。")

    snapshot = memory.snapshot("thread-a")
    assert len(snapshot.messages) == 2
    assert snapshot.conversation_summary == ""
    assert memory.thread_state("thread-a").summary_backlog[0].content == "PN8733 是什么？"
    assert memory.snapshot("thread-b").messages == []
    assert memory.snapshot("thread-b").conversation_summary == ""


def test_memory_prepares_original_question_and_separate_history_for_analyzer():
    memory = ConversationMemory(history_messages_to_keep=4)

    assert memory.prepare("new-thread", "它的保护功能呢？").rewritten_query == "它的保护功能呢？"

    memory.append("thread-a", "PN8733 的上电流程是什么？", "资料显示先完成输入检测。")
    prepared = memory.prepare("thread-a", "那它的保护功能呢？")
    assert prepared.question_is_clear is True
    assert prepared.history_messages[0]["content"] == "PN8733 的上电流程是什么？"
    assert prepared.rewritten_query == "那它的保护功能呢？"


def test_memory_uses_in_process_langgraph_saver_and_clears_thread():
    memory = ConversationMemory()
    assert isinstance(memory.checkpointer, InMemorySaver)
    memory.append("thread-a", "问题", "答案")
    memory.clear("thread-a")
    assert memory.snapshot("thread-a").messages == []
    assert memory.snapshot("thread-a").conversation_summary == ""
    fresh_memory = ConversationMemory()
    assert fresh_memory.snapshot("thread-a").messages == []
