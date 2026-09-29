import json
from pathlib import Path
from threading import Lock
from uuid import UUID

from ..schemas.documents import KnowledgeDocument, ParentContextUnit, SearchableChildUnit


class DocumentStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_path = data_dir / "documents.json"
        self.parents_path = data_dir / "parents.json"
        self.children_path = data_dir / "children.json"
        self._lock = Lock()

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, path: Path, values: list[dict]) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def list_documents(self) -> list[KnowledgeDocument]:
        values = [KnowledgeDocument.model_validate(item) for item in self._read(self.documents_path)]
        return sorted(values, key=lambda item: item.uploaded_at, reverse=True)

    def get_document(self, document_id: UUID) -> KnowledgeDocument | None:
        return next((item for item in self.list_documents() if item.document_id == document_id), None)

    def save_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        with self._lock:
            values = self._read(self.documents_path)
            payload = document.model_dump(mode="json")
            replaced = False
            for index, item in enumerate(values):
                if item.get("document_id") == str(document.document_id):
                    values[index] = payload
                    replaced = True
                    break
            if not replaced:
                values.append(payload)
            self._write(self.documents_path, values)
        return document

    def delete_document(self, document_id: UUID) -> None:
        with self._lock:
            self._write(
                self.documents_path,
                [item for item in self._read(self.documents_path) if item.get("document_id") != str(document_id)],
            )
            self._write(
                self.parents_path,
                [item for item in self._read(self.parents_path) if item.get("document_id") != str(document_id)],
            )
            self._write(
                self.children_path,
                [item for item in self._read(self.children_path) if item.get("document_id") != str(document_id)],
            )

    def replace_chunks(
        self, document_id: UUID, parents: list[ParentContextUnit], children: list[SearchableChildUnit]
    ) -> None:
        with self._lock:
            parent_values = [item for item in self._read(self.parents_path) if item.get("document_id") != str(document_id)]
            child_values = [item for item in self._read(self.children_path) if item.get("document_id") != str(document_id)]
            parent_values.extend(item.model_dump(mode="json") for item in parents)
            child_values.extend(item.model_dump(mode="json") for item in children)
            self._write(self.parents_path, parent_values)
            self._write(self.children_path, child_values)

    def list_parents(self, document_id: UUID | None = None) -> list[ParentContextUnit]:
        values = [ParentContextUnit.model_validate(item) for item in self._read(self.parents_path)]
        if document_id:
            values = [item for item in values if item.document_id == document_id]
        return values

    def list_children(self, document_id: UUID | None = None, ready_only: bool = False) -> list[SearchableChildUnit]:
        values = [SearchableChildUnit.model_validate(item) for item in self._read(self.children_path)]
        if document_id:
            values = [item for item in values if item.document_id == document_id]
        if ready_only:
            ready_ids = {item.document_id for item in self.list_documents() if item.status.value == "ready"}
            values = [item for item in values if item.document_id in ready_ids]
        return values

    def get_parent(self, parent_id: UUID) -> ParentContextUnit | None:
        return next((item for item in self.list_parents() if item.parent_id == parent_id), None)

