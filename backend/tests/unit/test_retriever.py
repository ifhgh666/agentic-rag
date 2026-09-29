from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.rag.embeddings import EmbeddingService
from app.rag.index_store import IndexStore
from app.rag.retriever import Retriever
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, SearchableChildUnit


def test_retriever_returns_only_ready_documents(settings):
    document_store = DocumentStore(settings.data_dir)
    ready_id, failed_id, parent_id = uuid4(), uuid4(), uuid4()
    document_store.save_document(KnowledgeDocument(document_id=ready_id, filename="ready.pdf", status=DocumentStatus.ready, size_bytes=1, uploaded_at=utc_now(), parent_count=1, child_count=1))
    document_store.save_document(KnowledgeDocument(document_id=failed_id, filename="failed.pdf", status=DocumentStatus.failed, size_bytes=1, uploaded_at=utc_now(), error_reason="bad"))
    children = [SearchableChildUnit(child_id=uuid4(), parent_id=parent_id, document_id=ready_id, text="retention period three years", char_count=29, ordinal=0), SearchableChildUnit(child_id=uuid4(), parent_id=uuid4(), document_id=failed_id, text="retention period", char_count=16, ordinal=0)]
    index = IndexStore(settings.data_dir, EmbeddingService(settings)); index.rebuild(children)
    results = Retriever(settings, index, document_store).search("retention period", min_score=0.01)
    assert results and all(item.document_id == ready_id for item in results)
    assert all(item.retrieval_mode == "hybrid" for item in results)
