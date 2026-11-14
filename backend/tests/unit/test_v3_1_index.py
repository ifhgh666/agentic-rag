from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.knowledge.embeddings import EmbeddingService
from app.knowledge.index import IndexStore
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, SearchableChildUnit


def _child(document_id):
    text = "设备上电前检查接地线和负载连接"
    return SearchableChildUnit(
        child_id=uuid4(), parent_id=uuid4(), document_id=document_id,
        text=text, char_count=len(text), ordinal=0,
    )


def test_index_manifest_rejects_changed_embedding_configuration(settings):
    store = DocumentStore(settings.data_dir)
    document_id = uuid4()
    store.save_document(KnowledgeDocument(
        document_id=document_id, filename="guide.pdf", status=DocumentStatus.ready,
        size_bytes=0, uploaded_at=utc_now(),
    ))
    child = _child(document_id)
    store.replace_chunks(document_id, [], [child])
    index = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    index.rebuild([child])
    assert index.ready
    assert (settings.data_dir / "index" / "manifest.json").exists()
    index.vector_db.client.close()

    changed = settings.model_copy(update={"embedding_model": "different-model"})
    stale = IndexStore(changed.data_dir, EmbeddingService(changed), document_store=store)
    assert stale.needs_rebuild
    assert not stale.ready
    assert stale.search("接地线", 5, 0.0) == []
    stale.vector_db.client.close()


def test_index_manifest_rejects_stale_document_points(settings):
    store = DocumentStore(settings.data_dir)
    document_id = uuid4()
    store.save_document(KnowledgeDocument(
        document_id=document_id, filename="guide.pdf", status=DocumentStatus.ready,
        size_bytes=0, uploaded_at=utc_now(),
    ))
    child = _child(document_id)
    store.replace_chunks(document_id, [], [child])
    index = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    index.rebuild([child])
    index.vector_db.client.close()

    store.delete_document(document_id)
    stale = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    assert stale.needs_rebuild
    assert not stale.ready
    stale.vector_db.client.close()


def test_missing_manifest_and_changed_source_pdf_require_rebuild(settings):
    source = settings.data_dir / "source.pdf"
    source.write_bytes(b"original")
    store = DocumentStore(settings.data_dir)
    document_id = uuid4()
    store.save_document(KnowledgeDocument(
        document_id=document_id, filename="guide.pdf", status=DocumentStatus.ready,
        size_bytes=8, uploaded_at=utc_now(), source_path=str(source),
    ))
    child = _child(document_id)
    store.replace_chunks(document_id, [], [child])
    index = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    index.rebuild([child])
    index.vector_db.client.close()

    source.write_bytes(b"modified")
    changed = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    assert changed.needs_rebuild and not changed.ready
    changed.vector_db.client.close()

    (settings.data_dir / "index" / "manifest.json").unlink()
    missing = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    assert missing.needs_rebuild and not missing.ready
    missing.vector_db.client.close()
