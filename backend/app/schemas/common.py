from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: UUID | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str
    service: str
    index_ready: bool


class PageInfo(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    count: int = Field(default=0, ge=0)


def new_id() -> UUID:
    return uuid4()

