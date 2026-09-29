"""可切换的 Dense Embedding；生产默认 ONNX，测试显式使用确定性向量。"""

import hashlib
import re

import numpy as np

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
