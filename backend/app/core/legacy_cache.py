"""Frozen independent legacy cache; not used by the online graph."""
from concurrent.futures import Future
from threading import Lock
from typing import Any, Callable

def dynamic_token_threshold(
    base_token_threshold: int,
    token_growth_factor: float,
    iteration_count: int,
) -> int:
    """Calculate the evidence-window threshold for the current retrieval round."""
    base = max(1, int(base_token_threshold))
    growth = max(0.0, float(token_growth_factor))
    rounds = max(0, int(iteration_count) - 1)
    return max(base, int(round(base * (1 + growth * rounds))))

class RequestToolCache:
    """同一请求的并行 Agent 共享单飞缓存；请求结束后清空。"""

    def __init__(self):
        self._lock = Lock()
        self._items: dict[tuple[str, str], Future] = {}
        self._hits: dict[str, dict[str, int]] = {}

    def run(self, request_id: str, key: str, operation: Callable[[], Any]) -> Any:
        return self.run_with_status(request_id, key, operation)[0]

    def run_with_status(self, request_id: str, key: str, operation: Callable[[], Any]) -> tuple[Any, bool]:
        if not request_id:
            return operation(), False
        with self._lock:
            identity = (request_id, key)
            future = self._items.get(identity)
            owner = future is None
            if owner:
                future = Future()
                self._items[identity] = future
            else:
                self._record_hit_locked(request_id, "request_tool")
        if owner:
            try:
                future.set_result(operation())
            except BaseException as exc:
                future.set_exception(exc)
                raise
        return future.result(), not owner

    def _record_hit_locked(self, request_id: str, category: str) -> None:
        values = self._hits.setdefault(request_id, {})
        values[category] = values.get(category, 0) + 1

    def record_hit(self, request_id: str, category: str) -> None:
        if request_id:
            with self._lock:
                self._record_hit_locked(request_id, category)

    def stats(self, request_id: str) -> dict[str, int]:
        with self._lock:
            return dict(self._hits.get(request_id, {}))

    def clear(self, request_id: str) -> None:
        with self._lock:
            for key in [key for key in self._items if key[0] == request_id]:
                del self._items[key]
            self._hits.pop(request_id, None)
