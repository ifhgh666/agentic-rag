from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import time
from typing import Any, Callable, TYPE_CHECKING

from ..config import Settings
from .model_provider import ChatProvider, create_provider, token_details
from .cost_control import BoundedCache, ModelCallBudget

if TYPE_CHECKING:
    from .tools import RequestToolCache


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


class QueryGenerator(Protocol):
    def generate(self, question: str, previous_queries: Sequence[str]) -> str:
        """生成一个不重复的补充检索 Query；没有候选时返回空字符串。"""


class RuleBasedQueryGenerator:
    """V2-4 默认 Query 生成器；后续可替换为模型调用而不改变图路由。"""

    def candidates(self, question: str) -> list[str]:
        base = " ".join(question.strip().split())
        if not base:
            return []
        return [
            f"{base} 关键步骤和工作过程",
            f"{base} 原理与触发条件",
            f"{base} 详细说明和注意事项",
        ]

    def generate(self, question: str, previous_queries: Sequence[str]) -> str:
        previous = {normalize_query(item) for item in previous_queries}
        for candidate in self.candidates(question):
            if normalize_query(candidate) not in previous:
                return candidate
        return ""


class ModelQueryGenerator:
    """仅在证据缺失或明确不匹配时请求模型生成一次不同的检索表达。"""

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

    def generate_with_result(
        self, question: str, previous_queries: Sequence[str], *, thread_id: str = "", request_id: str = "",
    ) -> tuple[str, dict[str, Any] | None]:
        version = self.index_version() if self.index_version else ""
        key = (
            thread_id, version, normalize_query(question),
            tuple(normalize_query(item) for item in previous_queries),
            id(self.provider) if self.provider else self.settings.ollama_model,
        )
        if self.cache and thread_id and version:
            hit, saved = self.cache.get(key)
            if hit:
                if self.request_cache:
                    self.request_cache.record_hit(request_id, "query_rewrite")
                return saved, None
        if self.budget and not self.budget.reserve(request_id, "query_rewrite"):
            return "", None
        messages = [
            {"role": "system", "content": (
                "你是 PDF 知识库的检索词改写器。原检索证据不足。只输出一个新的检索问题，"
                "保留设备型号、数值限制和主题；不得回答、猜测事实或重复旧查询。"
            )},
            {"role": "user", "content": f"原问题：{question}\n已检索：{'；'.join(previous_queries[-3:])}"},
        ]
        provider = self.provider or create_provider(self.settings)
        started = time.perf_counter()
        result = provider.complete(messages)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        candidate = " ".join(result.content.strip().strip('"“”').split())[: self.settings.max_question_chars]
        if not candidate or normalize_query(candidate) in {normalize_query(item) for item in previous_queries}:
            candidate = ""
        if candidate and self.cache and thread_id and version:
            self.cache.put(key, candidate)
        return candidate, {
            "node": "orchestrator", "reason": "evidence_gap_query_rewrite",
            "duration_ms": elapsed_ms, **token_details(messages, result),
        }

    def generate(self, question: str, previous_queries: Sequence[str]) -> str:
        return self.generate_with_result(question, previous_queries)[0]
