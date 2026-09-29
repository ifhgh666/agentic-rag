from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class KnowledgeDocument(BaseModel):
    document_id: UUID
    filename: str
    status: DocumentStatus
    size_bytes: int = Field(ge=0)
    uploaded_at: datetime
    processed_at: datetime | None = None
    parent_count: int = Field(default=0, ge=0)
    child_count: int = Field(default=0, ge=0)
    error_reason: str | None = None
    source_path: str | None = None
    markdown_path: str | None = None


class DocumentListResponse(BaseModel):
    items: list[KnowledgeDocument]


class UploadResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    filename: str


class ParentContextUnit(BaseModel):
    parent_id: UUID
    document_id: UUID
    section_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    text: str
    char_count: int
    ordinal: int


class SearchableChildUnit(BaseModel):
    child_id: UUID
    parent_id: UUID
    document_id: UUID
    section_title: str = ""
    text: str
    char_count: int
    ordinal: int
    vector_position: int | None = None

