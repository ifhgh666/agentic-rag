from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from ..config import Settings
from ..observability.logger import StructuredLogger
from ..schemas.documents import DocumentStatus, KnowledgeDocument
from .chunker import chunk_document
from .pdf_parser import PdfParser
from .stores import DocumentStore


class DocumentManager:
    def __init__(self, settings: Settings, store: DocumentStore, parser: PdfParser, index_store, logger: StructuredLogger):
        self.settings = settings
        self.store = store
        self.parser = parser
        self.index_store = index_store
        self.logger = logger

    def create_upload(self, filename: str, content: bytes) -> KnowledgeDocument:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("只支持 PDF 文件。")
        if not content:
            raise ValueError("上传文件为空。")
        if len(content) > self.settings.max_upload_bytes:
            raise ValueError("上传文件超过 25 MB 限制。")
        document_id = uuid4()
        document_dir = self.settings.data_dir / "documents" / str(document_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        source_path = document_dir / "source.pdf"
        source_path.write_bytes(content)
        document = KnowledgeDocument(
            document_id=document_id,
            filename=Path(filename).name,
            status=DocumentStatus.processing,
            size_bytes=len(content),
            uploaded_at=datetime.now(timezone.utc),
            source_path=str(source_path),
        )
        self.store.save_document(document)
        return document

    def process(self, document_id: UUID) -> KnowledgeDocument:
        document = self.store.get_document(document_id)
        if not document:
            raise ValueError("文档不存在。")
        try:
            content = Path(document.source_path or "").read_bytes()
            parsed = self.parser.parse(content)
            parents, children = chunk_document(document_id, parsed, self.settings)
            document_dir = self.settings.data_dir / "documents" / str(document_id)
            markdown_path = document_dir / "extracted.md"
            markdown_path.write_text(parsed.text, encoding="utf-8")
            self.store.replace_chunks(document_id, parents, children)
            ready = document.model_copy(
                update={
                    "status": DocumentStatus.ready,
                    "processed_at": datetime.now(timezone.utc),
                    "parent_count": len(parents),
                    "child_count": len(children),
                    "error_reason": None,
                    "markdown_path": str(markdown_path),
                }
            )
            self.store.save_document(ready)
            self.index_store.rebuild(self.store.list_children(ready_only=True))
            self.logger.log("INFO", "knowledge.manager", "文档处理完成", document_id)
            return ready
        except Exception as exc:
            failed = document.model_copy(
                update={
                    "status": DocumentStatus.failed,
                    "processed_at": datetime.now(timezone.utc),
                    "error_reason": str(exc),
                }
            )
            self.store.save_document(failed)
            self.logger.log("ERROR", "knowledge.manager", "文档处理失败", document_id, error={"message": str(exc)})
            return failed

    def delete(self, document_id: UUID) -> None:
        document = self.store.get_document(document_id)
        if not document:
            raise KeyError("文档不存在。")
        self.store.delete_document(document_id)
        document_dir = self.settings.data_dir / "documents" / str(document_id)
        if document_dir.exists():
            for child in document_dir.iterdir():
                if child.is_file():
                    child.unlink()
            document_dir.rmdir()
        self.index_store.rebuild(self.store.list_children(ready_only=True))
        self.logger.log("INFO", "knowledge.manager", "文档已删除", document_id)
