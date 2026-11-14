"""V3 索引迁移：先预览，停止后端后显式 --apply 才备份并重解析。"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.knowledge.chunker import chunk_document
from app.knowledge.manager import DocumentManager
from app.knowledge.pdf_parser import PdfParser
from app.knowledge.stores import DocumentStore
from app.observability.logger import StructuredLogger
from app.knowledge.embeddings import EmbeddingService
from app.knowledge.index import IndexStore


def _backup(settings: Settings, store: DocumentStore) -> Path:
    target = settings.data_dir / "backups" / f"v3-1-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"
    target.mkdir(parents=True, exist_ok=False)
    for path in (store.documents_path, store.parents_path, store.children_path):
        if path.is_file():
            shutil.copy2(path, target / path.name)
    if settings.qdrant_path.is_dir():
        # QdrantClient 在本进程持有 .lock；锁文件不是索引数据，也不能在 Windows 上复制。
        shutil.copytree(settings.qdrant_path, target / "qdrant", ignore=shutil.ignore_patterns(".lock"))
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="检查或重建 V3 PDF Markdown/Parent/Child/Dense+Sparse 索引")
    parser.add_argument("--apply", action="store_true", help="备份后实际重解析并重建；执行前须停止后端")
    args = parser.parse_args()
    settings = Settings()
    store = DocumentStore(settings.data_dir)
    documents = [item for item in store.list_documents() if item.status.value == "ready"]
    pdf_parser = PdfParser()
    print(f"嵌入模式：{settings.effective_embedding_backend}；模型：{settings.embedding_model}")
    print(f"待处理文档：{len(documents)}")
    if not args.apply:
        for document in documents:
            source = Path(document.source_path or "")
            if not source.is_file():
                print(f"缺少源 PDF：{document.filename}", file=sys.stderr)
                return 1
            parents, children = chunk_document(document.document_id, pdf_parser.parse(source.read_bytes()), settings)
            print(f"{document.filename}：{len(parents)} Parent / {len(children)} Child")
        print("仅预览；未修改文档库或索引。添加 --apply 才执行。")
        return 0
    try:
        index = IndexStore(settings.data_dir, EmbeddingService(settings), document_store=store)
    except Exception as exc:
        print(f"无法独占打开 Qdrant；请先停止后端服务：{exc}", file=sys.stderr)
        return 1
    try:
        backup = _backup(settings, store)
        print(f"已备份到：{backup}")
        logger = StructuredLogger(settings.data_dir / "logs" / "app.jsonl", enabled=settings.execution_logging_enabled)
        manager = DocumentManager(settings, store, pdf_parser, index, logger)
        for document in documents:
            result = manager.process(document.document_id)
            print(f"{document.filename}：{result.status.value}；{result.parent_count} Parent / {result.child_count} Child")
            if result.status.value != "ready":
                print(f"重建中止：{result.error_reason}；原始文件在备份目录中。", file=sys.stderr)
                return 1
        if not documents:
            index.rebuild([])
        print(f"索引状态：{'就绪' if index.ready else '需重建'}；{index.rebuild_reason or '版本一致'}")
        return 0 if (index.ready or not documents) else 1
    finally:
        index.vector_db.client.close()


if __name__ == "__main__":
    raise SystemExit(main())
