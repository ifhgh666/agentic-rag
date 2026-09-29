from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    module: str
    request_id: UUID | None = None
    message: str
    duration_ms: int | None = None
    error: dict | None = None
    thread_id: str | None = None
    node: str | None = None
    event: str | None = None
    tool: str | None = None
    query: str | None = None
    parent_id: str | None = None
    score: float | None = None
    iteration: int | None = None
    tool_call_count: int | None = None
    details: dict = Field(default_factory=dict)


class LogListResponse(BaseModel):
    items: list[LogEntry]
    count: int = Field(ge=0)
