from __future__ import annotations

import json
import hashlib
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, TYPE_CHECKING

from ..config import Settings
from .conversation_memory import PreparedQuery
from .model_provider import ChatProvider, create_provider, token_details
from .model_schema import QueryAnalysis
from .query_planner import normalize_query
from .cost_control import BoundedCache, ModelCallBudget

if TYPE_CHECKING:
    from .tools import RequestToolCache


_COMPLEX_MARKERS = re.compile(r"比较|对比|区别|以及|并且|同时|分别|还有|另外|再问|和.*(?:各|分别|多少|什么|如何)|及.*(?:多少|什么|如何|多久)|与.*(?:多少|什么|如何|多久)|[、；;\n]")
_REFERENCE_MARKERS = re.compile(r"它|其|这个|那个|上述|前面|刚才|该设备|该型号|这款|那款|同样")
_MODEL_ID_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,12}[-_]?\d{2,}[A-Za-z0-9-]*(?![A-Za-z0-9])")


def _explicit_multi_question_fallback(question: str) -> list[str]:
    """Reject a spurious clarification only for an explicit-model conjunction."""
    models = _MODEL_ID_RE.findall(question)
    if not models or _REFERENCE_MARKERS.search(question):
        return []
    parts = [item.strip(" ，。？?、") for item in re.split(r"以及|并且|同时|；|;", question) if item.strip(" ，。？?、")]
    if len(parts) < 2 or len(parts) > 3:
        return []
    model = models[0]
    return [f"{part if _MODEL_ID_RE.search(part) else model + ' ' + part}？" for part in parts]


@dataclass(frozen=True)
class AnalysisOutcome:
    is_clear: bool
    questions: list[str]
    clarification: str = ""
    model_trace: dict[str, Any] | None = None


class QueryAnalyzer:
    """简单独立问题直通；歧义或多意图问题由模型输出并验证结构化分析。"""

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

    def analyze(self, question: str, prepared: PreparedQuery, *, thread_id: str = "", request_id: str = "") -> AnalysisOutcome:
        fallback = AnalysisOutcome(
            prepared.question_is_clear,
            [prepared.rewritten_query] if prepared.question_is_clear else [],
            prepared.clarification,
        )
        if len(question.strip()) < 2 or (self.provider is None and self.settings.llm_provider == "fake"):
            return fallback
        if (
            prepared.question_is_clear
            and prepared.rewritten_query == question
            and len(question) > 6
            and len(question) <= 35
            and not _COMPLEX_MARKERS.search(question)
            and not _REFERENCE_MARKERS.search(question)
            and question.count("？") + question.count("?") <= 1
        ):
            return fallback

        if self.budget:
            self.budget.set_complex(request_id, True)
        version = self.index_version() if self.index_version else ""
        history_key = hashlib.sha256(json.dumps(
            [prepared.conversation_summary, prepared.history_messages, prepared.rewritten_query],
            ensure_ascii=False, sort_keys=True,
        ).encode("utf-8")).hexdigest()
        cache_key = (thread_id, version, normalize_query(question), history_key, id(self.provider) if self.provider else self.settings.ollama_model)
        if self.cache and thread_id and version:
            hit, saved = self.cache.get(cache_key)
            if hit:
                if self.request_cache:
                    self.request_cache.record_hit(request_id, "query_analysis")
                return saved
        if self.budget and not self.budget.reserve(request_id, "query_analysis"):
            return fallback

        messages = [
            {"role": "system", "content": (
                "你是 PDF 知识库查询分析器。只输出一个 JSON 对象，不要解释或 Markdown。"
                "字段：is_clear(boolean), questions(最多3个独立、可检索的中文问题), "
                "clarification_needed(string 或 null)。保持原问题的型号、数值和限定条件；"
                "遇到无法确定指代的对象时 is_clear=false，并提出一个最短澄清问题，questions=[]。"
                "不要回答问题，不要臆造型号或事实。"
            )},
            {"role": "user", "content": (
                f"当前问题：{question[:self.settings.max_question_chars]}\n"
                f"对话摘要：{prepared.conversation_summary[-800:]}\n"
                f"最近消息：{prepared.history_messages[-4:]}"
            )},
        ]
        trace: dict[str, Any] | None = None
        try:
            provider = self.provider or create_provider(self.settings)
            started = time.perf_counter()
            result = provider.complete(messages)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            trace = {
                "node": "query_analysis", "reason": "complex_or_ambiguous_query",
                "duration_ms": elapsed_ms, **token_details(messages, result),
            }
            content = result.content.strip()
            first, last = content.find("{"), content.rfind("}")
            if first < 0 or last <= first:
                return AnalysisOutcome(fallback.is_clear, fallback.questions, fallback.clarification, trace)
            analysis = QueryAnalysis.model_validate(json.loads(content[first : last + 1]))
            if not analysis.is_clear:
                recovered = _explicit_multi_question_fallback(question) if prepared.question_is_clear else []
                if recovered:
                    return AnalysisOutcome(True, recovered, "", trace)
                outcome = AnalysisOutcome(False, [], analysis.clarification_needed or fallback.clarification or "请补充问题所指的设备或主题。", trace)
                if self.cache and thread_id and version:
                    self.cache.put(cache_key, AnalysisOutcome(outcome.is_clear, outcome.questions, outcome.clarification))
                return outcome
            if not prepared.question_is_clear and not prepared.history_messages and not prepared.conversation_summary:
                return AnalysisOutcome(False, [], prepared.clarification or "请补充问题所指的设备或主题。", trace)
            questions: list[str] = []
            seen: set[str] = set()
            for item in analysis.questions:
                item = " ".join(item.split()).strip()
                key = normalize_query(item)
                if len(item) < 2 or len(item) > self.settings.max_question_chars or key in seen:
                    continue
                seen.add(key)
                questions.append(item)
            if not questions:
                return AnalysisOutcome(fallback.is_clear, fallback.questions, fallback.clarification, trace)
            outcome = AnalysisOutcome(True, questions[:3], "", trace)
            if self.cache and thread_id and version:
                self.cache.put(cache_key, AnalysisOutcome(outcome.is_clear, outcome.questions, outcome.clarification))
            return outcome
        except (ValueError, TypeError, RuntimeError, KeyError):
            return AnalysisOutcome(fallback.is_clear, fallback.questions, fallback.clarification, trace)
