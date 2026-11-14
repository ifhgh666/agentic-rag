from typing import List
from pydantic import BaseModel, Field, StrictBool


class ToolRouting(BaseModel):
    needs_knowledge: StrictBool = Field(
        description="Whether answering the current user request requires searching the PDF knowledge base."
    )

class QueryAnalysis(BaseModel):
    is_clear: bool = Field(
        description="Indicates if the user's question is clear and answerable."
    )
    questions: List[str] = Field(
        description="List of rewritten, self-contained questions."
    )
    clarification_needed: str = Field(
        description="Explanation if the question is unclear."
    )
