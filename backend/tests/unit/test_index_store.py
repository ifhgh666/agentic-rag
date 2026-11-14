import json
from uuid import uuid4

import numpy as np

from app.knowledge.embeddings import EmbeddingService
from app.knowledge.index import IndexStore
from app.schemas.documents import SearchableChildUnit


def test_index_store_rebuild_and_search(settings):
    store = IndexStore(settings.data_dir, EmbeddingService(settings))
    document_id, parent_id = uuid4(), uuid4()
    children = [SearchableChildUnit(child_id=uuid4(), parent_id=parent_id, document_id=document_id, text="数据保留期限三年", char_count=8, ordinal=0)]
    store.rebuild(children)
    assert store.ready
    results = store.search("数据保留期限", 5, 0.1)
    assert results and results[0][1].parent_id == parent_id
    assert store.search("数据保留期限", 5, 1.1) == []


def test_index_store_migrates_legacy_numpy_metadata_to_qdrant(settings):
    document_id, parent_id = uuid4(), uuid4()
    child = SearchableChildUnit(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        text="legacy dense vector",
        char_count=19,
        ordinal=0,
        vector_position=0,
    )
    index_dir = settings.data_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    legacy_vector = np.zeros((1, settings.embedding_dimension), dtype=np.float32)
    legacy_vector[0, 0] = 1.0
    np.save(index_dir / "vectors.npy", legacy_vector)
    (index_dir / "children.json").write_text(
        json.dumps([child.model_dump(mode="json")]), encoding="utf-8"
    )

    store = IndexStore(settings.data_dir, EmbeddingService(settings))

    assert store.ready
    sparse_query = store.vector_db.sparse_embedder.embed_one(child.text)
    assert store.vector_db.search(legacy_vector[0], 1, sparse_query)[0][1].child_id == child.child_id
