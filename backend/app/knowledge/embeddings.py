"""Dense and sparse embedding adapters."""
from __future__ import annotations

import hashlib
import numpy as np
import re
from collections.abc import Iterable
from pathlib import Path
from qdrant_client import models
from typing import Any, Callable
from ..config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    @property
    def backend(self) -> str:
        return self.settings.effective_embedding_backend

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(
                model_name=self.settings.embedding_model,
                cache_dir=str(self.settings.embedding_cache_path),
                local_files_only=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"本地 Dense 模型不可用：{self.settings.embedding_model}。"
                "请先下载模型，或在离线测试中设置 EMBEDDING_BACKEND=deterministic。"
            ) from exc
        return self._model

    def embed_many(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.settings.embedding_dimension), dtype=np.float32)
        if self.backend == "deterministic":
            return np.vstack([self._deterministic(text) for text in texts]).astype(np.float32)
        model = self._load_model()
        values = np.vstack([np.asarray(value, dtype=np.float32) for value in model.embed(texts)])
        expected = (len(texts), self.settings.embedding_dimension)
        if values.shape != expected:
            raise ValueError(f"Dense 向量维度不匹配：配置 {expected}，模型返回 {values.shape}。")
        norms = np.linalg.norm(values, axis=1, keepdims=True)
        return values / np.maximum(norms, 1e-12)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed_many([text])[0]

    def _deterministic(self, text: str) -> np.ndarray:
        vector = np.zeros(self.settings.embedding_dimension, dtype=np.float32)
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower(), flags=re.UNICODE)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.settings.embedding_dimension
            vector[index] += 1.0
            if len(token) > 2:
                for offset in range(len(token) - 1):
                    pair_digest = hashlib.sha256(token[offset : offset + 2].encode()).digest()
                    pair_index = int.from_bytes(pair_digest[:4], "big") % self.settings.embedding_dimension
                    vector[pair_index] += 0.25
        norm = np.linalg.norm(vector)
        if norm == 0:
            vector[0] = 1.0
            norm = 1.0
        return vector / norm

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
