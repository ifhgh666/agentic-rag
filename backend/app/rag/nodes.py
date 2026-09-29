from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from ..schemas.chat import RetrievalResult
from .graph_state import AgentState, Evidence
from .evidence import EvidenceSelector, source_from_record
from .generator import INSUFFICIENT_ANSWER
from .query_planner import ModelQueryGenerator, QueryGenerator, RuleBasedQueryGenerator, normalize_query


def _trace(state: dict, name: str) -> list[str]:
    return [*state.get("node_trace", []), name]


def _tool_content(message: ToolMessage) -> dict[str, Any] | None:
    content = message.content
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        return content[0] if content and isinstance(content[0], dict) else None
    if not isinstance(content, str):
        return None
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _latest_tool_payload(state: AgentState) -> dict[str, Any] | None:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            return _tool_content(message)
    return None


def _tool_call(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args,
                "id": f"{name}-{uuid4().hex}",
                "type": "tool_call",
            }
        ],
    )


def _can_continue(state: AgentState, max_tool_calls: int, max_iterations: int) -> bool:
    return (
        state.get("tool_call_count", 0) < max_tool_calls
        and state.get("iteration_count", 0) < max_iterations
    )


def _merge_results(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*existing, *incoming]:
        key = str(item.get("child_id", ""))
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        merged.append(item)
    return merged


def _merge_parents(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*existing, *incoming]:
        key = str(item.get("parent_id", ""))
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        merged.append(item)
    return merged


def _as_retrieval_result(evidence: Evidence) -> dict[str, Any]:
    return {
        "child_id": str(evidence.child_id),
        "parent_id": str(evidence.parent_id),
        "document_id": str(evidence.document_id),
        "filename": evidence.source,
        "section_title": evidence.section.get("title", ""),
        "score": evidence.score,
        "retrieval_mode": evidence.retrieval_mode,
        "content_preview": evidence.content[:240],
        "text": evidence.content,
    }


def _request_search(
    state: AgentState,
    query: str,
    trace: list[str],
    default_limit: int,
) -> dict[str, Any]:
    normalized = normalize_query(query)
    keys = set(state.get("retrieval_keys", set()))
    keys.add(f"search::{normalized}")
    history = list(state.get("query_history", []))
    if normalized not in {normalize_query(item) for item in history}:
        history.append(query.strip())
    return {
        "messages": [_tool_call("search_child_chunks", {"query": query.strip(), "limit": default_limit, "request_id": state.get("request_id", "")})],
        "retrieval_keys": keys,
        "query_history": history,
        "node_trace": trace,
    }


def _request_parent(state: AgentState, parent_id: str, trace: list[str]) -> dict[str, Any]:
    keys = set(state.get("retrieval_keys", set()))
    keys.add(f"parent::{parent_id}")
    return {
        "messages": [_tool_call("retrieve_parent_chunks", {"parent_id": parent_id, "request_id": state.get("request_id", "")})],
        "retrieval_keys": keys,
        "node_trace": trace,
    }


def _budget_result(state: AgentState, trace: list[str]) -> dict[str, Any]:
    if state.get("retrieved_results"):
        return {
            "messages": [AIMessage(content="已达到检索预算，将基于当前证据回答。")],
            "budget_exceeded": True,
            "node_trace": trace,
        }
    return {
        "messages": [AIMessage(content="已达到检索预算，当前没有足够证据。")],
        "status": "fallback",
        "budget_exceeded": True,
        "node_trace": trace,
    }


def _next_query(
    state: AgentState,
    question: str,
    query_generator: QueryGenerator,
) -> tuple[str, dict[str, Any] | None]:
    generate_with_result = getattr(query_generator, "generate_with_result", None)
    if generate_with_result:
        if isinstance(query_generator, ModelQueryGenerator):
            return generate_with_result(
                question, state.get("query_history", []),
                thread_id=state.get("thread_id", ""), request_id=state.get("request_id", ""),
            )
        return generate_with_result(question, state.get("query_history", []))
    return query_generator.generate(question, state.get("query_history", [])), None


_MODEL_ID_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,12}[-_]?\d{2,}[A-Za-z0-9-]*(?![A-Za-z0-9])")


def _evidence_matches(question: str, texts: list[str]) -> bool:
    ids = {item.lower() for item in _MODEL_ID_RE.findall(question)}
    if not ids:
        return True
    corpus = "\n".join(texts).lower()
    evidence_ids = {item.lower() for item in _MODEL_ID_RE.findall(corpus)}
    # 章节可能省略型号；只有明确命中另一个型号时才判定为不匹配。
    return not evidence_ids or ids.issubset(evidence_ids)


def _retry_search(
    state: AgentState,
    base_update: dict[str, Any],
    trace: list[str],
    query_generator: QueryGenerator,
    default_limit: int,
    max_tool_calls: int,
    max_iterations: int,
) -> dict[str, Any]:
    keys = set(state.get("retrieval_keys", set()))
    if len([key for key in keys if key.startswith("search::")]) >= 2 or not _can_continue(state, max_tool_calls, max_iterations):
        return {**base_update, **_budget_result({**state, **base_update}, trace)}
    new_query, model_call = _next_query(state, state.get("question", ""), query_generator)
    if model_call:
        base_update["model_trace"] = [*state.get("model_trace", []), model_call]
    if not new_query or f"search::{normalize_query(new_query)}" in keys:
        return {**base_update, "status": "fallback", "node_trace": trace, "messages": [AIMessage(content="没有找到新的检索方向。") ]}
    return {**base_update, **_request_search({**state, **base_update}, new_query, trace, default_limit)}


