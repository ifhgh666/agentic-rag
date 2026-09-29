from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from qdrant_client import models

from ..config import Settings


class SparseEmbeddingService:
    """FastEmbed BM25 适配器；模型只在首次编码时加载。

    When ``sparse_offline_fallback`` is enabled, FastEmbed's BM25 encoder is
    pointed at a local directory. Qdrant/bm25 does not require neural weights;
    this keeps the term-frequency encoder available when its stopword files
    cannot be downloaded from Hugging Face.
    """

    def __init__(
        self,
        settings: Settings,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.model_factory = model_factory or self._default_model_factory
        self._model: Any | None = None
        self.model_load_count = 0

    def _default_model_factory(self, model_name: str) -> Any:
        from fastembed import SparseTextEmbedding

        if self.settings.sparse_offline_fallback:
            model_path = self.settings.sparse_model_path
            if model_path is None:
                model_path = self.settings.data_dir / "models" / "qdrant-bm25-local"
            elif not model_path.is_absolute():
                model_path = self.settings.data_dir / model_path
            Path(model_path).mkdir(parents=True, exist_ok=True)
            return SparseTextEmbedding(
                model_name=model_name,
                specific_model_path=str(model_path),
                disable_stemmer=True,
            )

        return SparseTextEmbedding(model_name=model_name)

    @property
    def model(self) -> Any:
        if self._model is None:
            self._model = self.model_factory(self.settings.sparse_model)
            self.model_load_count += 1
        return self._model

    def embed_many(self, texts: Iterable[str]) -> list[models.SparseVector]:
        items = list(texts)
        if not items:
            return []
        return [self._to_sparse_vector(item) for item in self.model.embed(items)]

    def embed_one(self, text: str) -> models.SparseVector:
        values = self.embed_many([text])
        if not values:
            raise ValueError("稀疏向量编码没有返回结果。")
        return values[0]

    @staticmethod
    def _to_sparse_vector(value: Any) -> models.SparseVector:
        indices = getattr(value, "indices", None)
        weights = getattr(value, "values", None)
        if indices is None or weights is None:
            indices = value["indices"]
            weights = value["values"]
        return models.SparseVector(
            indices=[int(index) for index in indices],
            values=[float(weight) for weight in weights],
        )
