"""Request-scoped model budgets, bounded reusable caches and safe usage summaries."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
import time
from typing import Any


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

    def __init__(self, simple_limit: int, complex_limit: int, node_limits: dict[str, int]):
        self.simple_limit = max(0, simple_limit)
        self.complex_limit = max(self.simple_limit, complex_limit)
        self.node_limits = {key: max(0, value) for key, value in node_limits.items()}
        self._lock = Lock()
        self._requests: dict[str, dict[str, Any]] = {}

    def start(self, request_id: str) -> None:
        with self._lock:
            self._requests[request_id] = {
                "model_calls": 0, "by_node": {}, "budget_exceeded": False,
                "limit": self.simple_limit,
            }

    def set_complex(self, request_id: str, complex_query: bool) -> None:
        with self._lock:
            request = self._requests.get(request_id)
            if request and complex_query:
                request["limit"] = self.complex_limit

    def reserve(self, request_id: str, node: str) -> bool:
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                # Direct service/unit invocations outside AgentGraphService.run do not
                # have a request budget. Production requests are always registered.
                return True
            node_count = request["by_node"].get(node, 0)
            if request["model_calls"] >= request["limit"] or node_count >= self.node_limits.get(node, self.complex_limit):
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

    def finish(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            request = self._requests.pop(request_id, None)
            return {**request, "by_node": dict(request["by_node"])} if request else self.snapshot_missing()

    def snapshot_missing(self) -> dict[str, Any]:
        return {"model_calls": 0, "by_node": {}, "budget_exceeded": False, "limit": self.simple_limit}


def summarize_usage(
    traces: list[dict[str, Any]], budget: dict[str, Any], cache_hits: dict[str, int], duration_ms: int,
) -> dict[str, Any]:
    calls = [item for item in traces if not item.get("budget_exceeded")]
    actual = sum(item.get("input_tokens") is not None and item.get("output_tokens") is not None for item in calls)
    prompt_tokens = sum(int(item.get("input_tokens") if item.get("input_tokens") is not None else item.get("input_tokens_estimate") or 0) for item in calls)
    completion_tokens = sum(int(item.get("output_tokens") if item.get("output_tokens") is not None else item.get("output_tokens_estimate") or 0) for item in calls)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "usage_source": "provider" if actual == len(calls) else "estimate" if actual == 0 else "mixed",
        "model_calls": int(budget.get("model_calls", len(calls))),
        "model_call_limit": int(budget.get("limit", 0)),
        "calls_by_node": dict(budget.get("by_node", {})),
        "cache_hits": dict(cache_hits),
        "cache_hit_count": sum(cache_hits.values()),
        "model_duration_ms": sum(int(item.get("duration_ms") or 0) for item in calls),
        "duration_ms": duration_ms,
        "budget_exceeded": bool(budget.get("budget_exceeded", False)),
        "cloud_calls": sum(item.get("provider") == "openai_compatible" for item in calls),
    }
