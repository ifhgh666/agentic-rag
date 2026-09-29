from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventStatus(str, Enum):
    started = "started"
    completed = "completed"
    failed = "failed"


class StageEvent(BaseModel):
    request_id: UUID
    stage: str
    status: EventStatus
    sequence: int
    duration_ms: int | None = None
    detail: dict | None = None
    error: str | None = None


class ExecutionEvent(BaseModel):
    """对外可见的执行摘要，不包含完整 Prompt 或模型私有推理。"""

    request_id: UUID
    thread_id: str
    node: str
    event: str
    tool: str | None = None
    query: str | None = None
    parent_id: str | None = None
    duration_ms: int | None = None
    score: float | None = None
    iteration: int | None = None
    tool_call_count: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
