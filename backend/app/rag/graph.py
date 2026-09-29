from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Send

from ..config import Settings
from ..knowledge.stores import DocumentStore
from ..schemas.chat import EvaluationResult, RetrievalResult, SourceRef
from .context_builder import ContextBuilder
from .cost_control import BoundedCache, ModelCallBudget, summarize_usage
from .context_compression import CompressionResult, compress_context, dynamic_token_threshold, estimate_tokens
from .conversation_memory import ConversationMemory
from .evidence import EvidenceSelector, find_numeric_conflict, format_conflict_answer, format_evidence_records, source_from_record
from .evaluator import AnswerEvaluator
from .generator import AnswerGenerator, BUDGET_FALLBACK_PREFIX, INSUFFICIENT_ANSWER
from .graph_state import AgentState, GraphRunResult, MainState, new_agent_state, new_main_state
from .nodes import _tool_content, collect_answer, evaluate_answer, fallback_response, orchestrator
from .model_compression import ModelContextCompressor
from .query_analysis import QueryAnalyzer
from .query_planner import ModelQueryGenerator, QueryGenerator, RuleBasedQueryGenerator, normalize_query
from .retriever import Retriever
from .tools import RequestToolCache, create_rag_tools


def _route_after_orchestrator(state: AgentState) -> str:
    last_message = state.get("messages", [])[-1] if state.get("messages") else None
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    if state.get("retrieved_results"):
        return "collect_answer"
    return "fallback_response"


def build_agent_subgraph(
    tools: list,
    context_builder: ContextBuilder,
    generator: AnswerGenerator,
    selector: EvidenceSelector,
    retrieval_top_k: int = 7,
    max_tool_calls: int = 8,
    max_iterations: int = 10,
    parent_threshold_chars: int = 240,
    base_token_threshold: int = 2000,
    token_growth_factor: float = 0.9,
    query_generator: QueryGenerator | None = None,
):
    tool_node = ToolNode(tools, handle_tool_errors=True)

    def execute_tools(state: AgentState) -> dict[str, Any]:
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        tool_calls = last_message.tool_calls if isinstance(last_message, AIMessage) else []
        started = time.perf_counter()
        result = tool_node.invoke(state)
        duration_ms = int((time.perf_counter() - started) * 1000)
        tool_messages = [message for message in result.get("messages", []) if isinstance(message, ToolMessage)]
        tool_message = tool_messages[-1] if tool_messages else None
        tool_error = ""
        if isinstance(tool_message, ToolMessage) and isinstance(tool_message.content, str):
            if tool_message.content.startswith("Error") or "INDEX_NOT_READY" in tool_message.content:
                tool_error = tool_message.content
        previous_calls = state.get("tool_call_count", 0)
        execution_trace: list[dict[str, Any]] = []
        for index, call in enumerate(tool_calls):
            name = str(call.get("name", "unknown"))
            args = dict(call.get("args", {}))
            message = tool_messages[index] if index < len(tool_messages) else None
            payload = _tool_content(message) if isinstance(message, ToolMessage) else None
            results = payload.get("results", []) if isinstance(payload, dict) else []
            scores = [float(item.get("score", 0.0) or 0.0) for item in results if isinstance(item, dict)]
            execution_trace.append(
                {
                    "tool": name,
                    "query": args.get("query"),
                    "parent_id": args.get("parent_id") or (payload or {}).get("parent_id"),
                    "duration_ms": duration_ms,
                    "iteration": state.get("iteration_count", 0),
                    "tool_call_count": previous_calls + index + 1,
                    "count": len(results) if name == "search_child_chunks" else (1 if payload and not tool_error else 0),
                    "retrieval_mode": (results[0].get("retrieval_mode") if results else None),
                    "max_score": max(scores) if scores else None,
                    "status": "failed" if tool_error else "completed",
                }
            )
        return {
            **result,
            "tool_call_count": previous_calls + len(tool_calls),
            "last_tool": str(tool_calls[0].get("name", "")) if tool_calls else "",
            "last_tool_args": dict(tool_calls[0].get("args", {})) if tool_calls else {},
            "last_tool_error": tool_error,
            "tool_trace": [
                *state.get("tool_trace", []),
                *[str(call.get("name", "unknown")) for call in tool_calls],
            ],
            "execution_trace": [*state.get("execution_trace", []), *execution_trace],
            "node_trace": [*state.get("node_trace", []), "tools"],
        }

    builder = StateGraph(AgentState)
    builder.add_node(
        "orchestrator",
        lambda state: orchestrator(
            state,
            default_limit=retrieval_top_k,
            max_tool_calls=max_tool_calls,
            max_iterations=max_iterations,
            query_generator=query_generator,
            parent_threshold_chars=parent_threshold_chars,
        ),
    )
    builder.add_node("tools", execute_tools)
    builder.add_node(
        "collect_answer",
        lambda state: collect_answer(state, selector),
    )
    builder.add_node("fallback_response", fallback_response)
    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {"tools": "tools", "collect_answer": "collect_answer", "fallback_response": "fallback_response"},
    )
    builder.add_edge("tools", "orchestrator")
    builder.add_edge("collect_answer", END)
    builder.add_edge("fallback_response", END)
    return builder.compile()


