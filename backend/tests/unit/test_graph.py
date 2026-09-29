from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.rag.context_builder import ContextBuilder
from app.rag.evaluator import AnswerEvaluator
from app.rag.generator import INSUFFICIENT_ANSWER
from app.rag.graph import AgentGraphService
from app.rag.nodes import fallback_response
from app.rag.query_planner import RuleBasedQueryGenerator
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class FakeRetriever:
    def __init__(self, results):
        self.results = results

        class Index:
            ready = True

        self.index_store = Index()

    def search(self, query, top_k=None, min_score=None):
        return self.results


class SequenceRetriever(FakeRetriever):
    def __init__(self, results_by_call):
        super().__init__(results_by_call[0] if results_by_call else [])
        self.results_by_call = list(results_by_call)

    def search(self, query, top_k=None, min_score=None):
        self.calls = getattr(self, "calls", []) + [query]
        if self.results_by_call:
            return self.results_by_call.pop(0)
        return []


class EmptyRetriever(FakeRetriever):
    def __init__(self):
        super().__init__([])
        self.index_store.ready = False


class FakeGenerator:
    def generate(self, question, context):
        return f"答案：{context}"


def _service(settings, results, retriever=None, query_generator=None, query_analyzer=None):
    document_store = DocumentStore(settings.data_dir)
    for document_id in {result.document_id for result in results}:
        document_store.save_document(
            KnowledgeDocument(
                document_id=document_id,
                filename="guide.pdf",
                status=DocumentStatus.ready,
                size_bytes=1,
                uploaded_at=utc_now(),
            )
        )
        for result in results:
            document_store.replace_chunks(
                result.document_id,
                [
                    ParentContextUnit(
                        parent_id=result.parent_id,
                        document_id=result.document_id,
                        text=result.text or result.content_preview,
                        char_count=len(result.text or result.content_preview),
                        ordinal=0,
                    )
                ],
                [],
            )
    return AgentGraphService(
        settings=settings,
        retriever=retriever or FakeRetriever(results),
        context_builder=ContextBuilder(settings, document_store),
        generator=FakeGenerator(),
        evaluator=AnswerEvaluator(),
        document_store=document_store,
        query_generator=query_generator,
        query_analyzer=query_analyzer,
    )


def test_graph_forces_search_then_returns_to_orchestrator_and_evaluates(settings):
    document_id, parent_id = uuid4(), uuid4()
    result = RetrievalResult(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        filename="guide.pdf",
        score=0.9,
        content_preview="系统先检查输入电压并确认保护状态。 " * 20,
        text="系统先检查输入电压并确认保护状态。 " * 20,
        retrieval_mode="hybrid",
    )
    service = _service(settings, [result])

    output = service.run("系统如何上电？")

    assert output.status == "completed"
    assert output.final_answer.startswith("答案：")
    assert output.evaluation is not None
    assert output.tool_trace[0] == "search_child_chunks"
    assert output.execution_trace[0]["tool"] == "search_child_chunks"
    assert output.execution_trace[0]["count"] == 1
    assert output.execution_trace[0]["max_score"] == 0.9
    assert output.execution_trace[0]["duration_ms"] >= 0
    assert output.node_trace.count("orchestrator") == 2
    assert "collect_answer" in output.node_trace


def test_graph_uses_fallback_when_search_returns_no_evidence(settings):
    service = AgentGraphService(
        settings=settings,
        retriever=EmptyRetriever(),
        context_builder=ContextBuilder(settings, DocumentStore(settings.data_dir)),
        generator=FakeGenerator(),
        evaluator=AnswerEvaluator(),
        document_store=DocumentStore(settings.data_dir),
    )

    output = service.run("不存在的问题")

    assert output.status == "fallback"
    assert output.final_answer == INSUFFICIENT_ANSWER
    assert output.evaluation is not None
    assert fallback_response({})["final_answer"] == INSUFFICIENT_ANSWER


