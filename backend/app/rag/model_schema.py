from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    """V3-3 查询分析将使用的结构化输出契约。"""

    is_clear: bool
    questions: list[str] = Field(default_factory=list, max_length=3)
    clarification_needed: str | None = None


class GroundedCitation(BaseModel):
    citation_id: str
    quote: str


class GroundedAnswer(BaseModel):
    is_answerable: bool
    answer: str
    citations: list[GroundedCitation] = Field(default_factory=list)
    conflict: bool = False
