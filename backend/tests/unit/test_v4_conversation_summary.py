import json

from app.core.conversation import ConversationMemory
from app.core.legacy_summary import summarize_conversation
from app.core.model_call import ModelCallBudget
from app.core.model_provider import ModelResult


class Provider:
    def __init__(self, summary):
        self.summary = summary
        self.calls = []

    def complete(self, messages, *, tools=None):
        self.calls.append(messages)
        return ModelResult(json.dumps({"summary": self.summary}), "ollama", "stub", 30, 10)


def history():
    memory = ConversationMemory(history_messages_to_keep=2)
    memory.append("t", "PX-200 的阈值？", "讨论的数值是 16 A。")
    memory.append("t", "后续流程？", "还需要文档确认。")
    return memory


def test_no_overflow_means_no_summary_call(settings):
    memory = ConversationMemory()
    memory.append("t", "PX-200 的阈值？", "讨论的数值是 16 A。")
    provider = Provider("unused")
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    assert summarize_conversation(memory, "t", "r", settings, None, lambda: provider) is None
    assert provider.calls == []


def test_full_budget_defers_without_truncating_history(settings):
    memory = history()
    original = memory.thread_state("t")
    budget = ModelCallBudget(2, 4, {"query_analysis": 1, "collect_answer": 1, "conversation_summary": 1})
    budget.start("r"); budget.reserve("r", "query_analysis"); budget.reserve("r", "collect_answer")
    provider = Provider("unused")
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    trace = summarize_conversation(memory, "t", "r", settings, budget, lambda: provider)
    assert trace["status"] == "deferred" and trace["attempted"] is False
    assert trace["failure_reason"] == "budget_exceeded"
    assert memory.thread_state("t") == original and provider.calls == []
    assert budget.finish("r")["model_calls"] == 2
    assert "PX-200" in memory.prepare("t", "下一题").history_messages[0]["content"]


def test_valid_summary_is_incremental_and_excludes_pending(settings):
    memory = history()
    memory.set_pending("t", "尚待澄清的故障题", ["补充信息"])
    provider = Provider("用户讨论 PX-200 的阈值，助手提到 16 A，仅为历史对话。")
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    trace = summarize_conversation(memory, "t", "", settings, None, lambda: provider)
    state = memory.thread_state("t")
    assert trace["status"] == "completed" and trace["input_tokens"] == 30
    assert not state.summary_backlog and "PX-200" in state.conversation_summary
    assert state.pending_query == "尚待澄清的故障题"
    assert "尚待澄清的故障题" not in provider.calls[0][-1]["content"]


def test_lost_entities_leave_original_overflow_available(settings):
    memory = history()
    previous = memory.thread_state("t")
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    trace = summarize_conversation(memory, "t", "", settings, None, lambda: Provider("用户讨论设备。"))
    assert trace["status"] == "deferred"
    assert memory.thread_state("t") == previous
