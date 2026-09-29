"""混合索引适配层，并在检索前验证索引与文档/嵌入版本一致。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import Lock

import numpy as np

from ..knowledge.stores import DocumentStore
from ..schemas.documents import SearchableChildUnit
from .embeddings import EmbeddingService
from .vector_db_manager import VectorDbManager


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