def orchestrator(
    state: AgentState,
    default_limit: int = 7,
    max_tool_calls: int = 8,
    max_iterations: int = 10,
    query_generator: QueryGenerator | None = None,
    parent_threshold_chars: int = 240,
) -> dict[str, Any]:
    """V2-4 编排器：搜索不足时生成新 Query，Child 碎片时读取 Parent。"""
    query_generator = query_generator or RuleBasedQueryGenerator()
    next_iteration = min(state.get("iteration_count", 0) + 1, max_iterations)
    trace = _trace(state, "orchestrator")
    if state.get("tool_call_count", 0) == 0:
        if not _can_continue(state, max_tool_calls, max_iterations):
            return _budget_result(state, trace)
        return _request_search(state, state.get("question", ""), trace, default_limit) | {
            "iteration_count": next_iteration
        }

    payload = _latest_tool_payload(state)
    last_tool = state.get("last_tool", "")
    results = list(state.get("retrieved_results", []))
    contexts = list(state.get("retrieved_contexts", []))
    parents = list(state.get("parent_contexts", []))
    keys = set(state.get("retrieval_keys", set()))
    base_update: dict[str, Any] = {
        "iteration_count": next_iteration,
        "last_tool_error": "" if payload else state.get("last_tool_error", ""),
    }

    if last_tool == "search_child_chunks":
        if not payload or payload.get("tool") != "search_child_chunks":
            if results:
                return {
                    **base_update,
                    "messages": [AIMessage(content="搜索工具未返回新证据，将使用已有证据。")],
                    "node_trace": trace,
                }
            return {**base_update, "status": "fallback", "node_trace": trace, "messages": [AIMessage(content="搜索失败。 ")]}

        incoming: list[dict[str, Any]] = []
        for item in payload.get("results", []):
            evidence = Evidence.model_validate(item)
            contexts.append(evidence.model_dump(mode="json"))
            incoming.append(_as_retrieval_result(evidence))
        results = _merge_results(results, incoming)
        base_update.update({"retrieved_contexts": contexts, "retrieved_results": results})

        if not incoming:
            return _retry_search(state, base_update, trace, query_generator, default_limit, max_tool_calls, max_iterations)

        if parents:
            return {**base_update, "messages": [AIMessage(content="已获得 Parent 上下文。")], "node_trace": trace}

        short_result = next((item for item in results if len(item.get("text") or "") < parent_threshold_chars), None)
        if short_result:
            parent_id = str(short_result["parent_id"])
            if f"parent::{parent_id}" not in keys:
                if not _can_continue(state, max_tool_calls, max_iterations):
                    return {**base_update, **_budget_result(state, trace)}
                return {**base_update, **_request_parent({**state, **base_update}, parent_id, trace)}
        if not _evidence_matches(state.get("question", ""), [item.get("text", "") for item in results]):
            base_update.update({"retrieved_results": [], "retrieved_contexts": [], "parent_contexts": []})
            return _retry_search(state, base_update, trace, query_generator, default_limit, max_tool_calls, max_iterations)
        return {**base_update, "messages": [AIMessage(content="当前 Child 证据已足够。")], "node_trace": trace}

    if last_tool == "retrieve_parent_chunks":
        if payload and payload.get("tool") == "retrieve_parent_chunks":
            parents = _merge_parents(parents, [payload])
        if parents and not _evidence_matches(state.get("question", ""), [str(item.get("content", "")) for item in parents]):
            base_update.update({"retrieved_results": [], "retrieved_contexts": [], "parent_contexts": []})
            return _retry_search(state, base_update, trace, query_generator, default_limit, max_tool_calls, max_iterations)
        return {
            **base_update,
            "parent_contexts": parents,
            "messages": [AIMessage(content="已完成 Parent 检索。")],
            "node_trace": trace,
        }

    if results:
        return {**base_update, "messages": [AIMessage(content="将使用当前证据回答。")], "node_trace": trace}
    return {**base_update, "status": "fallback", "node_trace": trace, "messages": [AIMessage(content="没有可用证据。 ")]}


def collect_answer(
    state: AgentState,
    selector: EvidenceSelector,
) -> dict[str, Any]:
    trace = _trace(state, "collect_answer")
    results = [RetrievalResult.model_validate(item) for item in state.get("retrieved_results", [])]
    records = selector.select(state.get("question", ""), results, state.get("request_id", ""))
    if not records:
        return fallback_response({**state, "node_trace": trace})
    return {
        "context": "\n\n".join(str(item["content"]) for item in records),
        "context_messages": records,
        "sources": [source_from_record(item).model_dump(mode="json") for item in records],
        "status": "evidence_ready",
        "node_trace": trace,
    }


def fallback_response(state: dict) -> dict[str, Any]:
    return {
        "final_answer": INSUFFICIENT_ANSWER,
        "context": "",
        "sources": [],
        "status": "fallback",
        "node_trace": _trace(state, "fallback_response"),
    }


def evaluate_answer(state: AgentState, evaluator) -> dict[str, Any]:
    evaluation = evaluator.evaluate(
        state.get("question", ""),
        state.get("final_answer", INSUFFICIENT_ANSWER),
        state.get("context", ""),
    )
    return {"evaluation": evaluation.model_dump(mode="json"), "node_trace": _trace(state, "evaluate_answer")}
