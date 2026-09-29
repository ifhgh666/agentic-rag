from ..config import Settings
from ..knowledge.stores import DocumentStore
from ..schemas.chat import RetrievalResult
from .index_store import IndexStore
from .cost_control import BoundedCache
from .query_planner import normalize_query


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
                )
            )
        if version and version == getattr(self.index_store, "version", ""):
            self._cache.put(key, [item.model_copy(deep=True) for item in results])
        return results, False
