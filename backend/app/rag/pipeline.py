import json
import time
from uuid import UUID, uuid4

from ..observability.logger import StructuredLogger
from ..observability.execution import build_execution_event
from .context_builder import ContextBuilder
from .evaluator import AnswerEvaluator
from .generator import AnswerGenerator
from .graph import AgentGraphService
from .retriever import Retriever


def _public_failure(exc: Exception) -> tuple[str, str]:
    """Classify failures without streaming exception text, prompts or credentials."""
    detail = str(exc).lower()
    if "ollama_model" in detail or "未配置" in detail and "模型" in detail:
        return "LOCAL_MODEL_NOT_CONFIGURED", "本地模型尚未配置，请检查 OLLAMA_MODEL。"
    if "timeout" in detail or "timed out" in detail or "超时" in detail:
        return "LOCAL_MODEL_TIMEOUT", "本地模型响应超时，请确认 Ollama 正常运行。"
    if "connect" in detail or "连接" in detail:
        return "LOCAL_MODEL_UNAVAILABLE", "无法连接本地模型，请确认 Ollama 已启动。"
    if "index_not_ready" in detail or "索引未就绪" in detail:
        return "INDEX_NOT_READY", "知识库索引未就绪，请先检查或重建索引。"
    return "RAG_PIPELINE_FAILED", "问答处理失败，请查看服务端日志。"


