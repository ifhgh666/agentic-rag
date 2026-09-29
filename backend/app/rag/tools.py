from __future__ import annotations

from uuid import UUID
from concurrent.futures import Future
from threading import Lock
from typing import Callable, Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..config import Settings
from ..knowledge.stores import DocumentStore
from ..rag.retriever import Retriever
from .graph_state import Evidence


class SearchChildInput(BaseModel):
    query: str = Field(description="要检索的知识库问题或技术术语")
    limit: int = Field(default=7, ge=1, le=20, description="最多返回的 Child 数量")
    request_id: str = Field(default="", description="当前请求标识，用于避免同一请求重复读取")


class RetrieveParentInput(BaseModel):
    parent_id: str = Field(description="Parent UUID")
    request_id: str = Field(default="", description="当前请求标识，用于避免同一请求重复读取")


class RequestToolCache:
    """同一请求的并行 Agent 共享单飞缓存；请求结束后清空。"""

    def __init__(self):
        self._lock = Lock()
        self._items: dict[tuple[str, str], Future] = {}
        self._hits: dict[str, dict[str, int]] = {}

    def run(self, request_id: str, key: str, operation: Callable[[], Any]) -> Any:
        if not request_id:
            return operation()
        with self._lock:
            identity = (request_id, key)
            future = self._items.get(identity)
            owner = future is None
            if owner:
                future = Future()
                self._items[identity] = future
            else:
                self._record_hit_locked(request_id, "request_tool")
        if owner:
            try:
                future.set_result(operation())
            except BaseException as exc:
                future.set_exception(exc)
                raise
        return future.result()

    def _record_hit_locked(self, request_id: str, category: str) -> None:
        values = self._hits.setdefault(request_id, {})
        values[category] = values.get(category, 0) + 1

    def record_hit(self, request_id: str, category: str) -> None:
        if request_id:
            with self._lock:
                self._record_hit_locked(request_id, category)

    def stats(self, request_id: str) -> dict[str, int]:
        with self._lock:
            return dict(self._hits.get(request_id, {}))

    def clear(self, request_id: str) -> None:
        with self._lock:
            for key in [key for key in self._items if key[0] == request_id]:
                del self._items[key]
            self._hits.pop(request_id, None)


def create_rag_tools(
    retriever: Retriever,
    document_store: DocumentStore,
    settings: Settings,
    request_cache: RequestToolCache | None = None,
) -> list[StructuredTool]:
    def search_child_chunks(query: str, limit: int = settings.retrieval_top_k, request_id: str = "") -> dict:
        normalized = query.strip()
        if not normalized or len(normalized) > settings.max_question_chars:
            raise ValueError("INVALID_QUERY")
        if not retriever.index_store.ready:
            raise ValueError("INDEX_NOT_READY")
        def search():
            if isinstance(retriever, Retriever):
                found, hit = retriever.search_with_cache(normalized, top_k=limit, min_score=settings.retrieval_min_score)
                if hit and request_cache:
                    request_cache.record_hit(request_id, "retrieval")
                return found
            return retriever.search(normalized, top_k=limit, min_score=settings.retrieval_min_score)

        results = request_cache.run(request_id, f"search::{normalized.lower()}::{limit}", search) if request_cache else search()
        evidence = [
            Evidence(
                child_id=result.child_id,
                parent_id=result.parent_id,
                document_id=result.document_id,
                source=result.filename,
                section={"title": result.section_title},
                content=result.text or result.content_preview,
                score=result.score,
                retrieval_mode=result.retrieval_mode,
            ).model_dump(mode="json")
            for result in results
        ]
        return {"tool": "search_child_chunks", "query": normalized, "results": evidence}

    def retrieve_parent_chunks(parent_id: str, request_id: str = "") -> dict:
        try:
            parsed_parent_id = UUID(parent_id)
        except ValueError as exc:
            raise ValueError("INVALID_PARENT_ID") from exc
        def load_parent():
            return document_store.get_parent(parsed_parent_id)

        parent = request_cache.run(request_id, f"parent::{parsed_parent_id}", load_parent) if request_cache else load_parent()
        if not parent:
            raise ValueError("PARENT_NOT_FOUND")
        document = document_store.get_document(parent.document_id)
        if not document or document.status.value != "ready":
            raise ValueError("DOCUMENT_NOT_READY")
        return {
            "tool": "retrieve_parent_chunks",
            "parent_id": str(parent.parent_id),
            "document_id": str(parent.document_id),
            "source": document.filename,
            "section": {"title": parent.section_title},
            "page_start": parent.page_start,
            "page_end": parent.page_end,
            "content": parent.text,
        }

    return [
        StructuredTool.from_function(
            func=search_child_chunks,
            name="search_child_chunks",
            description="检索知识库中的 Child 证据；必须先调用该工具才能回答问题。",
            args_schema=SearchChildInput,
        ),
        StructuredTool.from_function(
            func=retrieve_parent_chunks,
            name="retrieve_parent_chunks",
            description="根据 parent_id 读取完整 Parent 上下文，不读取或解析 PDF。",
            args_schema=RetrieveParentInput,
        ),
    ]
