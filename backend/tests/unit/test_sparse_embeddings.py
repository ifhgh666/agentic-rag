from types import SimpleNamespace

from app.rag.sparse_embeddings import SparseEmbeddingService


class FakeModel:
    def embed(self, texts):
        return [SimpleNamespace(indices=[3, 9], values=[0.5, 1.25]) for _ in texts]


def test_sparse_embedding_service_converts_model_output(monkeypatch, settings):
    service = SparseEmbeddingService(settings, model_factory=lambda _name: FakeModel())

    values = service.embed_many(["PN8733 PWM", "VDD"])
    one = service.embed_one("技术术语")

    assert values[0].indices == [3, 9]
    assert values[0].values == [0.5, 1.25]
    assert one.indices == [3, 9]
    assert service.model_load_count == 1


def test_sparse_embedding_service_is_lazy(monkeypatch, settings):
    service = SparseEmbeddingService(settings, model_factory=lambda _name: FakeModel())
    assert service.model_load_count == 0
    service.embed_one("lazy")
    assert service.model_load_count == 1


def test_sparse_embedding_service_supports_offline_bm25_fallback(settings):
    settings.sparse_offline_fallback = True

    service = SparseEmbeddingService(settings)
    vector = service.embed_one("输入电压 data retention")

    assert vector.indices
    assert vector.values
    assert (settings.data_dir / "models" / "qdrant-bm25-local").is_dir()
