"""Governed model calls: shared budgets, leases, deadlines and usage records."""
from __future__ import annotations

import json
import time
from collections import OrderedDict
from concurrent.futures import Executor, TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from pydantic import BaseModel
from threading import Lock
from typing import Any, Iterator
from uuid import uuid4
from ..config import Settings
from .model_provider import (
    ChatProvider,
    ModelResult,
    PreparedAttempt,
    _MODEL_EXECUTOR,
    complete_model,
    estimate_tokens,
    token_details,
)


@dataclass(frozen=True)
class CallSpec:
    node: str
    messages: list[dict[str, Any]]
    tools: list[dict] | None = None
    response_schema: type[BaseModel] | None = None
    iteration: int = 0

@dataclass(frozen=True)
class AttemptRecord:
    attempt_index: int
    structured_mode: str
    input_tokens_estimate: int
    status: str
    reason: str
    timestamp_ns: int

@dataclass(frozen=True)
class CallRecord:
    model_call_id: str
    request_id: str
    branch_id: str
    node: str
    iteration: int
    timestamp_ns: int
    duration_ms: int
    attempted: bool
    input_tokens_estimate: int | None
    input_tokens: int | None
    output_tokens: int | None
    usage_source: str
    attempts: tuple[AttemptRecord, ...]
    details_json: str

    def to_trace(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("details_json")
        value["attempts"] = [asdict(attempt) for attempt in self.attempts]
        value["attempt_count"] = len(self.attempts)
        value.update(json.loads(self.details_json))
        return value

    def to_metadata(self) -> dict[str, Any]:
        """Preserve metadata-only legacy consumers' original private-body boundary."""
        value = self.to_trace()
        for key in ("input_messages", "candidate_content", "tool_definitions", "returned_tool_calls"):
            value.pop(key, None)
        return value

@dataclass(frozen=True)
class CallOutcome:
    outcome: str
    result: ModelResult | None
    reason: str
    record: CallRecord

class BoundedCache:
    def __init__(self, max_entries: int = 256, ttl_seconds: float = 300):
        self.max_entries = max(1, max_entries)
        self.ttl_seconds = max(1.0, ttl_seconds)
        self._lock = Lock()
        self._items: OrderedDict[tuple, tuple[float, Any]] = OrderedDict()

    def get(self, key: tuple) -> tuple[bool, Any]:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return False, None
            expires_at, value = entry
            if expires_at <= time.monotonic():
                del self._items[key]
                return False, None
            self._items.move_to_end(key)
            return True, value

    def put(self, key: tuple, value: Any) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + self.ttl_seconds, value)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

