"""Hybrid retrieval and parent context construction."""
from __future__ import annotations

from ..config import Settings
from ..core.model_call import BoundedCache
from ..core.model_provider import estimate_tokens
from .index import IndexStore
from .stores import DocumentStore
from ..schemas.chat import RetrievalResult, SourceRef


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())

class Retriever:
    def __init__(self, settings: Settings, index_store: IndexStore, document_store: DocumentStore):
        self.settings = settings
        self.index_store = index_store
        self.document_store = document_store
        self._cache = BoundedCache(settings.rag_cache_max_entries, settings.rag_cache_ttl_seconds)

    def search(self, query: str, top_k: int | None = None, min_score: float | None = None) -> list[RetrievalResult]:
        return self.search_with_cache(query, top_k, min_score)[0]

    def search_with_cache(self, query: str, top_k: int | None = None, min_score: float | None = None) -> tuple[list[RetrievalResult], bool]:
        limit = top_k or self.settings.retrieval_top_k
        floor = self.settings.retrieval_min_score if min_score is None else min_score
        version = getattr(self.index_store, "version", "")
        key = (version, normalize_query(query), limit, floor)
        if version:
            hit, cached = self._cache.get(key)
            if hit:
                ready = [item.model_copy(deep=True) for item in cached if (
                    (document := self.document_store.get_document(item.document_id)) is not None
                    and document.status.value == "ready"
                )]
                return ready, True
        pairs = self.index_store.search(
            query,
            limit,
            floor,
        )
        results: list[RetrievalResult] = []
        for score, child in pairs:
            document = self.document_store.get_document(child.document_id)
            if not document or document.status.value != "ready":
                continue
            results.append(
                RetrievalResult(
                    child_id=child.child_id,
                    parent_id=child.parent_id,
                    document_id=child.document_id,
                    filename=document.filename,
                    section_title=child.section_title,
                    score=round(score, 4),
                    retrieval_mode=self.index_store.retrieval_mode,
                    content_preview=child.text[:240],
                    text=child.text,
                    page_start=getattr(child, "page_start", None),
                    page_end=getattr(child, "page_end", None),
                )
            )
        if version and version == getattr(self.index_store, "version", ""):
            self._cache.put(key, [item.model_copy(deep=True) for item in results])
        return results, False

class ContextBuilder:
    def __init__(self, settings: Settings, document_store: DocumentStore):
        self.settings = settings
        self.document_store = document_store

    def load_parents(self, results: list[RetrievalResult]):
        parents = []
        seen: set = set()
        for result in results:
            if result.parent_id in seen:
                continue
            seen.add(result.parent_id)
            parent = self.document_store.get_parent(result.parent_id)
            if parent:
                parents.append(parent)
        return parents

    def build(self, results: list[RetrievalResult]) -> tuple[str, list[SourceRef]]:
        context, sources, _ = self.build_with_records(results)
        return context, sources

    def build_with_records(
        self, results: list[RetrievalResult]
    ) -> tuple[str, list[SourceRef], list[dict[str, object]]]:
        parents = self.load_parents(results)
        blocks: list[str] = []
        sources: list[SourceRef] = []
        records: list[dict[str, object]] = []
        total = 0
        for parent in parents:
            document = self.document_store.get_document(parent.document_id)
            filename = document.filename if document else str(parent.document_id)
            source = SourceRef(
                document_id=parent.document_id,
                filename=filename,
                section_title=parent.section_title,
                page_start=parent.page_start,
                page_end=parent.page_end,
            )
            sources.append(source)
            label = f"来源：{filename} | 章节：{parent.section_title or '未命名章节'}"
            block = f"[{label}]\n{parent.text}"
            remaining = self.settings.max_context_chars - total
            if remaining <= 0:
                break
            block = block[:remaining]
            blocks.append(block)
            total += len(block)
            parent_scores = [item.score for item in results if item.parent_id == parent.parent_id]
            records.append(
                {
                    "role": "retrieval_result",
                    "record_id": str(parent.parent_id),
                    "parent_id": str(parent.parent_id),
                    "document_id": str(parent.document_id),
                    "source": filename,
                    "section_title": parent.section_title,
                    "score": max(parent_scores, default=0.0),
                    "content": block,
                    "tokens": estimate_tokens(block),
                }
            )
        return "\n\n".join(blocks), sources, records