def build_main_graph(
    agent_graph, evaluator: AnswerEvaluator, memory: ConversationMemory,
    query_analyzer: QueryAnalyzer, generator: AnswerGenerator, settings: Settings,
    model_budget: ModelCallBudget | None = None,
):
    def prepare_query(state: MainState) -> dict[str, Any]:
        prepared = memory.prepare(state.get("thread_id", ""), state.get("original_query", ""))
        if isinstance(query_analyzer, QueryAnalyzer):
            analysis = query_analyzer.analyze(
                prepared.rewritten_query, prepared,
                thread_id=state.get("thread_id", ""), request_id=state.get("request_id", ""),
            )
        else:
            analysis = query_analyzer.analyze(prepared.rewritten_query, prepared)
        if model_budget and len(analysis.questions) > 1:
            model_budget.set_complex(state.get("request_id", ""), True)
        return {
            "conversation_summary": prepared.conversation_summary,
            "history_messages": prepared.history_messages,
            "rewritten_query": analysis.questions[0] if len(analysis.questions) == 1 else prepared.rewritten_query,
            "questions": analysis.questions,
            "question_is_clear": analysis.is_clear,
            "clarification": analysis.clarification,
            "model_trace": [analysis.model_trace] if analysis.model_trace else [],
            "node_trace": [*state.get("node_trace", []), "prepare_query"],
        }

    def route_after_prepare(state: MainState):
        if not state.get("question_is_clear", True):
            return "clarification"
        return [
            Send("agent", {
                "question": question,
                "question_index": index,
                "request_id": state.get("request_id", ""),
                "thread_id": state.get("thread_id", ""),
            })
            for index, question in enumerate(state.get("questions", []))
        ]

    def run_agent(state: dict[str, Any]) -> dict[str, Any]:
        question = state["question"]
        agent_state = new_agent_state(question, thread_id=state.get("thread_id"), request_id=state.get("request_id"))
        result = agent_graph.invoke(agent_state)
        return {"agent_results": [{"index": state["question_index"], "question": question, "result": result}]}

    def reduce_results(state: MainState) -> dict[str, Any]:
        branches = sorted(state.get("agent_results", []), key=lambda item: item["index"])
        results: list[dict[str, Any]] = []
        query_history: list[str] = []
        tool_trace: list[str] = []
        execution_trace: list[dict[str, Any]] = []
        model_trace = list(state.get("model_trace", []))
        node_trace = list(state.get("node_trace", []))
        context_messages: list[dict[str, Any]] = []
        seen_children: set[str] = set()
        seen_records: set[str] = set()
        seen_queries: set[str] = set()
        retrieval_keys: set[str] = set()
        for branch in branches:
            result = branch["result"]
            question = branch["question"]
            for item in result.get("retrieved_results", []):
                child_id = str(item.get("child_id", ""))
                if child_id not in seen_children:
                    seen_children.add(child_id)
                    results.append(item)
            for query in result.get("query_history", []):
                key = normalize_query(query)
                if key not in seen_queries:
                    seen_queries.add(key)
                    query_history.append(query)
            retrieval_keys.update(result.get("retrieval_keys", set()))
            tool_trace.extend(result.get("tool_trace", []))
            execution_trace.extend({**item, "subquestion": question} for item in result.get("execution_trace", []))
            model_trace.extend(result.get("model_trace", []))
            node_trace.extend(result.get("node_trace", []))
            for record in result.get("context_messages", []):
                key = str(record.get("record_id", ""))
                if key not in seen_records:
                    seen_records.add(key)
                    context_messages.append(record)

        records = format_evidence_records(context_messages)
        context = "\n\n".join(str(item["content"]) for item in records)
        threshold = min(settings.max_context_tokens, dynamic_token_threshold(
            settings.base_token_threshold, settings.token_growth_factor,
            max((item["result"].get("iteration_count", 1) for item in branches), default=1),
        ))
        conflict = find_numeric_conflict(state.get("original_query", ""), records)
        if conflict:
            conflicting_records = format_evidence_records([
                {**record, "raw_text": quote} for record, quote in conflict
            ])
            conflict_context = "\n\n".join(str(item["content"]) for item in conflicting_records)
            compression = CompressionResult(
                context=conflict_context, summary="", compressed=False,
                tokens_before=estimate_tokens(context), tokens_after=estimate_tokens(conflict_context),
                threshold=threshold, removed_items=max(0, len(records) - len(conflicting_records)),
                record_messages=conflicting_records,
                record_tokens_before=sum(int(item["tokens"]) for item in records),
                record_tokens_after=sum(int(item["tokens"]) for item in conflicting_records),
            )
            compression_call = None
            node_trace.append("conflict_check")
        elif records and isinstance(generator, AnswerGenerator) and settings.llm_provider != "fake":
            compression, compression_call = ModelContextCompressor(generator.get_provider(), model_budget).compress(
                state.get("original_query", ""), records, threshold, state.get("request_id", ""),
            )
        else:
            compression = compress_context(
                context,
                context_summary="",
                iteration_count=max((item["result"].get("iteration_count", 1) for item in branches), default=1),
                base_token_threshold=settings.base_token_threshold,
                token_growth_factor=settings.token_growth_factor,
                context_messages=records,
            )
            compression_call = None
        if compression_call:
            model_trace.append(compression_call)
        if conflict:
            answer = format_conflict_answer(conflict)
            selected_sources = [source_from_record(item).model_dump(mode="json") for item in compression.record_messages]
        elif records:
            if isinstance(generator, AnswerGenerator):
                answer, cited_ids, answer_call = generator.generate_grounded_with_result(
                    state.get("original_query", ""), compression.record_messages, compression.summary,
                    request_id=state.get("request_id", ""),
                )
                selected_sources = [
                    source_from_record(item).model_dump(mode="json")
                    for item in compression.record_messages if item.get("citation_id") in cited_ids
                ]
            else:
                generate_with_result = getattr(generator, "generate_with_result", None)
                if generate_with_result:
                    answer, answer_call = generate_with_result(state.get("original_query", ""), compression.context)
                else:
                    answer, answer_call = generator.generate(state.get("original_query", ""), compression.context), None
                selected_sources = [source_from_record(item).model_dump(mode="json") for item in compression.record_messages]
            if answer_call:
                model_trace.append(answer_call)
            if len(branches) > 1 and settings.llm_provider == "fake":
                headings = "\n".join(f"{index}. {branch['question']}" for index, branch in enumerate(branches, start=1))
                answer = f"{headings}\n\n{answer}"
        else:
            answer = INSUFFICIENT_ANSWER
            selected_sources = []
        return {
            "agent_state": branches[0]["result"] if branches else {},
            "final_answer": answer,
            "context": compression.context,
            "retrieved_results": results,
            "sources": selected_sources,
            "query_history": query_history,
            "retrieval_keys": retrieval_keys,
            "tool_trace": tool_trace,
            "execution_trace": execution_trace,
            "model_trace": model_trace,
            "node_trace": [*node_trace, "reduce_results"],
            "tool_call_count": sum(item["result"].get("tool_call_count", 0) for item in branches),
            "iteration_count": sum(item["result"].get("iteration_count", 0) for item in branches),
            "budget_exceeded": (
                any(item["result"].get("budget_exceeded", False) for item in branches)
                or bool(model_budget and model_budget.snapshot(state.get("request_id", "")).get("budget_exceeded"))
            ),
            "context_summary": compression.summary,
            "context_compressed": compression.compressed,
            "context_token_threshold": compression.threshold,
            "context_tokens_before": compression.tokens_before,
            "context_tokens_after": compression.tokens_after,
            "context_removed_items": compression.removed_items,
            "context_messages": compression.record_messages,
            "status": "completed" if answer and answer != INSUFFICIENT_ANSWER and not answer.startswith(BUDGET_FALLBACK_PREFIX) else "fallback",
        }

    def evaluate(state: MainState) -> dict[str, Any]:
        return evaluate_answer({**state, "question": state.get("original_query", "")}, evaluator)

    def clarification(state: MainState) -> dict[str, Any]:
        return {
            "final_answer": state.get("clarification") or "请补充你指的是哪份文档、哪个型号或哪个主题。",
            "status": "clarification",
            "node_trace": [*state.get("node_trace", []), "clarification"],
        }

    def persist_memory(state: MainState) -> dict[str, Any]:
        thread_id = state.get("thread_id", "")
        if state.get("status") == "clarification":
            memory.set_pending(thread_id, memory.pending(thread_id) or state.get("original_query", ""))
            snapshot = memory.snapshot(thread_id)
        else:
            memory.clear_pending(thread_id)
            snapshot = memory.append(thread_id, state.get("rewritten_query") or state.get("original_query", ""), state.get("final_answer", ""))
        return {
            "conversation_summary": snapshot.conversation_summary,
            "history_messages": snapshot.messages,
            "node_trace": [*state.get("node_trace", []), "persist_memory"],
        }

    builder = StateGraph(MainState)
    builder.add_node("prepare_query", prepare_query)
    builder.add_node("agent", run_agent)
    builder.add_node("reduce_results", reduce_results)
    builder.add_node("evaluate", evaluate)
    builder.add_node("clarification", clarification)
    builder.add_node("persist_memory", persist_memory)
    builder.add_edge(START, "prepare_query")
    builder.add_conditional_edges("prepare_query", route_after_prepare)
    builder.add_edge("agent", "reduce_results")
    builder.add_edge("reduce_results", "evaluate")
    builder.add_edge("evaluate", "persist_memory")
    builder.add_edge("clarification", "persist_memory")
    builder.add_edge("persist_memory", END)
    return builder.compile(checkpointer=memory.checkpointer)


