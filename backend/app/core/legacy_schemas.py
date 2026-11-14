"""Agent model output and tool input contracts."""
from __future__ import annotations

from copy import deepcopy
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal


def _query_clarity_schema(schema: dict) -> None:
    """Express the runtime state invariant in the schema used for generation."""
    clear, unclear = deepcopy(schema), deepcopy(schema)
    clear["properties"]["is_clear"]["const"] = True
    clear["properties"]["questions"]["minItems"] = 1
    clear["properties"]["clarification_needed"]["const"] = ""
    unclear["properties"]["is_clear"]["const"] = False
    unclear["properties"]["questions"]["maxItems"] = 0
    unclear["properties"]["clarification_needed"]["minLength"] = 1
    # Each alternative is a complete object contract. Grammar compilers may
    # process anyOf before sibling properties; partial alternatives would lose
    # the required fields, types and additionalProperties restriction.
    schema["anyOf"] = [clear, unclear]

class QueryAnalysis(BaseModel):
    """Strict model-only entrance contract; runtime action metadata is separate."""

    model_config = ConfigDict(extra="forbid", strict=True, json_schema_extra=_query_clarity_schema)

    is_clear: bool = Field(description=(
        "问题是否能按提供的上下文独立检索，不代表已知道答案。"
        "仅未解决的指代或无法在三问内保留的独立需求需要澄清。"
    ))
    questions: list[str] = Field(max_length=3, description=(
        "清楚时为1至3个非空、不重复、可独立检索的问题；完整单问保留原句。"
        "不清楚时为空数组，不包含答案或未确认事实。"
    ))
    clarification_needed: str = Field(description=(
        "清楚时为空字符串；不清楚时写具体的指代或最多三项需求选择问题。"
        "不得向用户索要需要从资料检索的答案。"
    ))

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, questions: list[str]) -> list[str]:
        cleaned = [question.strip() for question in questions]
        if any(not question or len(question) > 2000 for question in cleaned):
            raise ValueError("questions must contain 1–2000 characters")
        # Normalize only a comparison copy, never the text sent to retrieval.
        keys = [" ".join(question.split()).casefold() for question in cleaned]
        if len(set(keys)) != len(keys):
            raise ValueError("questions must be distinct")
        return cleaned

    @field_validator("clarification_needed")
    @classmethod
    def strip_clarification(cls, clarification: str) -> str:
        return clarification.strip()

    @model_validator(mode="after")
    def check_clarity(self) -> "QueryAnalysis":
        if self.is_clear:
            if not self.questions or self.clarification_needed:
                raise ValueError("clear output requires questions and empty clarification")
        elif self.questions or not self.clarification_needed:
            raise ValueError("unclear output requires empty questions and a clarification")
        return self

class GroundedCitation(BaseModel):
    citation_id: str
    quote: str

class GroundedAnswer(BaseModel):
    is_answerable: bool
    answer: str
    citations: list[GroundedCitation] = Field(default_factory=list)
    conflict: bool = False
    procedure_unit_ids: list[str] = Field(default_factory=list, max_length=16)

class EvidenceClaim(BaseModel):
    kind: Literal["document_fact", "user_condition", "derived_result"]
    text: str
    citation_ids: list[str] = Field(default_factory=list)
    input_refs: list[str] = Field(default_factory=list)

class BranchAnswer(BaseModel):
    status: Literal["answered", "partial", "insufficient"]
    answer: str = ""
    citations: list[GroundedCitation] = Field(default_factory=list)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    brief_reason: str = ""
    stop_reason: str = ""

    @model_validator(mode="after")
    def check_answer(self) -> "BranchAnswer":
        if self.status in {"answered", "partial"} and (not self.answer.strip() or not self.citations):
            raise ValueError("ANSWER_REQUIRES_TEXT_AND_CITATIONS")
        if self.status == "insufficient" and not (self.answer.strip() or self.missing_information):
            raise ValueError("INSUFFICIENT_REQUIRES_SPECIFIC_GAP")
        return self

class SearchChildInput(BaseModel):
    query: str = Field(description="要检索的知识库问题或技术术语")
    limit: int = Field(default=7, ge=1, le=20, description="最多返回的 Child 数量")
    request_id: str = Field(default="", description="当前请求标识，用于避免同一请求重复读取")

class RetrieveParentInput(BaseModel):
    parent_id: str = Field(description="Parent UUID")
    offset: int = Field(default=0, ge=0, description="原文章节的字符起点；由模型决定是否继续读取下一段")
    max_chars: int = Field(default=1600, ge=200, le=2400, description="本次原文窗口大小，防止超过模型上下文")
    request_id: str = Field(default="", description="当前请求标识，用于避免同一请求重复读取")
