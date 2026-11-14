import numpy as np
import pytest

from app.knowledge.embeddings import EmbeddingService


def test_embedding_is_normalized_and_repeatable(settings):
    service = EmbeddingService(settings)
    vector = service.embed_one("数据保留期限")
    assert vector.shape == (settings.embedding_dimension,)
    assert np.isclose(np.linalg.norm(vector), 1.0)
    assert np.allclose(vector, service.embed_one("数据保留期限"))


def test_missing_real_model_does_not_silently_fall_back_to_hash(settings):
    real = settings.model_copy(update={"embedding_backend": "fastembed", "embedding_model": "model-that-does-not-exist"})
    with pytest.raises(RuntimeError, match="本地 Dense 模型不可用"):
        EmbeddingService(real).embed_one("设备维护周期")
