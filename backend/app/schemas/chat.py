from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)


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


class SourceRef(BaseModel):
    document_id: UUID
    filename: str
    section_title: str = ""
    page_start: int | None = None
    page_end: int | None = None


class EvaluationResult(BaseModel):
    relevance: int = Field(ge=0, le=100)
    faithfulness: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)
    reason: str


class PipelineStage(str, Enum):
    query_receipt = "query_receipt"
    query_representation = "query_representation"
    child_retrieval = "child_retrieval"
    score_filtering = "score_filtering"
    parent_retrieval = "parent_retrieval"
    context_building = "context_building"
    context_compression = "context_compression"
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
