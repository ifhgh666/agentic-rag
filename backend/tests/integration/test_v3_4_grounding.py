import json
from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.rag.context_builder import ContextBuilder
from app.rag.evaluator import AnswerEvaluator
from app.rag.generator import AnswerGenerator, INSUFFICIENT_ANSWER
from app.rag.graph import AgentGraphService
from app.rag.model_provider import ModelResult
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class StaticRetriever:
    def __init__(self, results):
        self.results = results
        self.index_store = type("Index", (), {"ready": True})()

    def search(self, query, top_k=None, min_score=None):
        return self.results


class StructuredProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def complete(self, messages, *, tools=None):
        self.calls += 1
        return ModelResult(json.dumps(self.payload, ensure_ascii=False), "fake", "stub")


def _service(settings, facts, provider):
    store = DocumentStore(settings.data_dir)
    results = []
    for filename, text, score in facts:
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
    return AgentGraphService(
        settings=settings, retriever=StaticRetriever(results),
        context_builder=ContextBuilder(settings, store),
        generator=AnswerGenerator(settings, provider), evaluator=AnswerEvaluator(),
        document_store=store,
    )


def test_conflicting_evidence_keeps_both_sources_and_declines_unique_value(settings):
    first = "PX-200 的过流阈值为 16 A。"
    second = "PX-200 的过流阈值为 18 A。"
    provider = StructuredProvider({
        "is_answerable": True,
        "answer": "资料不一致：一份写 16 A，另一份写 18 A，无法确定唯一阈值。",
        "citations": [
            {"citation_id": "E1", "quote": first},
            {"citation_id": "E2", "quote": second},
        ],
        "conflict": True,
    })
    service = _service(settings, [("first.pdf", first, 0.9), ("second.pdf", second, 0.8)], provider)
    output = service.run("PX-200 的过流阈值是多少？")
    assert output.status == "completed"
    assert ("不一致" in output.final_answer or "冲突" in output.final_answer) and "无法确定" in output.final_answer
    assert {source.filename for source in output.sources} == {"first.pdf", "second.pdf"}
    assert provider.calls == 0


def test_no_or_low_relevance_evidence_does_not_call_answer_model(settings):
    class NoAnswerProvider:
        def complete(self, messages, *, tools=None):
            raise AssertionError("没有可信证据时不得调用回答模型")

    question = "完全不存在的设备参数是多少？"
    empty = _service(settings, [], NoAnswerProvider()).run(question)
    low = _service(settings, [("wrong.pdf", "无关资料", 0.001)], NoAnswerProvider()).run(question)
    assert empty.status == "fallback" and empty.final_answer == INSUFFICIENT_ANSWER
    assert low.status == "fallback" and low.final_answer == INSUFFICIENT_ANSWER
    assert empty.sources == [] and low.sources == []


def test_model_budget_exhaustion_returns_only_sourced_excerpts(settings):
    provider = StructuredProvider({"is_answerable": True, "answer": "不可调用", "citations": []})
    limited = settings.model_copy(update={"max_simple_llm_calls": 0, "max_llm_calls_per_request": 0})
    service = _service(limited, [("manual.pdf", "PX-200 的过流阈值为 16 A。", 0.9)], provider)
    result = service.run("PX-200 的过流阈值是多少？")
    assert result.status == "fallback" and result.budget_exceeded
    assert "模型调用预算已用尽" in result.final_answer
    assert "16 A" in result.final_answer and "manual.pdf" in result.final_answer
    assert result.sources and result.sources[0].filename == "manual.pdf"
    assert result.usage["model_calls"] == 0
    assert provider.calls == 0
