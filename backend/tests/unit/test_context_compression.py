from uuid import uuid4

from app.observability.logger import StructuredLogger
from app.rag.context_compression import (
    compress_context,
    dynamic_token_threshold,
    estimate_tokens,
    should_compress_context,
)
from app.rag.pipeline import RagPipeline
from app.schemas.chat import EvaluationResult, RetrievalResult, SourceRef
from app.rag.graph_state import GraphRunResult


def test_dynamic_token_threshold_and_compression_decision():
    assert dynamic_token_threshold(100, 0.9, 1) == 100
    assert dynamic_token_threshold(100, 0.9, 2) == 190
    assert should_compress_context("证据 " * 100, iteration_count=1, base_token_threshold=20, token_growth_factor=0.9)
    assert not should_compress_context("短证据", iteration_count=1, base_token_threshold=20, token_growth_factor=0.9)


def test_compress_context_keeps_summary_and_necessary_evidence():
    original = "\n\n".join(
        [
            "[来源：guide.pdf | 章节：上电]\n输入电压检查、保护状态确认和启动顺序。" * 20,
            "[来源：guide.pdf | 章节：保护]\n过流保护和过压保护的触发条件。" * 20,
        ]
    )

    compressed = compress_context(
        original,
        context_summary="",
        iteration_count=1,
        base_token_threshold=80,
        token_growth_factor=0.9,
    )

    assert compressed.compressed is True
    assert compressed.summary
    assert "上电" in compressed.summary
    assert "保护" in compressed.context
    assert compressed.tokens_after < compressed.tokens_before
    assert compressed.tokens_after <= compressed.threshold
    assert estimate_tokens(compressed.context) == compressed.tokens_after
    assert compressed.record_messages
    assert all(item["role"] == "retrieval_result" for item in compressed.record_messages)
    assert all(int(item["tokens"]) > 0 for item in compressed.record_messages)
    assert compressed.record_tokens_before > compressed.record_tokens_after


class FakeGraph:
    def run(self, question, request_id=None, thread_id=None):
        document_id = uuid4()
        return GraphRunResult(
            final_answer="测试答案",
            retrieved_results=[
                RetrievalResult(
                    child_id=uuid4(),
                    parent_id=uuid4(),
                    document_id=document_id,
                    filename="guide.pdf",
                    score=0.9,
                    content_preview="证据",
                    retrieval_mode="hybrid",
                )
            ],
            context="压缩后的上下文",
            sources=[SourceRef(document_id=document_id, filename="guide.pdf")],
            evaluation=EvaluationResult(
                relevance=90,
                faithfulness=90,
                completeness=90,
                overall=90,
                reason="测试",
            ),
            status="completed",
            tool_trace=["search_child_chunks"],
            node_trace=["orchestrator", "collect_answer"],
            request_id=str(request_id),
            thread_id=thread_id or "thread-test",
            query_history=[question],
            retrieval_keys=set(),
            budget_exceeded=False,
            context_summary="本轮证据摘要",
            context_compressed=True,
            context_token_threshold=80,
            context_tokens_before=200,
            context_tokens_after=70,
            context_removed_items=2,
        )


def test_pipeline_emits_context_compression_event(settings, tmp_path):
    pipeline = RagPipeline(
        retriever=None,
        context_builder=None,
        generator=None,
        evaluator=None,
        logger=StructuredLogger(tmp_path / "pipeline.jsonl"),
        graph_service=FakeGraph(),
    )

    events = list(pipeline.run("问题"))

    compression_events = [event for event in events if event["event"] == "context_compression"]
    assert compression_events
    assert compression_events[0]["data"]["summary_chars"] == len("本轮证据摘要")
    assert compression_events[0]["data"]["removed_messages"] == 2
    assert compression_events[0]["data"]["event"] == "context_compression"
    assert compression_events[0]["data"]["node"] == "collect_answer"
