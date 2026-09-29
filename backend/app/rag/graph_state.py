from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from ..schemas.chat import EvaluationResult, RetrievalResult, SourceRef


def merge_agent_results(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 每轮主图输入传入空列表，清掉同一 thread 上一轮的 Map 结果。
    return [] if not right else left + right


class Evidence(BaseModel):
    """工具返回给 Agent 的最小、可审计证据。"""

    child_id: UUID
    parent_id: UUID
    document_id: UUID
    source: str
    section: dict[str, Any] = Field(default_factory=dict)
    content: str
    score: float
    retrieval_mode: Literal["dense", "hybrid"]


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    request_id: str
    thread_id: str
    question: str
    final_answer: str
    context_summary: str
    retrieval_keys: set[str]
    query_history: list[str]
    retrieved_contexts: list[dict[str, Any]]
    retrieved_results: list[dict[str, Any]]
    parent_contexts: list[dict[str, Any]]
    context: str
    sources: list[dict[str, Any]]
    tool_call_count: int
    iteration_count: int
    retrieval_top_k: int
    last_tool: str
    last_tool_args: dict[str, Any]
    last_tool_error: str
    budget_exceeded: bool
    context_compressed: bool
    context_token_threshold: int
    context_tokens_before: int
    context_tokens_after: int
    context_removed_items: int
    context_messages: list[dict[str, Any]]
    tool_trace: list[str]
    execution_trace: list[dict[str, Any]]
    model_trace: list[dict[str, Any]]
    node_trace: list[str]
    status: str


class MainState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    conversation_summary: str
    history_messages: list[dict[str, str]]
    original_query: str
    rewritten_query: str
    question_is_clear: bool
    clarification: str
    pending_query: str
    questions: list[str]
    agent_results: Annotated[list[dict[str, Any]], merge_agent_results]
    final_answer: str
    evaluation: dict[str, Any] | None
    thread_id: str
    request_id: str
    retrieved_results: list[dict[str, Any]]
    query_history: list[str]
    retrieval_keys: set[str]
    context: str
    sources: list[dict[str, Any]]
    tool_call_count: int
    iteration_count: int
    tool_trace: list[str]
    execution_trace: list[dict[str, Any]]
    model_trace: list[dict[str, Any]]
    node_trace: list[str]
    status: str
    agent_state: dict[str, Any]
    context_summary: str
    context_compressed: bool
    context_token_threshold: int
    context_tokens_before: int
    context_tokens_after: int
    context_removed_items: int
    context_messages: list[dict[str, Any]]


@dataclass
class GraphRunResult:
    final_answer: str
    retrieved_results: list[RetrievalResult]
    context: str
    sources: list[SourceRef]
    evaluation: EvaluationResult | None
    status: str
    tool_trace: list[str]
    node_trace: list[str]
    request_id: str
    thread_id: str
    query_history: list[str]
    retrieval_keys: set[str]
    budget_exceeded: bool
    context_summary: str = ""
    context_compressed: bool = False
    context_token_threshold: int = 0
    context_tokens_before: int = 0
    context_tokens_after: int = 0
    context_removed_items: int = 0
    context_messages: list[dict[str, Any]] = field(default_factory=list)
    conversation_summary: str = ""
    rewritten_query: str = ""
    question_is_clear: bool = True
    clarification: str = ""
    execution_trace: list[dict[str, Any]] = field(default_factory=list)
    model_trace: list[dict[str, Any]] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)


def new_agent_state(question: str, thread_id: str | None = None, request_id: str | None = None) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=question)],
        request_id=request_id or "",
        thread_id=thread_id or "",
        question=question,
        final_answer="",
        context_summary="",
        retrieval_keys=set(),
        query_history=[question.strip()],
        retrieved_contexts=[],
        retrieved_results=[],
        parent_contexts=[],
        context="",
        sources=[],
        tool_call_count=0,
        iteration_count=0,
        retrieval_top_k=7,
        last_tool="",
        last_tool_args={},
        last_tool_error="",
        budget_exceeded=False,
        context_compressed=False,
        context_token_threshold=0,
        context_tokens_before=0,
        context_tokens_after=0,
        context_removed_items=0,
        context_messages=[],
        tool_trace=[],
        execution_trace=[],
        model_trace=[],
        node_trace=[],
        status="running",
    )


def new_main_state(question: str, thread_id: str | None = None, request_id: str | None = None) -> MainState:
    return MainState(
        messages=[HumanMessage(content=question)],
        conversation_summary="",
        history_messages=[],
        original_query=question,
        rewritten_query=question,
        question_is_clear=True,
        clarification="",
        pending_query=question,
        questions=[question],
        agent_results=[],
        final_answer="",
        evaluation=None,
        thread_id=thread_id or f"thread-{uuid4()}",
        request_id=request_id or str(uuid4()),
        retrieved_results=[],
        query_history=[question.strip()],
        retrieval_keys=set(),
        context="",
        sources=[],
        tool_call_count=0,
        iteration_count=0,
        tool_trace=[],
        execution_trace=[],
        model_trace=[],
        node_trace=[],
        status="running",
        agent_state={},
        context_summary="",
        context_compressed=False,
        context_token_threshold=0,
        context_tokens_before=0,
        context_tokens_after=0,
        context_removed_items=0,
        context_messages=[],
    )
