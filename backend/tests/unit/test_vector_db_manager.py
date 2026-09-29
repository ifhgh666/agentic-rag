from uuid import uuid4

import numpy as np

from app.rag.vector_db_manager import VectorDbManager
from app.schemas.documents import SearchableChildUnit


class FakeSparseEmbedder:
    def embed_many(self, texts):
        return [
            {"indices": [index + 1], "values": [1.0]}
            for index, _text in enumerate(texts)
        ]

    def embed_one(self, text):
        return {"indices": [1], "values": [1.0]}


def _child(document_id, parent_id, text, ordinal=0):
    return SearchableChildUnit(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        text=text,
        char_count=len(text),
        ordinal=ordinal,
    )


def test_qdrant_dense_rebuild_search_and_delete(settings):
    document_id, parent_id = uuid4(), uuid4()
    children = [
        _child(document_id, parent_id, "数据保留期限三年"),
        _child(document_id, parent_id, "管理员每年复核策略", ordinal=1),
    ]
    vectors = np.zeros((2, settings.embedding_dimension), dtype=np.float32)
    vectors[0, 0] = 1.0
    vectors[1, 1] = 1.0

    manager = VectorDbManager(settings, sparse_embedder=FakeSparseEmbedder())
    manager.rebuild(children, vectors)

    assert manager.ready
    assert manager.count == 2
    results = manager.search(vectors[0], top_k=2, sparse_vector=FakeSparseEmbedder().embed_one("数据"))
    assert results and results[0][1].child_id == children[0].child_id
    assert manager.count_for_document(document_id) == 2

    manager.delete_document(document_id)

    assert manager.count == 0
    assert not manager.ready


def test_qdrant_empty_rebuild_creates_not_ready_collection(settings):
    manager = VectorDbManager(settings, sparse_embedder=FakeSparseEmbedder())

    manager.rebuild([])

    assert manager.collection_exists
    assert not manager.ready
    assert manager.search(np.ones(settings.embedding_dimension, dtype=np.float32), 5, sparse_vector=FakeSparseEmbedder().embed_one("空")) == []


def test_qdrant_hybrid_schema_and_fusion_search(settings):
    document_id, parent_id = uuid4(), uuid4()
    children = [
        _child(document_id, parent_id, "PN8733 PWM VDD technical term"),
        _child(document_id, parent_id, "general power management", ordinal=1),
    ]
    vectors = np.zeros((2, settings.embedding_dimension), dtype=np.float32)
    vectors[0, 0] = 1.0
    vectors[1, 1] = 1.0
    sparse = FakeSparseEmbedder()

    manager = VectorDbManager(settings, sparse_embedder=sparse)
    manager.rebuild(children, vectors)

    info = manager.client.get_collection(settings.child_collection)
    assert settings.sparse_vector_name in info.config.params.sparse_vectors
    results = manager.search(vectors[0], top_k=2, sparse_vector=sparse.embed_one("PN8733"))
    assert results
    assert results[0][1].child_id == children[0].child_id
    assert manager.hybrid_ready


def test_rebuild_replaces_old_points_instead_of_accumulating(settings):
    manager = VectorDbManager(settings, sparse_embedder=FakeSparseEmbedder())
    old = _child(uuid4(), uuid4(), "旧文档内容")
    new = _child(uuid4(), uuid4(), "新文档内容")
    vector = np.zeros((1, settings.embedding_dimension), dtype=np.float32)
    vector[0, 0] = 1.0

    manager.rebuild([old], vector)
    manager.rebuild([new], vector)

    assert manager.count == 1
    assert [item.child_id for item in manager.load_children()] == [new.child_id]
    manager.client.close()
