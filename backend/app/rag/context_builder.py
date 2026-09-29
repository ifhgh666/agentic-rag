from ..config import Settings
from ..knowledge.stores import DocumentStore
from ..schemas.chat import RetrievalResult, SourceRef
from .context_compression import estimate_tokens


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