class ModelCallBudget:
    """Atomically reserve calls before invoking any model, including parallel branches."""

    def __init__(self, simple_limit: int, complex_limit: int, node_limits: dict[str, int],
                 timeout_seconds: float = 300, tool_limit: int = 16):
        self.simple_limit = max(0, simple_limit)
        self.complex_limit = max(self.simple_limit, complex_limit)
        self.node_limits = {key: max(0, value) for key, value in node_limits.items()}
        self._lock = Lock()
        self._requests: dict[str, dict[str, Any]] = {}
        self.timeout_seconds = timeout_seconds
        self.tool_limit = tool_limit

    def start(self, request_id: str, *, deadline: float | None = None, require_missing: bool = False) -> str:
        with self._lock:
            if require_missing and request_id in self._requests:
                raise ValueError("request_already_owned")
            expires_at = time.monotonic() + self.timeout_seconds
            self._requests[request_id] = {
                "lease_id": uuid4().hex,
                "model_calls": 0, "by_node": {}, "budget_exceeded": False,
                "limit": self.simple_limit,
                "deadline": min(expires_at, deadline) if deadline is not None else expires_at,
                "branches": {}, "branch_limits": {}, "branch_tools": {}, "tool_calls": 0,
                "synthesis_reserved": 0, "auxiliary_reserved": 0,
            }
            return self._requests[request_id]["lease_id"]

    def lease(self, request_id: str) -> tuple[str, float] | None:
        with self._lock:
            request = self._requests.get(request_id)
            return (request["lease_id"], request["deadline"]) if request else None

    def active(self, request_id: str, lease_id: str) -> bool:
        with self._lock:
            request = self._requests.get(request_id)
            return bool(request and request["lease_id"] == lease_id
                        and request["deadline"] > time.monotonic())

    def exists(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._requests

    def set_complex(self, request_id: str, complex_query: bool) -> None:
        with self._lock:
            request = self._requests.get(request_id)
            if request and complex_query:
                request["limit"] = self.complex_limit

    def configure_branches(self, request_id: str, count: int) -> None:
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                return
            request["limit"] = self.complex_limit if count > 1 else self.simple_limit
            quota = {1: 5, 2: 4, 3: 3}[count]
            request["branch_limits"] = {f"B{i + 1}": quota for i in range(count)}
            request["branches"] = {key: 0 for key in request["branch_limits"]}
            request["branch_tools"] = {key: 0 for key in request["branch_limits"]}
            request["branch_tool_limit"] = min(8, self.tool_limit // count)
            request["synthesis_reserved"] = int(count > 1)
            request["auxiliary_reserved"] = 1

    def remaining_seconds(self, request_id: str, *, lease_id: str | None = None) -> float:
        with self._lock:
            request = self._requests.get(request_id)
            if lease_id is not None and (request is None or request["lease_id"] != lease_id):
                return 0.0
            return max(0.0, request["deadline"] - time.monotonic()) if request else self.timeout_seconds

    def branch_remaining(self, request_id: str, branch_id: str) -> int:
        with self._lock:
            request = self._requests.get(request_id)
            return max(0, request["branch_limits"].get(branch_id, 5) - request["branches"].get(branch_id, 0)) if request else 5

    def release_branch(self, request_id: str, branch_id: str, *, lease_id: str | None = None) -> None:
        with self._lock:
            request = self._requests.get(request_id)
            if request and (lease_id is None or request["lease_id"] == lease_id):
                request["branch_limits"][branch_id] = request["branches"].get(branch_id, 0)

    def reserve_tool(self, request_id: str, branch_id: str, *, lease_id: str | None = None) -> bool:
        with self._lock:
            request = self._requests.get(request_id)
            if lease_id is not None and (request is None or request["lease_id"] != lease_id):
                return False
            if request is None:
                return True
            used = request["branch_tools"].get(branch_id, 0)
            if (request["deadline"] <= time.monotonic() or request["tool_calls"] >= self.tool_limit
                    or used >= request.get("branch_tool_limit", self.tool_limit)):
                request["budget_exceeded"] = True
                return False
            request["tool_calls"] += 1
            request["branch_tools"][branch_id] = used + 1
            return True

    def reserve(self, request_id: str, node: str, *, preserve_answer_slot: bool = True,
                required: bool = True, branch_id: str | None = None,
                require_active: bool = False, lease_id: str | None = None) -> bool:
        with self._lock:
            request = self._requests.get(request_id)
            if require_active and (request is None or request["lease_id"] != lease_id):
                return False
            if request is None:
                # Direct service/unit invocations outside AgentGraphService.run do not
                # have a request budget. Production requests are always registered.
                return True
            node_count = request["by_node"].get(node, 0)
            if request["deadline"] <= time.monotonic():
                if required:
                    request["budget_exceeded"] = True
                return False
            if request["branches"]:
                remaining = request["limit"] - request["model_calls"]
                held = sum(max(0, limit - request["branches"].get(key, 0))
                           for key, limit in request["branch_limits"].items())
                allowed = remaining > 0
                if branch_id is not None:
                    allowed = allowed and request["branches"].get(branch_id, 0) < request["branch_limits"].get(branch_id, 0)
                elif node == "final_synthesis":
                    allowed = allowed and request["synthesis_reserved"] > 0
                elif node == "answer_repair":
                    allowed = allowed and request["auxiliary_reserved"] > 0 and remaining > held + request["synthesis_reserved"]
                else:
                    allowed = allowed and remaining > held + request["synthesis_reserved"] + request["auxiliary_reserved"]
                allowed = allowed and node_count < self.node_limits.get(node, self.complex_limit)
                if not allowed:
                    if required:
                        request["budget_exceeded"] = True
                    return False
                if branch_id is not None:
                    request["branches"][branch_id] += 1
                elif node == "final_synthesis":
                    request["synthesis_reserved"] -= 1
                elif node == "answer_repair":
                    request["auxiliary_reserved"] -= 1
                request["model_calls"] += 1
                request["by_node"][node] = node_count + 1
                return True
            # Once analysis ran, leave one slot for the final grounded answer.
            # Query rewrites and future summaries may not consume it.
            answer_slot_needed = (
                preserve_answer_slot
                and
                node not in {"query_analysis", "collect_answer"}
                and request["by_node"].get("query_analysis", 0) > 0
                and request["by_node"].get("collect_answer", 0) == 0
            )
            available = request["limit"] - request["model_calls"]
            if available <= (1 if answer_slot_needed else 0) or node_count >= self.node_limits.get(node, self.complex_limit):
                if required:
                    request["budget_exceeded"] = True
                return False
            request["model_calls"] += 1
            request["by_node"][node] = node_count + 1
            return True

    def snapshot(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            request = self._requests.get(request_id)
            return {**request, "by_node": dict(request["by_node"])} if request else {
                "model_calls": 0, "by_node": {}, "budget_exceeded": False, "limit": self.simple_limit,
            }

    def finish(self, request_id: str, *, lease_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if lease_id is not None and self._requests.get(request_id, {}).get("lease_id") != lease_id:
                return self.snapshot_missing()
            request = self._requests.pop(request_id, None)
            return {**request, "by_node": dict(request["by_node"])} if request else self.snapshot_missing()

    def snapshot_missing(self) -> dict[str, Any]:
        return {"model_calls": 0, "by_node": {}, "budget_exceeded": False, "limit": self.simple_limit}

def build_model_budget(settings: Settings) -> ModelCallBudget:
    """One source for graph and standalone operation limits."""
    return ModelCallBudget(
        simple_limit=min(settings.max_simple_llm_calls, settings.max_llm_calls_per_request),
        complex_limit=settings.max_llm_calls_per_request,
        node_limits={"query_analysis": settings.max_query_analysis_calls,
            "query_rewrite": settings.max_query_rewrite_calls, "collect_answer": settings.max_answer_calls,
            "orchestrator": settings.max_llm_calls_per_request, "final_synthesis": 1, "answer_repair": 1,
            "conversation_summary": settings.max_summary_calls},
        timeout_seconds=min(300.0, settings.request_timeout_seconds), tool_limit=settings.max_tool_calls)

def summarize_usage(
    traces: list[dict[str, Any]], budget: dict[str, Any], cache_hits: dict[str, int], duration_ms: int,
) -> dict[str, Any]:
    calls = [item for item in traces if not item.get("budget_exceeded") and item.get("attempted", True)]
    actual = sum(item.get("input_tokens") is not None and item.get("output_tokens") is not None
                 and item.get("usage_source", "provider") == "provider" for item in calls)
    partial = any(item.get("usage_source") == "mixed" for item in calls)
    prompt_tokens = sum(int(item.get("input_tokens") if item.get("input_tokens") is not None else item.get("input_tokens_estimate") or 0) for item in calls)
    completion_tokens = sum(int(item.get("output_tokens") if item.get("output_tokens") is not None else item.get("output_tokens_estimate") or 0) for item in calls)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "usage_source": "provider" if actual == len(calls) else "estimate" if actual == 0 and not partial else "mixed",
        "model_calls": int(budget.get("model_calls", len(calls))),
        "model_call_limit": int(budget.get("limit", 0)),
        "tool_calls": int(budget.get("tool_calls", 0)),
        "calls_by_branch": dict(budget.get("branches", {})),
        "tools_by_branch": dict(budget.get("branch_tools", {})),
        "calls_by_node": dict(budget.get("by_node", {})),
        "cache_hits": dict(cache_hits),
        "cache_hit_count": sum(cache_hits.values()),
        "model_duration_ms": sum(int(item.get("duration_ms") or 0) for item in calls),
        "duration_ms": duration_ms,
        "budget_exceeded": bool(budget.get("budget_exceeded", False)),
        "cloud_calls": sum(item.get("provider") == "openai_compatible" for item in calls),
    }

def input_limit(settings: Settings) -> int:
    return max(1, min(settings.max_context_tokens, settings.model_context_window
                     - settings.llm_max_output_tokens - settings.model_context_safety_tokens))

def input_tokens(messages: list[dict], tools: list[dict] | None = None,
                 response_format: dict | None = None) -> int:
    value = {"messages": messages, "tools": tools or []}
    if response_format is not None:
        value["response_format"] = response_format
    return estimate_tokens(json.dumps(value, ensure_ascii=False))

@dataclass(frozen=True)
class CallContext:
    request_id: str
    lease_id: str
    budget: ModelCallBudget
    request_deadline: float
    branch_id: str | None = None
    ownership: str = "shared"

    def __post_init__(self) -> None:
        if not self.request_id or not self.lease_id:
            raise ValueError("call_identity_required")

    @classmethod
    def shared(cls, budget: ModelCallBudget, request_id: str, *, branch_id: str | None = None,
               lease_id: str | None = None) -> CallContext:
        if not request_id:
            raise ValueError("request_id_required")
        lease = budget.lease(request_id)
        identity = (lease_id or "inactive") if lease_id is not None else (lease[0] if lease else uuid4().hex)
        return cls(request_id, identity, budget,
                   lease[1] if lease else time.monotonic(), branch_id)

@contextmanager
def owned_call_context(settings: Settings, *, budget: ModelCallBudget | None = None,
                       request_id: str | None = None, deadline: float | None = None,
                       branch_id: str | None = None) -> Iterator[CallContext]:
    budget = budget if budget is not None else build_model_budget(settings)
    request_id = request_id or str(uuid4())
    lease = budget.start(request_id, deadline=deadline, require_missing=True)
    context = replace(CallContext.shared(budget, request_id, branch_id=branch_id, lease_id=lease), ownership="owned")
    try:
        yield context
    finally:
        budget.finish(request_id, lease_id=lease)

@contextmanager
def operation_context(settings: Settings, *, budget: ModelCallBudget | None = None,
                      request_id: str = "", call_context: CallContext | None = None,
                      lease_id: str | None = None) -> Iterator[CallContext]:
    """Borrow supplied scopes, including invalid ones; only absence creates an owner."""
    if call_context is not None:
        if ((request_id and request_id != call_context.request_id)
                or (budget is not None and budget is not call_context.budget)
                or (lease_id is not None and lease_id != call_context.lease_id)):
            yield replace(call_context, lease_id="context-mismatch", ownership="shared")
        else:
            yield replace(call_context, ownership="shared")
    elif request_id or lease_id is not None:
        shared_budget = budget if budget is not None else build_model_budget(settings)
        yield CallContext.shared(shared_budget, request_id or str(uuid4()), lease_id=lease_id)
    else:
        with owned_call_context(settings, budget=budget) as context:
            yield context

class _Rejected(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)

class _CallGuard:
    def __init__(self, settings: Settings, spec: CallSpec, context: CallContext, deadline: float):
        self.settings, self.spec, self.context, self.deadline = settings, spec, context, deadline
        self.lock = Lock()
        self.closed = False
        self.reserved = False
        self.estimate = None
        self.attempts: list[AttemptRecord] = []

    def __call__(self, prepared: PreparedAttempt) -> float:
        with self.lock:
            if self.closed:
                raise _Rejected("timeout")
            context = self.context
            reason = ""
            if time.monotonic() >= self.deadline:
                reason = "timeout"
            elif not context.budget.active(context.request_id, context.lease_id):
                reason = "budget_exceeded"
            estimate = input_tokens(prepared.messages, prepared.tools, prepared.response_format)
            if not reason and time.monotonic() >= self.deadline:
                reason = "timeout"
            if not reason and estimate > input_limit(self.settings):
                reason = "context_budget_exceeded"
            fallback = (len(self.attempts) == 1 and self.attempts[0].structured_mode == "json_schema"
                        and prepared.structured_mode == "json_object" and prepared.attempt_index == 2)
            if not reason and self.attempts and not fallback:
                reason = "invalid_model_output"
            if not reason and not self.reserved:
                if context.budget.reserve(context.request_id, self.spec.node,
                        branch_id=context.branch_id, required=self.spec.node != "conversation_summary",
                        require_active=True, lease_id=context.lease_id):
                    self.reserved = True
                else:
                    reason = "timeout" if time.monotonic() >= self.deadline else "budget_exceeded"
            if self.attempts and fallback:
                self.attempts[-1] = replace(self.attempts[-1], status="format_rejected", reason="format_unsupported")
            self.attempts.append(AttemptRecord(prepared.attempt_index, prepared.structured_mode, estimate,
                "rejected" if reason else "admitted", reason, time.perf_counter_ns()))
            if reason:
                raise _Rejected(reason)
            self.estimate = estimate
            return max(0.0, self.deadline - time.monotonic())

    def close(self, outcome: str, reason: str) -> tuple[bool, int | None, tuple[AttemptRecord, ...]]:
        with self.lock:
            self.closed = True
            if self.attempts and self.attempts[-1].status == "admitted":
                self.attempts[-1] = replace(self.attempts[-1], status=outcome, reason=reason)
            return self.reserved, self.estimate, tuple(self.attempts)

class ModelCallRunner:
    def __init__(self, settings: Settings, provider: ChatProvider, *, executor: Executor | None = None):
        self.settings, self.provider = settings, provider
        self.executor = executor if executor is not None else _MODEL_EXECUTOR

    def invoke(self, spec: CallSpec, context: CallContext) -> CallOutcome:
        if spec.tools and spec.response_schema is not None:
            raise ValueError("structured_output_cannot_mix_with_tools")
        started = time.monotonic()
        timestamp = time.perf_counter_ns()
        messages, tools = deepcopy(spec.messages), deepcopy(spec.tools)
        diagnostic_messages, diagnostic_tools = deepcopy(messages), deepcopy(tools)
        deadline = min(context.request_deadline, started + self.settings.llm_timeout_seconds)
        guard = _CallGuard(self.settings, spec, context, deadline)
        result = None
        outcome, reason = "completed", ""
        error_type = ""
        future = None
        try:
            if deadline <= time.monotonic():
                raise _Rejected("timeout")
            if not context.budget.active(context.request_id, context.lease_id):
                raise _Rejected("budget_exceeded")
            future = self.executor.submit(complete_model, self.provider, messages, tools=tools,
                response_schema=spec.response_schema, before_attempt=guard)
            result = future.result(timeout=max(0.0, deadline - time.monotonic()))
            if not guard.reserved:
                result = None
                raise _Rejected("model_unavailable")
            if time.monotonic() >= deadline:
                result = None
                raise _Rejected("timeout")
            if not context.budget.active(context.request_id, context.lease_id):
                result = None
                raise _Rejected("budget_exceeded")
        except _Rejected as exc:
            reason = exc.reason
            outcome = "failed" if guard.reserved else "rejected"
        except Exception as exc:
            reason = "timeout" if isinstance(exc, (FutureTimeoutError, TimeoutError)) or "timeout" in type(exc).__name__.lower() else "model_unavailable"
            outcome, error_type = "failed", type(exc).__name__
        finally:
            attempted, estimate, attempts = guard.close(outcome, reason)
            if future is not None and result is None:
                future.cancel()
        if not attempted and spec.node == "conversation_summary":
            outcome = "skipped"
        details = {"input_messages": diagnostic_messages, "tool_definitions": diagnostic_tools or [],
                   "provider": self.settings.llm_provider}
        usage_source = "estimate_only"
        if result is not None:
            result = deepcopy(result)
            details.update(token_details(messages, result))
            details.pop("input_tokens_estimate", None)
            usage_source = details.pop("usage_source")
            if len(attempts) > 1 and usage_source == "provider":
                usage_source = "mixed"
            details.update(candidate_content=result.content, returned_tool_calls=result.tool_calls,
                           structured_mode=result.structured_mode, structured_fallback=result.structured_fallback)
        if reason:
            details["reason"] = reason
            lease = context.budget.lease(context.request_id)
            if lease is None or lease[0] != context.lease_id:
                details["guard_reason"] = "context_inactive"
        if error_type:
            details["error_type"] = error_type
        record = CallRecord(f"model-{uuid4().hex}", context.request_id, context.branch_id or "final",
            spec.node, spec.iteration, timestamp, int((time.monotonic() - started) * 1000), attempted,
            estimate, result.prompt_tokens if result else None, result.completion_tokens if result else None,
            usage_source, attempts, json.dumps(details, ensure_ascii=False))
        return CallOutcome(outcome, result, reason, record)
