"""隔离的本地 Ollama 双事实编排验收，不打开正式 Qdrant。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from app.config import Settings
from app.knowledge.stores import DocumentStore
from app.knowledge.retrieval import ContextBuilder
from app.core.answering import AnswerEvaluator, AnswerGenerator
from app.rag.graph import AgentGraphService
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class LocalRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []
        self.index_store = type("Index", (), {"ready": True})()

    def search(self, query, top_k=None, min_score=None):
        self.calls.append(query)
        if "过流" in query or "阈值" in query:
            return [self.results[0]]
        if "记录" in query or "保留" in query or "保存" in query:
            return [self.results[1]]
        return []


def main() -> dict:
    configured = Settings()
    if configured.llm_provider != "ollama":
        raise RuntimeError("真机验收只能使用本地 Ollama")
    with TemporaryDirectory(prefix="v3-3-smoke-") as temp_dir:
        settings = configured.model_copy(update={"data_dir": Path(temp_dir)})
        store = DocumentStore(settings.data_dir)
        results = []
        for filename, content in [
            ("protection.pdf", "PX-200 的过流保护阈值是 16 A。"),
            ("records.pdf", "PX-200 的运行记录默认保留 90 天。"),
        ]:
            document_id, parent_id = uuid4(), uuid4()
            store.save_document(KnowledgeDocument(
                document_id=document_id, filename=filename, status=DocumentStatus.ready,
                size_bytes=1, uploaded_at=utc_now(),
            ))
            store.replace_chunks(document_id, [ParentContextUnit(
                parent_id=parent_id, document_id=document_id, text=content,
                char_count=len(content), ordinal=0,
            )], [])
            results.append(RetrievalResult(
                child_id=uuid4(), parent_id=parent_id, document_id=document_id,
                filename=filename, score=0.9, content_preview=content, text=content,
                retrieval_mode="hybrid",
            ))
        retriever = LocalRetriever(results)
        service = AgentGraphService(
            settings=settings, retriever=retriever, context_builder=ContextBuilder(settings, store),
            generator=AnswerGenerator(settings), evaluator=AnswerEvaluator(), document_store=store,
        )
        output = service.run("PX-200 的过流保护阈值是多少，以及运行记录默认保留多久？", thread_id="v3-3-smoke")
        if len(retriever.calls) != 2 or len(output.sources) != 2:
            raise AssertionError(
                f"未分别召回两组证据：queries={retriever.calls}, sources={len(output.sources)}, "
                f"status={output.status}, questions={output.questions}, usage={output.usage}, "
                f"answer={output.final_answer}, model_trace={output.model_trace}"
            )
        if "16" not in output.final_answer or "90" not in output.final_answer:
            raise AssertionError(f"双事实答案不完整：{output.final_answer}")
        split_queries = list(retriever.calls)
        unclear = service.run("这个阈值是多少？", thread_id="v3-3-clarify")
        clarified = service.run("我问的是 PX-200 的过流保护阈值。", thread_id="v3-3-clarify")
        if unclear.status != "clarification" or unclear.tool_trace:
            raise AssertionError("含糊问题未暂停检索并请求澄清")
        if clarified.status != "completed" or "16" not in clarified.final_answer:
            raise AssertionError("同 thread 补充信息后未恢复检索并回答")
        report = {
            "answer": output.final_answer,
            "queries": split_queries,
            "sources": [source.filename for source in output.sources],
            "model_calls": [{"node": item["node"], "reason": item["reason"], "input_tokens": item.get("input_tokens"), "output_tokens": item.get("output_tokens")} for item in output.model_trace],
            "clarification": unclear.final_answer,
            "clarified_answer": clarified.final_answer,
            "usage": output.usage,
            "clarification_usage": unclear.usage,
            "clarified_usage": clarified.usage,
        }
        if output.usage["model_calls"] > 4 or clarified.usage["model_calls"] > 2:
            raise AssertionError("多问题或追问超过模型调用预算")
        if any(item["cloud_calls"] for item in (output.usage, unclear.usage, clarified.usage)):
            raise AssertionError("本地 Ollama 验收出现云端模型调用")
        print(json.dumps(report, ensure_ascii=False))
        return report


if __name__ == "__main__":
    main()
