"""Question analysis, constraint guards and entrance cache."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable
from ..config import Settings
from .conversation import PreparedQuery
from .model_call import (
    BoundedCache,
    CallContext,
    CallSpec,
    ModelCallBudget,
    ModelCallRunner,
    operation_context,
)
from .model_provider import ChatProvider, FakeProvider, create_provider, estimate_tokens
from .legacy_prompts import REWRITE_PROMPT_VERSION, get_query_analysis_input, get_rewrite_query_prompt
from .legacy_schemas import QueryAnalysis
from .legacy_cache import RequestToolCache


@dataclass(frozen=True)
class AnalysisOutcome:
    is_clear: bool
    questions: list[str]
    clarification: str = ""
    model_trace: dict[str, Any] | None = None
    relation: str = "new_question"
    failure_reason: str | None = None
    source: str = "model"
    # Legacy outcome/cache attribute, outside the three-field model schema;
    # the entrance does not classify procedures or configure graph routing.
    requires_procedure: bool = False
    guard_trace: dict[str, Any] | None = None

QUERY_REWRITE_POLICY_VERSION = "query-rewrite-v1"

REFERENCE_FALLBACK_VERSION = "unique-reference-fallback-v1"

# Literal validation only; these expressions never decide the question's intent.
_MODEL_ID = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,12}[-_]?\d{2,}[A-Za-z0-9-]*(?![A-Za-z0-9])")

_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?(?:\s*(?:mA|A|V|Hz|ms|秒|分钟|小时|天|年|个月|%|℃))?", re.IGNORECASE)

_CONSTRAINTS = ("不能", "不可", "不应", "不要", "禁止", "未", "无", "低于", "高于", "至少", "不超过", "超过", "以下", "以上")

_REFERENCE_MARKERS = re.compile(
    r"(?:它|其|这个(?:设备|型号)?|该(?:设备|型号)?|那个(?:设备|型号)?|前一个|后一个|上述(?:设备|型号)?)"
)

def _literal_constraints_preserved(original: str, questions: list[str], history: str) -> bool:
    combined = "\n".join(questions)
    available = original + "\n" + history
    for pattern in (_MODEL_ID, _NUMBER):
        original_items = {match.group().replace(" ", "").casefold() for match in pattern.finditer(original)}
        available_items = {match.group().replace(" ", "").casefold() for match in pattern.finditer(available)}
        output_items = {match.group().replace(" ", "").casefold() for match in pattern.finditer(combined)}
        if not original_items.issubset(output_items) or not output_items.issubset(available_items):
            return False
    if any(term in original and term not in combined for term in _CONSTRAINTS):
        return False
    return True

def _unique_history_reference(question: str, history: list[dict[str, str]], summary: str) -> str | None:
    """Fill one explicit Chinese reference when history has exactly one model-like object.

    This is deliberately narrower than general coreference resolution. It only repairs
    a model clarification when the current query contains a supported reference marker
    and the available history contains one unique model identifier. Multiple candidates,
    absent history, and non-model object names remain model-owned clarification cases.
    """
    if not _REFERENCE_MARKERS.search(question):
        return None
    history_text = "\n".join([
        summary,
        *(str(item.get("content", "")) for item in history if isinstance(item, dict)),
    ])
    candidates: dict[str, str] = {}
    for match in _MODEL_ID.finditer(history_text):
        candidates.setdefault(match.group().casefold(), match.group())
    if len(candidates) != 1:
        return None
    object_id = next(iter(candidates.values()))
    rewritten = question.strip()
    # Discourse particles before an explicit pronoun do not belong in the retrieval query.
    rewritten = re.sub(r"^(?:那|那么|然后)\s*(?=它|其)", "", rewritten)
    rewritten = re.sub(r"(?:它|其)的", f"{object_id} 的", rewritten, count=1)
    rewritten = re.sub(
        r"(?:它|其|这个设备|该设备|那个设备|这个型号|该型号|那个型号|前一个|后一个|上述设备|上述型号)",
        object_id,
        rewritten,
        count=1,
    )
    if rewritten == question.strip() or not rewritten.strip():
        return None
    return rewritten

class QueryAnalyzer:
    """One bounded model decision per uncached real-model user message."""

    def __init__(
        self, settings: Settings, provider: ChatProvider | None = None,
        *, cache: BoundedCache | None = None, index_version: Callable[[], str] | None = None,
        budget: ModelCallBudget | None = None, request_cache: RequestToolCache | None = None,
    ):
        self.settings = settings
        self.provider = provider
        self.cache = cache
        self.index_version = index_version
        self.budget = budget
        self.request_cache = request_cache

    def analyze(self, question: str, prepared: PreparedQuery, *, thread_id: str = "", request_id: str = "",
                call_context: CallContext | None = None, lease_id: str | None = None) -> AnalysisOutcome:
        original = question.strip()
        relation = "clarification" if prepared.action == "continue_clarification" else "new_question"
        # These are explicit action/state guards, never text intent decisions.
        if prepared.action == "cancel":
            return AnalysisOutcome(False, [], relation="uncertain", source="safe_fallback")
        if prepared.action == "continue_clarification" and not prepared.pending_query:
            return AnalysisOutcome(False, [], "当前没有待补充的问题，请直接开始新问题。",
                                   relation=relation, failure_reason="NO_PENDING_QUERY", source="safe_fallback")
        if prepared.pending_query and prepared.action == "auto":
            return AnalysisOutcome(False, [], "请明确选择继续补充、开始新问题或取消。",
                                   relation="uncertain", source="safe_fallback")
        if not original:
            return AnalysisOutcome(False, [], "请填写问题。", relation=relation,
                                   failure_reason="empty_question", source="safe_fallback")

        # The explicit fake provider is a deterministic test mode, not model analysis.
        if isinstance(self.provider, FakeProvider) or (self.provider is None and self.settings.llm_provider == "fake"):
            return AnalysisOutcome(
                prepared.question_is_clear,
                [prepared.rewritten_query] if prepared.question_is_clear else [],
                prepared.clarification, relation=relation, source="safe_fallback",
            )

        history = prepared.history_messages
        summary = prepared.conversation_summary
        pending = prepared.pending_query if prepared.action == "continue_clarification" else ""
        supplements = prepared.pending_clarifications if pending else []
        effective_original = prepared.resolved_original(original)
        memory_input = summary + json.dumps([history, pending, supplements], ensure_ascii=False)
        if estimate_tokens(memory_input) > self.settings.main_history_input_token_limit:
            return AnalysisOutcome(False, [], "本会话历史或澄清信息过长，请开启新会话后重试。",
                                   relation=relation, failure_reason="history_budget_exceeded", source="safe_fallback")
        history_key = hashlib.sha256(json.dumps(
            [summary, history, pending, supplements, prepared.action], ensure_ascii=False, sort_keys=True,
        ).encode("utf-8")).hexdigest()
        version = self.index_version() if self.index_version else ""
        provider_settings = getattr(self.provider, "settings", self.settings)
        provider_identity = (
            type(self.provider).__module__, type(self.provider).__qualname__, id(self.provider),
            id(getattr(self.provider, "model", None)),
            self.settings.llm_provider, self.settings.ollama_model, self.settings.llm_model,
            provider_settings.llm_provider, provider_settings.ollama_model, provider_settings.llm_model,
            provider_settings.llm_temperature, provider_settings.llm_seed,
        )
        schema_text = json.dumps(QueryAnalysis.model_json_schema(), ensure_ascii=False, sort_keys=True)
        schema_hash = hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
        cache_key = (
            QUERY_REWRITE_POLICY_VERSION, REFERENCE_FALLBACK_VERSION, REWRITE_PROMPT_VERSION,
            "json_schema", schema_hash,
            thread_id, hashlib.sha256(original.encode("utf-8")).hexdigest(),
            history_key, version, provider_identity,
        )
        if self.cache and thread_id and version:
            hit, saved = self.cache.get(cache_key)
            if hit:
                if self.request_cache:
                    self.request_cache.record_hit(request_id, "query_analysis")
                return AnalysisOutcome(saved.is_clear, list(saved.questions), saved.clarification,
                                       relation=relation, source="cache")
        messages = [
            {"role": "system", "content": get_rewrite_query_prompt()},
            {"role": "user", "content": get_query_analysis_input(
                summary,
                json.dumps(history, ensure_ascii=False),
                prepared.action,
                pending,
                json.dumps(supplements, ensure_ascii=False),
                original,
            )},
        ]
        if len(original) > self.settings.max_question_chars:
            return AnalysisOutcome(False, [], "问题分析输入超过模型窗口，请开启新会话或缩短问题。",
                                   relation=relation, failure_reason="context_budget_exceeded", source="safe_fallback")
        try:
            with operation_context(self.settings, budget=self.budget, request_id=request_id,
                                   call_context=call_context, lease_id=lease_id) as context:
                provider = self.provider or create_provider(self.settings)
                called = ModelCallRunner(self.settings, provider).invoke(
                    CallSpec("query_analysis", messages, response_schema=QueryAnalysis), context)
        except Exception:
            return AnalysisOutcome(False, [], "问题分析模型暂时不可用，请稍后重试。",
                relation=relation, failure_reason="model_unavailable", source="safe_fallback")
        if called.result is None:
            trace = called.record.to_trace() if called.record.attempted else None
            if trace is not None:
                trace.update(failure_reason=called.reason, structured_mode="none", structured_fallback=False)
            return AnalysisOutcome(False, [], "问题分析达到边界或模型暂时不可用，请稍后重试。",
                trace, relation=relation, failure_reason=called.reason, source="safe_fallback",
                guard_trace=called.record.to_metadata() if not called.record.attempted else None)
        result = called.result
        trace = called.record.to_trace()
        trace.update(reason="user_message_analysis", original_conditions=effective_original)

        def failure(code: str) -> AnalysisOutcome:
            trace["failure_reason"] = code
            return AnalysisOutcome(False, [], "无法可靠理解该问题，请换一种说法后重试。",
                                   trace, relation=relation, failure_reason=code, source="safe_fallback")

        decision = result.structured_output
        if not isinstance(decision, QueryAnalysis):
            return failure("invalid_model_output")
        if not decision.is_clear:
            fallback_question = _unique_history_reference(original, history, summary)
            if fallback_question:
                trace["reference_fallback"] = {
                    "version": REFERENCE_FALLBACK_VERSION,
                    "source": "unique_history_model_id",
                    "rewritten_question": fallback_question,
                }
                outcome = AnalysisOutcome(True, [fallback_question], model_trace=trace, relation=relation)
            else:
                outcome = AnalysisOutcome(False, [], decision.clarification_needed, trace, relation=relation)
        else:
            questions = decision.questions
            if any(len(item) > self.settings.max_question_chars for item in questions):
                return failure("invalid_model_output")
            # Protocol validation is not semantic/numeric validation. Keep the
            # original independently; real fidelity is an explicit acceptance gate.
            outcome = AnalysisOutcome(True, questions, model_trace=trace, relation=relation)

        if self.cache and thread_id and version:
            self.cache.put(cache_key, AnalysisOutcome(
                outcome.is_clear, list(outcome.questions), outcome.clarification, relation=outcome.relation,
            ))
        return outcome
