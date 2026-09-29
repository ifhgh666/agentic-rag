from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver


_CONTEXTUAL_RE = re.compile(r"(?:它|其|这个问题|这个|该|上述|那个|这方面|那它)")


@dataclass(frozen=True)
class MemorySnapshot:
    thread_id: str
    conversation_summary: str
    messages: list[dict[str, str]]


@dataclass(frozen=True)
class PreparedQuery:
    conversation_summary: str
    history_messages: list[dict[str, str]]
    rewritten_query: str
    question_is_clear: bool
    clarification: str = ""


class ConversationMemory:
    """进程内短期会话记忆。

    `InMemorySaver` 作为 LangGraph 的线程检查点存储；轻量的消息窗口和滚动摘要由本类
    管理，便于在进入检索图之前确定性地改写追问或返回澄清。
    """

    def __init__(self, history_messages_to_keep: int = 4, summary_max_chars: int = 2000, checkpointer: InMemorySaver | None = None):
        self.history_messages_to_keep = max(2, int(history_messages_to_keep))
        self.summary_max_chars = max(200, int(summary_max_chars))
        self.checkpointer = checkpointer or InMemorySaver()
        self._threads: dict[str, dict[str, Any]] = {}

    def snapshot(self, thread_id: str) -> MemorySnapshot:
        thread = self._threads.get(thread_id, {"summary": "", "messages": []})
        return MemorySnapshot(
            thread_id=thread_id,
            conversation_summary=str(thread.get("summary", "")),
            messages=[dict(item) for item in thread.get("messages", [])],
        )

    def prepare(self, thread_id: str, question: str) -> PreparedQuery:
        snapshot = self.snapshot(thread_id)
        normalized = " ".join(question.strip().split())
        pending = self.pending(thread_id)
        if pending and normalized:
            return PreparedQuery(
                snapshot.conversation_summary,
                snapshot.messages,
                f"原问题：{pending}\n补充信息：{normalized}"[:2000],
                True,
            )
        if len(normalized) < 2:
            return PreparedQuery(
                snapshot.conversation_summary,
                snapshot.messages,
                normalized,
                False,
                "请把问题描述得更完整一些，并说明相关文档、型号或主题。",
            )

        if not _CONTEXTUAL_RE.search(normalized):
            return PreparedQuery(
                snapshot.conversation_summary,
                snapshot.messages,
                normalized,
                True,
            )

        background = self._last_user_message(snapshot.messages) or snapshot.conversation_summary
        if not background:
            return PreparedQuery(
                snapshot.conversation_summary,
                snapshot.messages,
                normalized,
                False,
                "请说明你指的是哪份文档、哪个型号或哪个主题。",
            )
        rewritten = f"上轮对话背景：{background}\n补充问题：{normalized}"
        return PreparedQuery(
            snapshot.conversation_summary,
            snapshot.messages,
            rewritten[:2000],
            True,
        )

    def pending(self, thread_id: str) -> str:
        return str(self._threads.get(thread_id, {}).get("pending", ""))

    def set_pending(self, thread_id: str, question: str) -> None:
        thread = self._threads.setdefault(thread_id, {"summary": "", "messages": []})
        thread["pending"] = question.strip()

    def clear_pending(self, thread_id: str) -> None:
        if thread_id in self._threads:
            self._threads[thread_id].pop("pending", None)

    def append(self, thread_id: str, question: str, answer: str) -> MemorySnapshot:
        thread = self._threads.setdefault(thread_id, {"summary": "", "messages": []})
        messages = [*thread.get("messages", [])]
        messages.extend(
            [
                {"role": "user", "content": question.strip()},
                {"role": "assistant", "content": answer.strip()},
            ]
        )
        summary = str(thread.get("summary", ""))
        if len(messages) > self.history_messages_to_keep:
            overflow = messages[:-self.history_messages_to_keep]
            messages = messages[-self.history_messages_to_keep :]
            summary = self._roll_summary(summary, overflow)
        thread["summary"] = summary
        thread["messages"] = messages
        return self.snapshot(thread_id)

    def clear(self, thread_id: str) -> None:
        self._threads.pop(thread_id, None)

    def _last_user_message(self, messages: list[dict[str, str]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content", "").strip():
                return message["content"].strip()
        return ""

    def _roll_summary(self, previous: str, overflow: list[dict[str, str]]) -> str:
        lines = [previous] if previous else []
        for message in overflow:
            role = "用户" if message.get("role") == "user" else "助手"
            content = " ".join(message.get("content", "").split())
            if content:
                lines.append(f"{role}：{content}")
        summary = "\n".join(lines)
        return summary[-self.summary_max_chars :]