class AgentGraphService:
    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        context_builder: ContextBuilder,
        generator: AnswerGenerator,
        evaluator: AnswerEvaluator,
        document_store: DocumentStore,
        query_generator: QueryGenerator | None = None,
        memory: ConversationMemory | None = None,
        query_analyzer: QueryAnalyzer | None = None,
    ) -> None:
        self.settings = settings
        self.retriever = retriever
        self.context_builder = context_builder
        self.generator = generator
        self.evaluator = evaluator
        self.document_store = document_store
        self.request_cache = RequestToolCache()
        self.model_budget = ModelCallBudget(
            simple_limit=min(settings.max_simple_llm_calls, settings.max_llm_calls_per_request),
            complex_limit=settings.max_llm_calls_per_request,
            node_limits={
                "query_analysis": settings.max_query_analysis_calls,
                "query_rewrite": settings.max_query_rewrite_calls,
                "context_compression": settings.max_compression_calls,
                "collect_answer": settings.max_answer_calls,
            },
        )
        analysis_cache = BoundedCache(settings.rag_cache_max_entries, settings.rag_cache_ttl_seconds)
        rewrite_cache = BoundedCache(settings.rag_cache_max_entries, settings.rag_cache_ttl_seconds)
        version = lambda: getattr(self.retriever.index_store, "version", "")
        if isinstance(generator, AnswerGenerator):
            generator.budget = self.model_budget
        self.query_generator = query_generator or (
            RuleBasedQueryGenerator() if settings.llm_provider == "fake"
            else ModelQueryGenerator(
                settings, provider=getattr(generator, "provider", None), cache=rewrite_cache,
                index_version=version, budget=self.model_budget, request_cache=self.request_cache,
            )
        )
        self.memory = memory or ConversationMemory(settings.main_history_messages_to_keep)
        self.query_analyzer = query_analyzer or QueryAnalyzer(
            settings, provider=getattr(generator, "provider", None), cache=analysis_cache,
            index_version=version, budget=self.model_budget, request_cache=self.request_cache,
        )
        if isinstance(self.query_generator, ModelQueryGenerator):
            self.query_generator.budget = self.model_budget
            self.query_generator.request_cache = self.request_cache
        if isinstance(self.query_analyzer, QueryAnalyzer):
            self.query_analyzer.budget = self.model_budget
            self.query_analyzer.request_cache = self.request_cache
        self.evidence_selector = EvidenceSelector(settings, document_store, self.request_cache)
        self.tools = create_rag_tools(retriever, document_store, settings, self.request_cache)
        self.agent_graph = build_agent_subgraph(
            self.tools,
            context_builder,
            generator,
            self.evidence_selector,
            retrieval_top_k=settings.retrieval_top_k,
            max_tool_calls=settings.max_tool_calls,
            max_iterations=settings.max_iterations,
            parent_threshold_chars=settings.agent_parent_threshold_chars,
            base_token_threshold=settings.base_token_threshold,
            token_growth_factor=settings.token_growth_factor,
            query_generator=self.query_generator,
        )
        self.main_graph = build_main_graph(self.agent_graph, evaluator, self.memory, self.query_analyzer, generator, settings, self.model_budget)

    def run(
        self,
        question: str,
        request_id: str | None = None,
        thread_id: str | None = None,
    ) -> GraphRunResult:
        state = new_main_state(question, thread_id=thread_id, request_id=request_id)
        started = time.perf_counter()
        self.model_budget.start(state["request_id"])
        try:
            result = self.main_graph.invoke(
                state,
                config={
                    "recursion_limit": self.settings.graph_recursion_limit,
                    "configurable": {"thread_id": state["thread_id"]},
                },
            )
        finally:
            budget_summary = self.model_budget.finish(state["request_id"])
            cache_hits = self.request_cache.stats(state["request_id"])
            self.request_cache.clear(state["request_id"])
        usage = summarize_usage(
            list(result.get("model_trace", [])), budget_summary, cache_hits,
            int((time.perf_counter() - started) * 1000),
        )
        return GraphRunResult(
            final_answer=result.get("final_answer", ""),
            retrieved_results=[RetrievalResult.model_validate(item) for item in result.get("retrieved_results", [])],
            context=result.get("context", ""),
            sources=[SourceRef.model_validate(item) for item in result.get("sources", [])],
            evaluation=EvaluationResult.model_validate(result["evaluation"]) if result.get("evaluation") else None,
            status=result.get("status", "failed"),
            tool_trace=list(result.get("tool_trace", [])),
            execution_trace=list(result.get("execution_trace", [])),
            model_trace=list(result.get("model_trace", [])),
            node_trace=list(result.get("node_trace", [])),
            request_id=result.get("request_id", ""),
            thread_id=result.get("thread_id", ""),
            query_history=list(result.get("query_history", [])),
            retrieval_keys=set(result.get("retrieval_keys", set())),
            budget_exceeded=bool(result.get("budget_exceeded", False) or budget_summary["budget_exceeded"]),
            context_summary=result.get("context_summary", ""),
            context_compressed=bool(result.get("context_compressed", False)),
            context_token_threshold=int(result.get("context_token_threshold", 0)),
            context_tokens_before=int(result.get("context_tokens_before", 0)),
            context_tokens_after=int(result.get("context_tokens_after", 0)),
            context_removed_items=int(result.get("context_removed_items", 0)),
            context_messages=list(result.get("context_messages", [])),
            conversation_summary=result.get("conversation_summary", ""),
            rewritten_query=result.get("rewritten_query", question),
            question_is_clear=bool(result.get("question_is_clear", True)),
            clarification=result.get("clarification", ""),
            questions=list(result.get("questions", [])),
            usage=usage,
        )
