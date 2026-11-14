"""Index manifests, vector storage and lifecycle."""
from __future__ import annotations

import hashlib
import json
import numpy as np
from pathlib import Path
from qdrant_client import QdrantClient, models
from threading import Lock
from uuid import UUID
from ..config import Settings
from .embeddings import EmbeddingService, SparseEmbeddingService
from .stores import DocumentStore
from ..schemas.documents import SearchableChildUnit


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

INDEX_SCHEMA_VERSION = 3

PARSER_VERSION = "pymupdf4llm-page-markdown-v3-1"

CHUNKER_VERSION = "markdown-hierarchy-balanced-v3-1"

def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _children_digest(children: list[SearchableChildUnit]) -> str:
    records = [
        {
            "child_id": str(item.child_id),
            "parent_id": str(item.parent_id),
            "document_id": str(item.document_id),
            "section_title": item.section_title,
            "text": item.text,
            "char_count": item.char_count,
            "ordinal": item.ordinal,
        }
        for item in children
    ]
    return _digest(sorted(records, key=lambda item: item["child_id"]))

class IndexStore:
    """保持检索接口不变；过期或混合版本索引一律 fail closed。"""

    def __init__(self, data_dir: Path, embedder: EmbeddingService, document_store: DocumentStore | None = None):
        self.index_dir = data_dir / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.vectors_path = self.index_dir / "vectors.npy"
        self.metadata_path = self.index_dir / "children.json"
        self.manifest_path = self.index_dir / "manifest.json"
        self.embedder = embedder
        self.document_store = document_store
        self.vector_db = VectorDbManager(embedder.settings)
        self._lock = Lock()
        self._children: list[SearchableChildUnit] = []
        self.needs_rebuild = False
        self.rebuild_reason = ""
        self._load_and_migrate_legacy_index()
        self._validate_manifest()

    @property
    def ready(self) -> bool:
        return not self.needs_rebuild and self.vector_db.ready and self.vector_db.hybrid_ready

    @property
    def retrieval_mode(self) -> str:
        return "hybrid"

    @property
    def version(self) -> str:
        """Manifest content changes after every completed rebuild; unsuitable indexes are never cached."""
        if not self.ready:
            return ""
        try:
            return hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        except OSError:
            return ""

    def _signature(self) -> dict[str, object]:
        settings = self.embedder.settings
        return {
            "schema": INDEX_SCHEMA_VERSION,
            "parser": PARSER_VERSION,
            "chunker": CHUNKER_VERSION,
            "embedding_backend": self.embedder.backend,
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "parent_chunk_size": settings.parent_chunk_size,
            "child_chunk_size": settings.child_chunk_size,
            "child_chunk_overlap": settings.child_chunk_overlap,
            "sparse_model": settings.sparse_model,
            "collection": settings.child_collection,
            "dense_vector": settings.dense_vector_name,
            "sparse_vector": settings.sparse_vector_name,
        }

    def _documents_digest(self) -> str | None:
        if self.document_store is None:
            return None
        documents = [item for item in self.document_store.list_documents() if item.status.value == "ready"]
        records: list[dict[str, object]] = []
        for item in documents:
            source = Path(item.source_path) if item.source_path else None
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest() if source and source.is_file() else None
            records.append({"document_id": str(item.document_id), "source_sha256": source_hash})
        return _digest(sorted(records, key=lambda item: item["document_id"]))

    def _manifest(self, children: list[SearchableChildUnit]) -> dict[str, object]:
        return {
            "signature": self._signature(),
            "point_count": len(children),
            "children_sha256": _children_digest(children),
            "documents_sha256": self._documents_digest(),
        }

    def _validate_manifest(self) -> None:
        self.needs_rebuild = False
        self.rebuild_reason = ""
        if not self.vector_db.ready:
            if self.document_store and self.document_store.list_children(ready_only=True):
                self.needs_rebuild, self.rebuild_reason = True, "文档已有 Child，但混合索引为空"
            return
        if not self.vector_db.hybrid_ready:
            self.needs_rebuild, self.rebuild_reason = True, "Qdrant 缺少 Sparse 向量"
            return
        try:
            saved = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.needs_rebuild, self.rebuild_reason = True, "缺少或无法读取 V3 索引清单"
            return
        if saved.get("signature") != self._signature():
            self.needs_rebuild, self.rebuild_reason = True, "解析/分块/嵌入配置版本已变化"
            return
        try:
            points = self.vector_db.load_children()
            expected = self._manifest(points)
            if (
                saved.get("point_count") != self.vector_db.count
                or saved.get("children_sha256") != expected["children_sha256"]
                or saved.get("documents_sha256") != expected["documents_sha256"]
            ):
                self.needs_rebuild, self.rebuild_reason = True, "索引 Point 或源 PDF 已变化"
                return
            if self.document_store and _children_digest(self.document_store.list_children(ready_only=True)) != expected["children_sha256"]:
                self.needs_rebuild, self.rebuild_reason = True, "文档库 Child 与 Qdrant 不一致"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.needs_rebuild, self.rebuild_reason = True, f"索引校验失败：{type(exc).__name__}"

    def _load_and_migrate_legacy_index(self) -> None:
        """仅在没有可用 Qdrant Point 时迁移旧 FAISS 伴随文件。"""
        if self.vector_db.ready:
            return
        try:
            values = json.loads(self.metadata_path.read_text(encoding="utf-8")) if self.metadata_path.exists() else []
            children = [SearchableChildUnit.model_validate(item) for item in values]
            legacy_vectors = np.load(self.vectors_path) if self.vectors_path.exists() else None
        except Exception:
            children, legacy_vectors = [], None
        if not children:
            return
        if legacy_vectors is not None and legacy_vectors.shape == (
            len(children), self.embedder.settings.embedding_dimension,
        ):
            self._children = children
            self.vector_db.rebuild(children, legacy_vectors)
            self._write_manifest(children)
            return
        self.rebuild(children)

    def _write_manifest(self, children: list[SearchableChildUnit]) -> None:
        temp = self.manifest_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self._manifest(children), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.manifest_path)

    def rebuild(self, children: list[SearchableChildUnit]) -> None:
        with self._lock:
            self.needs_rebuild = True
            self.rebuild_reason = "正在重建索引"
            values = [item.model_copy(update={"vector_position": index}) for index, item in enumerate(children)]
            vectors = self.embedder.embed_many([item.text for item in values])
            self.vector_db.rebuild(values, vectors)
            self._children = values
            self._write_manifest(values)
            self._validate_manifest()

    def search(self, query: str, top_k: int, min_score: float) -> list[tuple[float, SearchableChildUnit]]:
        if not self.ready:
            return []
        vector = self.embedder.embed_one(query)
        sparse_vector = self.vector_db.sparse_embedder.embed_one(query)
        pairs = self.vector_db.search(vector, top_k, sparse_vector)
        return [(score, child) for score, child in pairs if score >= min_score]
