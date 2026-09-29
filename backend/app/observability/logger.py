import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID

from .execution import sanitize_details


class StructuredLogger:
    def __init__(self, log_path: Path, *, enabled: bool = True, max_chars: int = 1200):
        self.log_path = log_path
        self.enabled = enabled
        self.max_chars = max(1, int(max_chars))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log(
        self,
        level: str,
        module: str,
        message: str,
        request_id: UUID | str | None = None,
        duration_ms: int | None = None,
        error: dict | None = None,
        thread_id: str | None = None,
        node: str | None = None,
        event: str | None = None,
        tool: str | None = None,
        query: str | None = None,
        parent_id: str | None = None,
        score: float | None = None,
        iteration: int | None = None,
        tool_call_count: int | None = None,
        details: dict | None = None,
    ) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "module": module,
            "request_id": str(request_id) if request_id else None,
            "message": message,
            "duration_ms": duration_ms,
            "error": error,
            "thread_id": thread_id,
            "node": node,
            "event": event,
            "tool": tool,
            "query": sanitize_details(query, max_chars=self.max_chars, key="query") if query is not None else None,
            "parent_id": parent_id,
            "score": score,
            "iteration": iteration,
            "tool_call_count": tool_call_count,
            "details": sanitize_details(details or {}, max_chars=self.max_chars),
        }
        entry = sanitize_details(entry, max_chars=self.max_chars)
        if not self.enabled:
            return entry
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def query(
        self,
        level: str | None = None,
        module: str | None = None,
        request_id: str | None = None,
        thread_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if not self.log_path.exists():
            return []
        entries: list[dict] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if level and item.get("level") != level.upper():
                continue
            if module and item.get("module") != module:
                continue
            if request_id and item.get("request_id") != request_id:
                continue
            if thread_id and item.get("thread_id") != thread_id:
                continue
            entries.append(item)
        return entries[-limit:][::-1]
