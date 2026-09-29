"""Check that the real local model does not select one of two conflicting PDF facts."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.config import Settings
from app.knowledge.stores import DocumentStore
from app.rag.context_builder import ContextBuilder
from app.rag.evaluator import AnswerEvaluator
from app.rag.generator import AnswerGenerator, INSUFFICIENT_ANSWER
from app.rag.graph import AgentGraphService
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class StaticRetriever:
    def __init__(self, results):
        self.results = results
        self.index_store = type("Index", (), {"ready": True})()

    def search(self, query, top_k=None, min_score=None):
        return self.results


def main() -> dict:
    configured = Settings()
    if configured.llm_provider != "ollama":
        raise RuntimeError("仅使用本地 Ollama 做冲突验收")
    with TemporaryDirectory(prefix="v3-4-conflict-") as temp_dir:
        settings = configured.model_copy(update={"data_dir": Path(temp_dir)})
        store = DocumentStore(settings.data_dir)
        results = []
        for filename, text, score in [
            ("version-a.pdf", "PX-200 的过流保护阈值是 16 A。", 0.9),
            ("version-b.pdf", "PX-200 的过流保护阈值是 18 A。", 0.8),
        ]:
            document_id, parent_id = uuid4(), uuid4()
            store.save_document(KnowledgeDocument(
                document_id=document_id, filename=filename, status=DocumentStatus.ready,
                size_bytes=1, uploaded_at=utc_now(),
            ))
            store.replace_chunks(document_id, [ParentContextUnit(
                parent_id=parent_id, document_id=document_id, text=text,
                char_count=len(text), ordinal=0,
            )], [])
            results.append(RetrievalResult(
                child_id=uuid4(), parent_id=parent_id, document_id=document_id,
                filename=filename, score=score, content_preview=text, text=text,
                retrieval_mode="hybrid",
            ))
        service = AgentGraphService(
            settings=settings, retriever=StaticRetriever(results),
            context_builder=ContextBuilder(settings, store),
            generator=AnswerGenerator(settings), evaluator=AnswerEvaluator(),
            document_store=store,
        )
        result = service.run("PX-200 的过流保护阈值是多少？")
        if result.status == "completed":
            safe = "无法确定" in result.final_answer or "不一致" in result.final_answer or "冲突" in result.final_answer
            safe = safe and {item.filename for item in result.sources} == {"version-a.pdf", "version-b.pdf"}
        else:
            safe = result.final_answer == INSUFFICIENT_ANSWER
        report = {
            "answer": result.final_answer,
            "status": result.status,
            "sources": [item.filename for item in result.sources],
            "validation": [item.get("validation_status") for item in result.model_trace],
            "usage": result.usage,
        }
        print(json.dumps(report, ensure_ascii=True))
        if not safe:
            raise AssertionError("冲突资料被错误地当作唯一阈值")
        if result.usage["cloud_calls"]:
            raise AssertionError("冲突验收出现云端模型调用")
        return report


if __name__ == "__main__":
    main()
