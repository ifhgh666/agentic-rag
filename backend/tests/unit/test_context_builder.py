from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.knowledge.retrieval import ContextBuilder
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


def test_context_builder_deduplicates_parent(settings):
    store = DocumentStore(settings.data_dir)
    document_id, parent_id = uuid4(), uuid4()
    store.save_document(KnowledgeDocument(document_id=document_id, filename="a.pdf", status=DocumentStatus.ready, size_bytes=1, uploaded_at=utc_now(), parent_count=1, child_count=2))
    store.replace_chunks(document_id, [ParentContextUnit(parent_id=parent_id, document_id=document_id, text="完整内容", char_count=4, ordinal=0)], [])
    results = [RetrievalResult(child_id=uuid4(), parent_id=parent_id, document_id=document_id, filename="a.pdf", score=.9, content_preview="完整内容"), RetrievalResult(child_id=uuid4(), parent_id=parent_id, document_id=document_id, filename="a.pdf", score=.8, content_preview="完整内容")]
    context, sources = ContextBuilder(settings, store).build(results)
    assert context.count("完整内容") == 1 and len(sources) == 1

