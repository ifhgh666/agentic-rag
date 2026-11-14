"""Validated conversation state, snapshots and atomic in-memory storage."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from threading import Lock, RLock
from typing import Any, Iterator, Literal


class ConversationTurn(BaseModel):
    """A completed, user-visible turn; internal and tool messages are excluded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, content: str) -> str:
        value = content.strip()
        if not value:
            raise ValueError("conversation turn content must not be blank")
        return value

class ThreadState(BaseModel):
    """Validated target contract for a single thread's conversation memory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    thread_id: str = Field(min_length=1, max_length=128)
    state_version: int = Field(default=0, ge=0)
    phase: Literal["idle", "awaiting_clarification", "answering"] = "idle"
    recent_messages: list[ConversationTurn] = Field(default_factory=list)
    summary_backlog: list[ConversationTurn] = Field(default_factory=list)
    conversation_summary: str = ""
    pending_query: str = ""
    pending_clarifications: list[str] = Field(default_factory=list)
    last_request_id: str | None = None

    @field_validator("thread_id", "pending_query")
    @classmethod
    def strip_identity_and_pending(cls, value: str, info: Any) -> str:
        cleaned = value.strip()
        if info.field_name == "thread_id" and not cleaned:
            raise ValueError("thread_id must not be blank")
        return cleaned

    @field_validator("pending_clarifications")
    @classmethod
    def validate_supplements(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("pending clarifications must not contain blank items")
        return cleaned

    @model_validator(mode="after")
    def check_pending_phase(self) -> "ThreadState":
        if self.phase == "awaiting_clarification":
            if not self.pending_query:
                raise ValueError("awaiting_clarification requires pending_query")
        elif self.pending_query or self.pending_clarifications:
            raise ValueError("pending data is only valid while awaiting clarification")
        return self

    def advance(self, *, expected_version: int, **changes: Any) -> "ThreadState":
        """Build a validated next state; persistence must still enforce atomic writes."""

        if expected_version != self.state_version:
            raise ValueError("stale thread state version")
        if "state_version" in changes or ("thread_id" in changes and changes["thread_id"] != self.thread_id):
            raise ValueError("state_version and thread_id cannot be overwritten")
        return type(self).model_validate({**self.model_dump(), **changes, "state_version": self.state_version + 1})

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
    pending_query: str = ""
    pending_clarifications: list[str] = field(default_factory=list)
    action: str = "auto"

    def resolved_original(self, current_question: str) -> str:
        """Join only original text and supplements explicitly confirmed by action."""
        current = current_question.strip()
        if self.action == "continue_clarification" and self.pending_query:
            return "\n".join([self.pending_query, *self.pending_clarifications, current])
        return current

class ConversationMemory:
    """Single validated store with a non-blocking request lease per thread."""

    def __init__(self, history_messages_to_keep: int = 4, summary_max_chars: int = 2000, checkpointer: InMemorySaver | None = None):
        self.history_messages_to_keep = max(2, int(history_messages_to_keep))
        self.summary_max_chars = max(200, int(summary_max_chars))
        self.checkpointer = checkpointer or InMemorySaver()
        self._threads: dict[str, ThreadState] = {}
        self._guard = RLock()
        self._leases: dict[str, Lock] = {}

    def exists(self, thread_id: str) -> bool:
        with self._guard:
            return thread_id in self._threads

    @contextmanager
    def request(self, thread_id: str) -> Iterator[ThreadState]:
        with self._guard:
            lease = self._leases.setdefault(thread_id, Lock())
        if not lease.acquire(blocking=False):
            raise RuntimeError("THREAD_BUSY")
        try:
            yield self.thread_state(thread_id)
        finally:
            lease.release()

    def thread_state(self, thread_id: str) -> ThreadState:
        with self._guard:
            return self._threads.get(thread_id, ThreadState(thread_id=thread_id)).model_copy(deep=True)

    def update(self, thread_id: str, *, expected_version: int, **changes: Any) -> ThreadState:
        with self._guard:
            current = self._threads.get(thread_id, ThreadState(thread_id=thread_id))
            updated = current.advance(expected_version=expected_version, **changes)
            self._threads[thread_id] = updated
            return updated.model_copy(deep=True)

    def restore(self, previous: ThreadState) -> None:
        current = self.thread_state(previous.thread_id)
        values = previous.model_dump(exclude={"thread_id", "state_version"})
        self.update(previous.thread_id, expected_version=current.state_version, **values)

    def snapshot(self, thread_id: str) -> MemorySnapshot:
        state = self.thread_state(thread_id)
        return MemorySnapshot(thread_id, state.conversation_summary,
                              [item.model_dump() for item in state.recent_messages])

    def prepare(self, thread_id: str, question: str, action: str = "auto") -> PreparedQuery:
        state = self.thread_state(thread_id)
        history = [item.model_dump() for item in [*state.summary_backlog, *state.recent_messages]]
        return PreparedQuery(
            state.conversation_summary, history, question.strip(), bool(question.strip()),
            pending_query=state.pending_query if action != "new_question" else "",
            pending_clarifications=list(state.pending_clarifications) if action != "new_question" else [],
            action=action,
        )

    def pending(self, thread_id: str) -> str:
        return self.thread_state(thread_id).pending_query

    def set_pending(self, thread_id: str, question: str, supplements: list[str] | None = None) -> None:
        state = self.thread_state(thread_id)
        self.update(thread_id, expected_version=state.state_version, phase="awaiting_clarification",
                    pending_query=question, pending_clarifications=supplements or [])

    def clear_pending(self, thread_id: str) -> None:
        state = self.thread_state(thread_id)
        if state.pending_query:
            self.update(thread_id, expected_version=state.state_version, phase="idle",
                        pending_query="", pending_clarifications=[])

    def begin_answer(self, thread_id: str, request_id: str) -> None:
        state = self.thread_state(thread_id)
        self.update(thread_id, expected_version=state.state_version, phase="answering",
                    pending_query="", pending_clarifications=[], last_request_id=request_id)

    def append(self, thread_id: str, question: str, answer: str) -> MemorySnapshot:
        """Persist real user text (including confirmed supplements), never model queries."""
        state = self.thread_state(thread_id)
        messages = [*state.recent_messages, ConversationTurn(role="user", content=question),
                    ConversationTurn(role="assistant", content=answer)]
        overflow = messages[:-self.history_messages_to_keep]
        messages = messages[-self.history_messages_to_keep:]
        self.update(thread_id, expected_version=state.state_version, phase="idle",
                    pending_query="", pending_clarifications=[], recent_messages=messages,
                    summary_backlog=[*state.summary_backlog, *overflow])
        return self.snapshot(thread_id)

    def clear(self, thread_id: str) -> None:
        with self._guard:
            self._threads.pop(thread_id, None)
