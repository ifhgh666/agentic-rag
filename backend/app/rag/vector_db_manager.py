from __future__ import annotations

from pathlib import Path
from threading import Lock
from uuid import UUID

import numpy as np
from qdrant_client import QdrantClient, models

from ..config import Settings
from ..schemas.documents import SearchableChildUnit
from .sparse_embeddings import SparseEmbeddingService


class VectorDbManager:
    """本地 Qdrant Child 索引管理器，支持 Dense + BM25 Sparse 混合检索。"""

    def __init__(self, settings: Settings, sparse_embedder: SparseEmbeddingService | None = None):
        self.settings = settings
        self.storage_path: Path = settings.qdrant_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.collection_name = settings.child_collection
        self.dense_vector_name = settings.dense_vector_name
        self.sparse_vector_name = settings.sparse_vector_name
        self.sparse_embedder = sparse_embedder or SparseEmbeddingService(settings)
        self._lock = Lock()
        self.client = QdrantClient(path=str(self.storage_path))
        self._ensure_collection()

    @property
    def collection_exists(self) -> bool:
        return self.client.collection_exists(self.collection_name)

    @property
    def count(self) -> int:
        if not self.collection_exists:
            return 0
        return int(self.client.count(collection_name=self.collection_name, exact=True).count)

    @property
    def ready(self) -> bool:
        return self.collection_exists and self.count > 0

    @property
    def hybrid_ready(self) -> bool:
        if not self.collection_exists:
            return False
        try:
            info = self.client.get_collection(self.collection_name)
            sparse_vectors = info.config.params.sparse_vectors or {}
            return self.sparse_vector_name in sparse_vectors
        except (AttributeError, KeyError, TypeError):
            return False

    def _ensure_collection(self) -> None:
        if self.collection_exists:
            return
        self._create_hybrid_collection()

    def _create_hybrid_collection(self) -> None:
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                self.dense_vector_name: models.VectorParams(
                    size=self.settings.embedding_dimension,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                self.sparse_vector_name: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )

    def _schema_compatible(self) -> bool:
        if not self.collection_exists or not self.hybrid_ready:
            return False
        vectors = self.client.get_collection(self.collection_name).config.params.vectors
        return (
            isinstance(vectors, dict)
            and self.dense_vector_name in vectors
            and vectors[self.dense_vector_name].size == self.settings.embedding_dimension
        )

    def _point_ids(self) -> list[str]:
        if not self.collection_exists:
            return []
        ids: list[str] = []
        offset = None
        while True:
            records, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            ids.extend(str(item.id) for item in records)
            if offset is None:
                return ids

    def rebuild(
        self,
        children: list[SearchableChildUnit],
        vectors: np.ndarray | None = None,
        sparse_vectors: list[models.SparseVector | dict] | None = None,
    ) -> None:
        """原子重建当前集合；每个 Child Point 同时保存 Dense 和 Sparse 向量。"""
        if children:
            if vectors is None:
                raise ValueError("重建 Qdrant Dense 索引必须提供 vectors。")
            values = np.asarray(vectors, dtype=np.float32)
            expected_shape = (len(children), self.settings.embedding_dimension)
            if values.shape != expected_shape:
                raise ValueError(f"向量形状不匹配：期望 {expected_shape}，实际 {values.shape}。")
            if sparse_vectors is None:
                sparse_vectors = self.sparse_embedder.embed_many(child.text for child in children)
            if len(sparse_vectors) != len(children):
                raise ValueError("Sparse 向量数量必须与 Child 数量一致。")
            sparse_values = [self._coerce_sparse_vector(item) for item in sparse_vectors]
        else:
            values = np.zeros((0, self.settings.embedding_dimension), dtype=np.float32)
            sparse_values = []

        with self._lock:
            # Qdrant local 在同一路径 delete_collection/create_collection 后可能仍保留旧 Point。
            # 对兼容 schema 直接按 ID 清空；不兼容时重建 schema 后再次按 ID 清空。
            if self.collection_exists and not self._schema_compatible():
                self.client.delete_collection(self.collection_name)
            if not self.collection_exists:
                self._create_hybrid_collection()
            existing_ids = self._point_ids()
            for start in range(0, len(existing_ids), 256):
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=existing_ids[start : start + 256]),
                    wait=True,
                )
            if self.count:
                raise RuntimeError("Qdrant 旧 Point 未完全清除，重建已中止。")
            if not children:
                return

            points = [
                models.PointStruct(
                    id=str(child.child_id),
                    vector={
                        self.dense_vector_name: values[index].tolist(),
                        self.sparse_vector_name: sparse_values[index],
                    },
                    payload=self._payload(child),
                )
                for index, child in enumerate(children)
            ]
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
            if self.count != len(children):
                raise RuntimeError("Qdrant 重建后的 Point 数量与 Child 数量不一致。")

    def search(
        self,
        vector: np.ndarray,
        top_k: int,
        sparse_vector: models.SparseVector | dict | None = None,
    ) -> list[tuple[float, SearchableChildUnit]]:
        if top_k <= 0 or not self.ready or not self.hybrid_ready:
            return []
        query_vector = np.asarray(vector, dtype=np.float32).reshape(-1)
        if query_vector.shape != (self.settings.embedding_dimension,):
            raise ValueError(
                f"查询向量形状不匹配：期望 {(self.settings.embedding_dimension,)}, 实际 {query_vector.shape}。"
            )
        if sparse_vector is None:
            raise ValueError("混合检索必须提供 Sparse 查询向量。")
        sparse_query = self._coerce_sparse_vector(sparse_vector)
        candidate_limit = max(top_k * 2, 10)
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=query_vector.tolist(),
                    using=self.dense_vector_name,
                    limit=candidate_limit,
                ),
                models.Prefetch(
                    query=sparse_query,
                    using=self.sparse_vector_name,
                    limit=candidate_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.DBSF),
            limit=top_k,
            with_payload=True,
        )
        return [
            (float(point.score), self._child_from_payload(point.payload or {}))
            for point in response.points
            if point.payload
        ]

    def load_children(self) -> list[SearchableChildUnit]:
        """从现有 Qdrant payload 读取 Child，用于 Dense-only collection 迁移。"""
        if not self.collection_exists:
            return []
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=max(self.count, 1),
            with_payload=True,
            with_vectors=False,
        )
        return [self._child_from_payload(point.payload or {}) for point in records if point.payload]

    def delete_document(self, document_id: UUID) -> None:
        if not self.collection_exists:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
            wait=True,
        )

    def count_for_document(self, document_id: UUID) -> int:
        if not self.collection_exists:
            return 0
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=str(document_id)),
                    )
                ]
            ),
            exact=True,
        )
        return int(result.count)

    @staticmethod
    def _coerce_sparse_vector(value: models.SparseVector | dict) -> models.SparseVector:
        if isinstance(value, models.SparseVector):
            return value
        return models.SparseVector(
            indices=[int(index) for index in value["indices"]],
            values=[float(weight) for weight in value["values"]],
        )

    @staticmethod
    def _payload(child: SearchableChildUnit) -> dict:
        payload = child.model_dump(mode="json")
        payload["child_id"] = str(child.child_id)
        payload["parent_id"] = str(child.parent_id)
        payload["document_id"] = str(child.document_id)
        payload["page_content"] = child.text
        return payload

    @staticmethod
    def _child_from_payload(payload: dict) -> SearchableChildUnit:
        return SearchableChildUnit.model_validate(
            {
                "child_id": payload["child_id"],
                "parent_id": payload["parent_id"],
                "document_id": payload["document_id"],
                "section_title": payload.get("section_title", ""),
                "text": payload.get("text", payload.get("page_content", "")),
                "char_count": payload.get("char_count", 0),
                "ordinal": payload.get("ordinal", 0),
                "vector_position": payload.get("vector_position"),
            }
        )
