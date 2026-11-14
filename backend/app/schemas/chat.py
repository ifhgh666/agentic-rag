from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(default="", max_length=2000)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)
    action: Literal["auto", "continue_clarification", "new_question", "cancel"] = "auto"

    @field_validator("question", "thread_id", "conversation_id")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned

    @model_validator(mode="after")
    def validate_action(self) -> "ChatRequest":
        if self.thread_id == "" or self.conversation_id == "":
            raise ValueError("thread_id must not be blank")
        if self.action == "cancel":
            if not self.thread_id:
                raise ValueError("cancel requires thread_id")
        elif not self.question:
            raise ValueError("question must not be blank")
        return self


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    min_score: float | None = Field(default=None, ge=-1.0, le=1.0)


class RetrievalResult(BaseModel):
    child_id: UUID
    parent_id: UUID
    document_id: UUID
    filename: str
    section_title: str = ""
    score: float
    retrieval_mode: Literal["dense", "hybrid"] = "hybrid"
    content_preview: str
    text: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class SourceRef(BaseModel):
    document_id: UUID
    filename: str
    section_title: str = ""
    page_start: int | None = None
    page_end: int | None = None


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2] = 2
    evidence_status: Literal["found", "insufficient", "not_evaluated"]
    citation_status: Literal["verified", "issue_found", "not_applicable", "not_evaluated"] = "not_evaluated"
    numeric_status: Literal["verified", "issue_found", "not_applicable", "not_evaluated"] = "not_evaluated"
    completeness_status: Literal["verified", "issue_found", "not_evaluated"] = "not_evaluated"
    reason: str


class PipelineStage(str, Enum):
    query_receipt = "query_receipt"
    query_representation = "query_representation"
    child_retrieval = "child_retrieval"
    score_filtering = "score_filtering"
    parent_retrieval = "parent_retrieval"
    context_building = "context_building"
    answer_generation = "answer_generation"
    answer_evaluation = "answer_evaluation"


class PipelineEvent(BaseModel):
    request_id: UUID
    stage: PipelineStage
    status: str
    sequence: int
    duration_ms: int | None = None
    detail: dict | None = None
    error: str | None = None