class RagPipeline:
    def __init__(
        self,
        retriever: Retriever,
        context_builder: ContextBuilder,
        generator: AnswerGenerator,
        evaluator: AnswerEvaluator,
        logger: StructuredLogger,
        graph_service: AgentGraphService | None = None,
    ):
        self.retriever = retriever
        self.context_builder = context_builder
        self.generator = generator
        self.evaluator = evaluator
        self.logger = logger
        self.graph_service = graph_service

    def _event(self, event: str, payload: dict) -> dict:
        return {"event": event, "data": payload}

    def run(self, question: str, request_id: UUID | None = None, thread_id: str | None = None):
        request_id = request_id or uuid4()
        thread_id = thread_id or f"thread-{uuid4()}"
        sequence = 0

        def step(stage: str, status: str, duration_ms: int | None = None, detail: dict | None = None, error: str | None = None):
            nonlocal sequence
            sequence += 1
            payload = {
                "request_id": str(request_id),
                "thread_id": thread_id,
                "stage": stage,
                "status": status,
                "sequence": sequence,
                "duration_ms": duration_ms,
                "detail": detail or {},
            }
            if error:
                payload["error"] = error
            return self._event("step", payload)

        def execution(
            event: str,
            node: str,
            *,
            tool: str | None = None,
            query: str | None = None,
            parent_id: str | None = None,
            duration_ms: int | None = None,
            score: float | None = None,
            iteration: int | None = None,
            tool_call_count: int | None = None,
            details: dict | None = None,
            compatibility: dict | None = None,
        ):
            payload = build_execution_event(
                request_id=str(request_id),
                thread_id=thread_id,
                node=node,
                event=event,
                tool=tool,
                query=query,
                parent_id=parent_id,
                duration_ms=duration_ms,
                score=score,
                iteration=iteration,
                tool_call_count=tool_call_count,
                details=details,
                max_chars=getattr(self.logger, "max_chars", 1200),
            )
            if compatibility:
                payload.update(compatibility)
            self.logger.log(
                "INFO",
                "rag.execution",
                f"执行事件：{event}",
                request_id,
                duration_ms=duration_ms,
                thread_id=thread_id,
                node=node,
                event=event,
                tool=tool,
                query=query,
                parent_id=parent_id,
                score=score,
                iteration=iteration,
                tool_call_count=tool_call_count,
                details=details,
            )
            return self._event(event, payload)

        def execute(stage: str, operation, detail: dict | None = None):
            started = time.perf_counter()
            yield step(stage, "started", detail=detail)
            try:
                value = operation()
                duration = int((time.perf_counter() - started) * 1000)
                self.logger.log("INFO", "rag.pipeline", f"阶段完成：{stage}", request_id, duration_ms=duration)
                yield step(stage, "completed", duration_ms=duration, detail=detail)
                return value
            except Exception as exc:
                duration = int((time.perf_counter() - started) * 1000)
                self.logger.log("ERROR", "rag.pipeline", f"阶段失败：{stage}", request_id, duration_ms=duration, error={"message": str(exc)})
                yield step(stage, "failed", duration_ms=duration, error=str(exc))
                raise

        try:
            yield step("query_receipt", "started", detail={"question_length": len(question)})
            yield step("query_receipt", "completed", duration_ms=0, detail={"message": "已收到问题"})
            self.logger.log("INFO", "rag.pipeline", "收到问题", request_id)

            if self.graph_service:
                graph_result = self.graph_service.run(question, request_id=str(request_id), thread_id=thread_id)
                for node_index, node in enumerate(graph_result.node_trace, start=1):
                    yield execution("node", node, iteration=node_index, details={"status": "completed"})
                for model_call in graph_result.model_trace:
                    yield execution(
                        "model_call",
                        str(model_call.get("node", "collect_answer")),
                        duration_ms=model_call.get("duration_ms"),
                        details={key: value for key, value in model_call.items() if key not in {"node", "duration_ms"}},
                    )
                usage = graph_result.usage
                yield execution(
                    "query_rewritten",
                    "prepare_query",
                    query=graph_result.rewritten_query,
                    details={"is_clear": graph_result.question_is_clear, "questions": graph_result.questions},
                    compatibility={"is_clear": graph_result.question_is_clear},
                )
                if not graph_result.question_is_clear or graph_result.status == "clarification":
                    yield execution(
                        "agent_decision",
                        "orchestrator",
                        tool="clarification",
                        iteration=0,
                        details={"action": "clarification"},
                    )
                    yield self._event(
                        "answer",
                        {
                            "request_id": str(request_id),
                            "thread_id": thread_id,
                            "answer": graph_result.final_answer,
                            "sources": [],
                        },
                    )
                    self.logger.log(
                        "INFO", "rag.usage", "模型与缓存用量汇总", request_id,
                        duration_ms=usage.get("duration_ms"), thread_id=thread_id, details=usage,
                    )
                    yield self._event("usage", {"request_id": str(request_id), "thread_id": thread_id, **usage})
                    yield self._event(
                        "complete",
                        {"request_id": str(request_id), "thread_id": thread_id, "status": "clarification"},
                    )
                    self.logger.log("INFO", "rag.pipeline", "Graph 澄清完成", request_id)
                    return
                retrieval_box = graph_result.retrieved_results
                trace_items = graph_result.execution_trace or [
                    {
                        "tool": tool,
                        "query": None,
                        "parent_id": None,
                        "duration_ms": None,
                        "iteration": index,
                        "tool_call_count": index,
                        "count": len(retrieval_box) if tool == "search_child_chunks" else 1,
                        "retrieval_mode": retrieval_box[0].retrieval_mode if retrieval_box and tool == "search_child_chunks" else None,
                        "max_score": max((item.score for item in retrieval_box), default=None) if tool == "search_child_chunks" else None,
                        "status": "completed",
                    }
                    for index, tool in enumerate(graph_result.tool_trace, start=1)
                ]
                for trace_item in trace_items:
                    tool = str(trace_item.get("tool", "unknown"))
                    query_value = trace_item.get("query")
                    parent_value = trace_item.get("parent_id")
                    call_index = trace_item.get("tool_call_count") or trace_item.get("iteration") or 0
                    details = {key: trace_item.get(key) for key in ("status", "count", "retrieval_mode") if trace_item.get(key) is not None}
                    if trace_item.get("subquestion"):
                        details["subquestion"] = trace_item["subquestion"]
                    if trace_item.get("max_score") is not None:
                        details["max_score"] = trace_item["max_score"]
                    yield execution(
                        "agent_decision",
                        "orchestrator",
                        tool=tool,
                        query=query_value,
                        parent_id=parent_value,
                        iteration=trace_item.get("iteration"),
                        tool_call_count=trace_item.get("tool_call_count"),
                        details={"action": tool},
                    )
                    yield execution(
                        "tool_call",
                        "tools",
                        tool=tool,
                        query=query_value,
                        parent_id=parent_value,
                        duration_ms=trace_item.get("duration_ms"),
                        score=trace_item.get("max_score"),
                        iteration=trace_item.get("iteration"),
                        tool_call_count=trace_item.get("tool_call_count"),
                        details=details,
                    )
                    if tool == "search_child_chunks":
                        yield execution(
                            "hybrid_search",
                            "retriever",
                            tool=tool,
                            query=query_value,
                            duration_ms=trace_item.get("duration_ms"),
                            score=trace_item.get("max_score"),
                            iteration=trace_item.get("iteration"),
                            tool_call_count=trace_item.get("tool_call_count"),
                            details=details,
                        )
                    elif tool == "retrieve_parent_chunks":
                        yield execution(
                            "parent_retrieval",
                            "parent_store",
                            tool=tool,
                            parent_id=parent_value,
                            duration_ms=trace_item.get("duration_ms"),
                            iteration=trace_item.get("iteration"),
                            tool_call_count=trace_item.get("tool_call_count"),
                            details=details,
                        )
                if graph_result.budget_exceeded:
                    yield execution(
                        "budget",
                        "orchestrator",
                        iteration=len(graph_result.tool_trace),
                        tool_call_count=len(graph_result.tool_trace),
                        details={
                            "budget_exceeded": True,
                            "reason": "模型或检索调用达到预算上限；仅展示可核对的证据。",
                            "model_calls": usage.get("model_calls", 0),
                            "model_call_limit": usage.get("model_call_limit", 0),
                        },
                    )
                if any(item.get("tool") == "search_child_chunks" for item in trace_items):
                    yield step("child_retrieval", "started")
                    yield step("child_retrieval", "completed", detail={"count": len(retrieval_box)})
                    yield step("score_filtering", "completed", detail={"count": len(retrieval_box)})
                yield self._event(
                    "retrieval",
                    {"request_id": str(request_id), "thread_id": thread_id, "results": [item.model_dump(mode="json") for item in retrieval_box]},
                )
                if graph_result.sources:
                    yield step("parent_retrieval", "completed", detail={"count": len(graph_result.sources)})
                    yield step("context_building", "completed", detail={"characters": len(graph_result.context), "sources": len(graph_result.sources)})
                if graph_result.context_compressed:
                    compression_detail = {
                        "tokens_before": graph_result.context_tokens_before,
                        "tokens_after": graph_result.context_tokens_after,
                        "token_threshold": graph_result.context_token_threshold,
                        "summary_chars": len(graph_result.context_summary),
                        "removed_items": graph_result.context_removed_items,
                    }
                    yield execution(
                        "context_compression",
                        "collect_answer",
                        details={
                            "summary_chars": len(graph_result.context_summary),
                            "removed_messages": graph_result.context_removed_items,
                            "tokens_before": graph_result.context_tokens_before,
                            "tokens_after": graph_result.context_tokens_after,
                            "token_threshold": graph_result.context_token_threshold,
                        },
                        compatibility={
                            "summary_chars": len(graph_result.context_summary),
                            "removed_messages": graph_result.context_removed_items,
                            "tokens_before": graph_result.context_tokens_before,
                            "tokens_after": graph_result.context_tokens_after,
                            "token_threshold": graph_result.context_token_threshold,
                        },
                    )
                    compression_call = next((item for item in graph_result.model_trace if item.get("node") == "context_compression"), None)
                    yield step("context_compression", "completed", duration_ms=compression_call.get("duration_ms") if compression_call else None, detail=compression_detail)
                answer_call = next((item for item in graph_result.model_trace if item.get("node") == "collect_answer"), None)
                yield step(
                    "answer_generation",
                    "completed",
                    duration_ms=answer_call.get("duration_ms") if answer_call else None,
                    detail={"characters": len(graph_result.final_answer)},
                )
                yield self._event(
                    "answer",
                    {
                        "request_id": str(request_id),
                        "thread_id": thread_id,
                        "answer": graph_result.final_answer,
                        "sources": [item.model_dump(mode="json") for item in graph_result.sources],
                    },
                )
                evaluation = graph_result.evaluation
                if evaluation:
                    yield step("answer_evaluation", "completed", detail={"overall": evaluation.overall})
                if evaluation:
                    yield self._event("evaluation", {"request_id": str(request_id), "thread_id": thread_id, **evaluation.model_dump()})
                self.logger.log(
                    "INFO", "rag.usage", "模型与缓存用量汇总", request_id,
                    duration_ms=usage.get("duration_ms"), thread_id=thread_id, details=usage,
                )
                yield self._event("usage", {"request_id": str(request_id), "thread_id": thread_id, **usage})
                yield self._event(
                    "complete",
                    {
                        "request_id": str(request_id),
                        "thread_id": thread_id,
                        "status": "completed" if graph_result.status in {"completed", "fallback"} else "failed",
                        "reason": "模型调用预算已用尽，已返回原文证据。" if usage.get("budget_exceeded") else None,
                    },
                )
                self.logger.log("INFO", "rag.pipeline", "Graph 问答完成", request_id)
                return

            yield step("query_representation", "started")
            representation_start = time.perf_counter()
            query_detail = {"characters": len(question), "embedding": "本地确定性嵌入或配置的模型"}
            yield step("query_representation", "completed", duration_ms=int((time.perf_counter() - representation_start) * 1000), detail=query_detail)

            retrieval_box: list = []
            retrieval_start = time.perf_counter()
            yield step("child_retrieval", "started")
            retrieval_box.extend(self.retriever.search(question))
            retrieval_duration = int((time.perf_counter() - retrieval_start) * 1000)
            self.logger.log("INFO", "rag.pipeline", "子级检索完成", request_id, duration_ms=retrieval_duration)
            yield step("child_retrieval", "completed", duration_ms=retrieval_duration, detail={"count": len(retrieval_box)})

            filter_start = time.perf_counter()
            yield step("score_filtering", "started")
            yield step("score_filtering", "completed", duration_ms=int((time.perf_counter() - filter_start) * 1000), detail={"count": len(retrieval_box)})
            yield self._event(
                "retrieval",
                {"request_id": str(request_id), "results": [item.model_dump(mode="json") for item in retrieval_box]},
            )

            parent_start = time.perf_counter()
            yield step("parent_retrieval", "started")
            parents = self.context_builder.load_parents(retrieval_box)
            yield step("parent_retrieval", "completed", duration_ms=int((time.perf_counter() - parent_start) * 1000), detail={"count": len(parents)})

            context_start = time.perf_counter()
            yield step("context_building", "started")
            context, sources = self.context_builder.build(retrieval_box)
            yield step("context_building", "completed", duration_ms=int((time.perf_counter() - context_start) * 1000), detail={"characters": len(context), "sources": len(sources)})

            answer_start = time.perf_counter()
            yield step("answer_generation", "started")
            answer, model_call = self.generator.generate_with_result(question, context)
            if model_call:
                yield execution(
                    "model_call",
                    str(model_call.get("node", "collect_answer")),
                    duration_ms=model_call.get("duration_ms"),
                    details={key: value for key, value in model_call.items() if key not in {"node", "duration_ms"}},
                )
            yield step("answer_generation", "completed", duration_ms=int((time.perf_counter() - answer_start) * 1000), detail={"characters": len(answer)})
            yield self._event(
                "answer",
                {"request_id": str(request_id), "thread_id": thread_id, "answer": answer, "sources": [item.model_dump(mode="json") for item in sources]},
            )

            evaluation_start = time.perf_counter()
            yield step("answer_evaluation", "started")
            evaluation = self.evaluator.evaluate(question, answer, context)
            yield step("answer_evaluation", "completed", duration_ms=int((time.perf_counter() - evaluation_start) * 1000), detail={"overall": evaluation.overall})
            yield self._event("evaluation", {"request_id": str(request_id), "thread_id": thread_id, **evaluation.model_dump()})
            yield self._event("complete", {"request_id": str(request_id), "thread_id": thread_id, "status": "completed"})
            self.logger.log("INFO", "rag.pipeline", "问答完成", request_id)
        except Exception as exc:
            code, message = _public_failure(exc)
            self.logger.log(
                "ERROR", "rag.pipeline", "问答处理失败", request_id,
                thread_id=thread_id, details={"code": code, "exception_type": type(exc).__name__},
            )
            yield step("rag_graph", "failed", error=message, detail={"code": code})
            yield self._event(
                "error",
                {
                    "request_id": str(request_id),
                    "thread_id": thread_id,
                    "code": code,
                    "message": message,
                },
            )
            yield self._event("complete", {"request_id": str(request_id), "thread_id": thread_id, "status": "failed"})
