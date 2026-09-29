from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


_SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "jwt_secret", "token"}
_HIDDEN_KEYS = {"prompt", "system_prompt", "reasoning", "chain_of_thought", "thoughts"}
_SECRET_VALUE_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9._~-]+|(?:api[_-]?key|token|secret|password)\s*[=:]\s*[^\s,;]+)",
    re.IGNORECASE,
)


def _safe_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_")


def sanitize_details(value: Any, *, max_chars: int = 1200, key: str = "") -> Any:
    normalized_key = _safe_key(key)
    if normalized_key in _SECRET_KEYS or any(item in normalized_key for item in ("api_key", "authorization", "password")):
        return "[已脱敏]"
    if normalized_key in _HIDDEN_KEYS or any(item in normalized_key for item in ("reasoning", "prompt")):
        return "[已隐藏]"
    if isinstance(value, Mapping):
        return {str(child_key): sanitize_details(child_value, max_chars=max_chars, key=str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [sanitize_details(item, max_chars=max_chars, key=key) for item in value]
    if isinstance(value, tuple):
        return [sanitize_details(item, max_chars=max_chars, key=key) for item in value]
    if isinstance(value, str) and len(value) > max_chars:
        value = value[:max_chars] + "…"
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub("[已脱敏]", value)
    return value


def build_execution_event(
    *,
    request_id: str,
    thread_id: str,
    node: str,
    event: str,
    tool: str | None = None,
    query: str | None = None,
    parent_id: str | None = None,
    duration_ms: int | None = None,
    score: float | None = None,
    iteration: int | None = None,
    tool_call_count: int | None = None,
    details: Mapping[str, Any] | None = None,
    max_chars: int = 1200,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "node": node,
        "event": event,
        "tool": tool,
        "query": sanitize_details(query, max_chars=max_chars, key="query") if query is not None else None,
        "parent_id": parent_id,
        "duration_ms": duration_ms,
        "score": score,
        "iteration": iteration,
        "tool_call_count": tool_call_count,
        "details": sanitize_details(dict(details or {}), max_chars=max_chars),
    }