def test_graph_supports_child_fragment_parent_retrieval(settings):
    document_id, parent_id = uuid4(), uuid4()
    result = RetrievalResult(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        filename="guide.pdf",
        score=0.9,
        content_preview="短 Child",
        text="短 Child",
        retrieval_mode="hybrid",
    )
    service = _service(settings, [result])

    output = service.run("完整工作过程是什么？")

    assert output.status == "completed"
    assert output.tool_trace == ["search_child_chunks", "retrieve_parent_chunks"]
    assert output.execution_trace[1]["parent_id"] == str(parent_id)
    assert output.execution_trace[1]["count"] == 1
    assert output.final_answer.startswith("答案：")


def test_graph_generates_second_query_when_first_search_is_empty(settings):
    document_id, parent_id = uuid4(), uuid4()
    result = RetrievalResult(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        filename="guide.pdf",
        score=0.9,
        content_preview="详细证据 " * 80,
        text="详细证据 " * 80,
        retrieval_mode="hybrid",
    )
    retriever = SequenceRetriever([[], [result]])
    service = _service(
        settings,
        [result],
        retriever=retriever,
        query_generator=RuleBasedQueryGenerator(),
    )

    output = service.run("原始问题")

    assert output.status == "completed"
    assert output.tool_trace == ["search_child_chunks", "search_child_chunks"]
    assert [item["query"] for item in output.execution_trace] == ["原始问题", "原始问题 关键步骤和工作过程"]
    assert len(retriever.calls) == 2
    assert retriever.calls[0] != retriever.calls[1]


def test_graph_stops_at_tool_budget_without_looping(settings):
    limited = settings.model_copy(update={"max_tool_calls": 1})
    service = _service(limited, [], retriever=SequenceRetriever([[]]))

    output = service.run("没有证据的问题")

    assert output.status == "fallback"
    assert output.tool_trace == ["search_child_chunks"]


def test_graph_compresses_long_context_before_answer(settings):
    document_id, parent_id = uuid4(), uuid4()
    result = RetrievalResult(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        filename="guide.pdf",
        score=0.9,
        content_preview="长证据",
        text="输入电压检查和保护状态确认。 " * 180,
        retrieval_mode="hybrid",
    )
    compressed_settings = settings.model_copy(
        update={"base_token_threshold": 30, "token_growth_factor": 0.9}
    )
    service = _service(compressed_settings, [result])

    output = service.run("系统如何上电？")

    assert output.status == "completed"
    assert output.context_compressed is True
    assert output.context_summary
    assert output.context_tokens_after < output.context_tokens_before
    assert output.context_messages
    assert output.context_messages[0]["role"] == "retrieval_result"
    assert output.context_messages[0]["parent_id"] == str(parent_id)
    assert output.context_messages[0]["document_id"] == str(document_id)
    assert len(output.retrieved_results) == 1
    assert output.tool_trace == ["search_child_chunks"]


def test_graph_reuses_thread_memory_for_contextual_followup_and_isolates_new_thread(settings):
    document_id, parent_id = uuid4(), uuid4()
    result = RetrievalResult(
        child_id=uuid4(),
        parent_id=parent_id,
        document_id=document_id,
        filename="guide.pdf",
        score=0.9,
        content_preview="保护功能证据 " * 20,
        text="保护功能证据 " * 20,
        retrieval_mode="hybrid",
    )
    service = _service(settings, [result])

    first = service.run("PN8733 的上电流程是什么？", thread_id="chat-a")
    follow_up = service.run("那它的保护功能呢？", thread_id="chat-a")
    isolated = service.run("那它的保护功能呢？", thread_id="chat-b")

    assert first.thread_id == "chat-a"
    assert follow_up.question_is_clear is True
    assert "PN8733 的上电流程是什么？" in follow_up.rewritten_query
    assert follow_up.status == "completed"
    assert isolated.question_is_clear is False
    assert isolated.status == "clarification"
    assert isolated.tool_trace == []
