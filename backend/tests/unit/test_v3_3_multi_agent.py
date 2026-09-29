from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.rag.context_builder import ContextBuilder
from app.rag.evaluator import AnswerEvaluator
from app.rag.graph import AgentGraphService
from app.rag.query_analysis import AnalysisOutcome
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class StubAnalyzer:
    def __init__(self, questions=None):
        self.questions = questions

    def analyze(self, question, prepared):
        if self.questions is None and "补充信息：" not in question:
            return AnalysisOutcome(False, [], "请说明设备型号。")
        questions = self.questions or ["PX-200 的过流阈值是多少？"]
        return AnalysisOutcome(True, questions, "")


class QueryRetriever:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []
        self.index_store = type("Index", (), {"ready": True})()

    def search(self, query, top_k=None, min_score=None):
        self.calls.append(query)
        return self.mapping.get(query, [])


class EchoGenerator:
    def generate(self, question, context):
        return f"{question}：{context}"


def _result(document_id, parent_id, content):
    return RetrievalResult(
        child_id=uuid4(), parent_id=parent_id, document_id=document_id,
        filename="guide.pdf", score=0.9, content_preview=content, text=content,
        retrieval_mode="hybrid",
    )


def _service(settings, retriever, records, analyzer, query_generator=None):
    store = DocumentStore(settings.data_dir)
    for document_id, parent_id, content in records:
        store.save_document(KnowledgeDocument(
            document_id=document_id, filename="guide.pdf", status=DocumentStatus.ready,
            size_bytes=1, uploaded_at=utc_now(),
        ))
        store.replace_chunks(document_id, [ParentContextUnit(
            parent_id=parent_id, document_id=document_id, text=content,
            char_count=len(content), ordinal=0,
        )], [])
    return AgentGraphService(
        settings=settings, retriever=retriever, context_builder=ContextBuilder(settings, store),
        generator=EchoGenerator(), evaluator=AnswerEvaluator(), document_store=store,
        query_analyzer=analyzer, query_generator=query_generator,
    )


def test_two_facts_run_independent_agents_and_merge_evidence(settings):
    first = (uuid4(), uuid4(), "PX-200 过流保护阈值为 16 A。")
    second = (uuid4(), uuid4(), "PX-200 运行记录默认保留 90 天。")
    q1, q2 = "PX-200 的过流阈值是多少？", "PX-200 记录保留多久？"
    retriever = QueryRetriever({q1: [_result(*first)], q2: [_result(*second)]})
    service = _service(settings, retriever, [first, second], StubAnalyzer([q1, q2]))

    answer = service.run("PX-200 的过流阈值和运行记录保留期分别是多少？")

    assert answer.status == "completed"
    assert set(retriever.calls) == {q1, q2}
    assert len(retriever.calls) == 2
    assert "16 A" in answer.final_answer and "90 天" in answer.final_answer
    assert len(answer.retrieved_results) == 2
    assert len(answer.sources) == 2
    assert answer.evaluation is not None
    assert answer.tool_trace.count("search_child_chunks") == 2
    assert answer.tool_trace.count("retrieve_parent_chunks") == 2

    service.query_analyzer.questions = [q1]
    follow_up = service.run(q1, thread_id=answer.thread_id)
    assert follow_up.status == "completed"
    assert "90 天" not in follow_up.final_answer
    assert len(follow_up.retrieved_results) == 1


def test_shared_parent_is_fetched_once_per_request(settings, monkeypatch):
    record = (uuid4(), uuid4(), "PX-200 阈值 16 A，恢复方法为断电复位。")
    q1, q2 = "PX-200 的阈值？", "PX-200 如何恢复？"
    retriever = QueryRetriever({q1: [_result(*record)], q2: [_result(*record)]})
    service = _service(settings, retriever, [record], StubAnalyzer([q1, q2]))
    calls = []
    original = service.document_store.get_parent

    def counted(parent_id):
        calls.append(parent_id)
        return original(parent_id)

    monkeypatch.setattr(service.document_store, "get_parent", counted)
    answer = service.run("PX-200 的阈值和恢复方法？")
    assert answer.status == "completed"
    assert calls.count(record[1]) == 1


def test_clarification_resumes_on_same_thread_without_first_search(settings):
    record = (uuid4(), uuid4(), "PX-200 的过流保护阈值为 16 A。")
    q = "PX-200 的过流阈值是多少？"
    retriever = QueryRetriever({q: [_result(*record)]})
    service = _service(settings, retriever, [record], StubAnalyzer())

    first = service.run("这个阈值是多少？", thread_id="clarify-1")
    second = service.run("是 PX-200", thread_id="clarify-1")

    assert first.status == "clarification" and first.tool_trace == []
    assert second.status == "completed" and "16 A" in second.final_answer
    assert retriever.calls == [q]
    assert service.memory.pending("clarify-1") == ""


def test_nonmatching_model_evidence_triggers_bounded_new_query(settings):
    wrong = (uuid4(), uuid4(), "PN8733 的过流阈值为 8 A。" * 20)
    right = (uuid4(), uuid4(), "PX-200 的过流阈值为 16 A。" * 20)
    retriever = QueryRetriever({"PX-200 的过流阈值是多少？": [_result(*wrong)], "PX-200 过流保护电流": [_result(*right)]})

    class Rewriter:
        def generate(self, question, previous_queries):
            return "PX-200 过流保护电流"

    service = _service(settings, retriever, [wrong, right], StubAnalyzer(["PX-200 的过流阈值是多少？"]), Rewriter())
    result = service.run("PX-200 的过流阈值是多少？")
    assert retriever.calls == ["PX-200 的过流阈值是多少？", "PX-200 过流保护电流"]
    assert "16 A" in result.final_answer
    assert "8 A" not in result.final_answer
