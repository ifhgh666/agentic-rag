"""Independent frozen summary API; never used by the reference online graph."""
from __future__ import annotations
import json
from typing import Any, Callable
from ..config import Settings
from .conversation import ConversationMemory
from .model_call import CallContext, CallSpec, ModelCallBudget, ModelCallRunner, input_limit, input_tokens, operation_context
from .model_provider import ChatProvider, estimate_tokens
from .query_analysis import _literal_constraints_preserved
from .legacy_prompts import get_conversation_summary_prompt

def summarize_conversation(
    memory: ConversationMemory, thread_id: str, request_id: str,
    settings: Settings, budget: ModelCallBudget | None, provider_factory: Callable[[], ChatProvider],
    *, call_context: CallContext | None = None, lease_id: str | None = None,
) -> dict[str, Any] | None:
    state = memory.thread_state(thread_id)
    if not state.summary_backlog or settings.llm_provider == "fake":
        return None
    batch = []
    used = estimate_tokens(state.conversation_summary)
    for message in state.summary_backlog:
        tokens = estimate_tokens(message.content)
        if used + tokens > settings.main_history_input_token_limit:
            break
        batch.append(message)
        used += tokens
    if not batch:
        return None
    source = state.conversation_summary + "\n" + json.dumps([item.model_dump() for item in batch], ensure_ascii=False)
    messages = [
        {"role": "system", "content": get_conversation_summary_prompt(memory.summary_max_chars)},
        {"role": "user", "content": source},
    ]
    while batch and input_tokens(messages) > input_limit(settings):
        batch.pop()
        source = state.conversation_summary + "\n" + json.dumps([item.model_dump() for item in batch], ensure_ascii=False)
        messages[-1]["content"] = source
    if not batch:
        return None
    with operation_context(settings, budget=budget, request_id=request_id,
                           call_context=call_context, lease_id=lease_id) as scope:
        try:
            called = ModelCallRunner(settings, provider_factory()).invoke(CallSpec("conversation_summary", messages), scope)
        except Exception:
            return {"node": "conversation_summary", "status": "deferred", "attempted": False,
                    "reason": "model_unavailable", "failure_reason": "summary_unavailable_or_invalid"}
        trace = called.record.to_metadata()
        trace.update(reason="history_window_overflow", status="deferred",
                     failure_reason=called.reason or "summary_unavailable_or_invalid")
        if called.record.attempted:
            trace["input_messages"] = messages
        if called.result is None:
            return trace
        try:
            summary = json.loads(called.result.content).get("summary")
            if not isinstance(summary, str) or not summary.strip() or len(summary) > memory.summary_max_chars:
                raise ValueError("invalid summary")
            user_constraints = state.conversation_summary + "\n" + "\n".join(item.content for item in batch if item.role == "user")
            if not _literal_constraints_preserved(user_constraints, [summary], source):
                raise ValueError("summary lost constraints")
            if not scope.budget.active(scope.request_id, scope.lease_id):
                return trace
            memory.update(thread_id, expected_version=state.state_version, conversation_summary=summary.strip(),
                          summary_backlog=state.summary_backlog[len(batch):])
            trace.update(status="completed")
            trace.pop("failure_reason", None)
        except Exception:
            pass
        return trace
