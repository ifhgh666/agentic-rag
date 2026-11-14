"""Preserved independent query and evidence APIs outside the active Agent loop."""
from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, Protocol
from ..config import Settings
from .answering import format_evidence_records
from .model_call import (
    BoundedCache,
    CallContext,
    CallSpec,
    ModelCallBudget,
    ModelCallRunner,
    operation_context,
)
from .model_provider import ChatProvider, create_provider
from ..knowledge.retrieval import normalize_query
from ..knowledge.stores import DocumentStore
from .legacy_prompts import get_retrieval_rewrite_input, get_retrieval_rewrite_prompt
from .legacy_cache import RequestToolCache
from ..schemas.chat import RetrievalResult
from ..schemas.documents import DocumentStatus


_MODEL_ID_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,12}[-_]?\d{2,}[A-Za-z0-9-]*(?![A-Za-z0-9])")

_SENTENCE_RE = re.compile(r"(?<=[。！？；;\n])")

_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(个月|mA|ms|Hz|A|V|秒|年|天|℃|%)", re.IGNORECASE)

_CHINESE_VALUE_RE = re.compile(r"([一二三四五六七八九十两]+)(个月|秒|年|天)")

_CHINESE_NUMBERS = {"一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}

_HTML_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)

_HEADING = re.compile(r"(?m)^#{1,6}\s+")

_LIST = re.compile(r"^(?:[-*+]\s+|\d+[.)、]\s*|[一二三四五六七八九十]+、)")

_ENDINGS = tuple("。！？.!?；;")

def normalized(text: str) -> str:
    return "".join(_HTML_BREAK.sub(" ", text).split())

def _matching_section(parent_text: str, markdown: str) -> str:
    expected = normalized(parent_text)
    if not expected:
        return ""
    starts = [match.start() for match in _HEADING.finditer(markdown)]
    bounds = sorted(set([0, *starts, len(markdown)]))
    for position, start in enumerate(bounds[:-1]):
        first = normalized(markdown[start:bounds[position + 1]])
        if not first or not expected.startswith(first[:min(64, len(first))]):
            continue
        for end in bounds[position + 1:]:
            candidate = markdown[start:end]
            candidate_normalized = normalized(candidate)
            if candidate_normalized == expected:
                return candidate
            if len(candidate_normalized) >= len(expected):
                break
    return ""

def recover_paragraphs(parent_text: str, markdown: str) -> list[dict]:
    """只在整个章节与 Parent 一致时恢复单元，排除表格，合并断行与有序列表。"""
    section = _matching_section(parent_text, markdown)
    if not section:
        return []
    units: list[str] = []
    pending = ""
    in_list = False

    def flush():
        nonlocal pending, in_list
        if pending and pending.rstrip().endswith(_ENDINGS):
            units.append(pending.strip())
        pending, in_list = "", False

    for part in re.split(r"\n\s*\n", section):
        text = " ".join(_HTML_BREAK.sub(" ", part).split())
        if not text:
            continue
        if text.startswith(("#", "|")):
            flush()
            continue
        # 无终止标点的短片段也可能是条件的开头，不能当标题丢弃。
        listed = bool(_LIST.match(text))
        if pending and not in_list and not listed and pending.endswith(_ENDINGS):
            flush()
        pending = f"{pending} {text}".strip()
        in_list = in_list or listed
    flush()
    return [{"text": text, "complete": True, "ordinal": index}
            for index, text in enumerate(units) if normalized(text) in normalized(parent_text)]

def read_saved_markdown(document) -> str:
    """仅读取同一文档目录的已有派生文件；缺失或过大时不尝试重解析。"""
    if not document.markdown_path or not document.source_path:
        return ""
    path, source = Path(document.markdown_path).resolve(), Path(document.source_path).resolve()
    if path.parent != source.parent or path.parent.name != str(document.document_id):
        return ""
    try:
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            return ""
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""

def eligible_units(records: list[dict]) -> dict[str, tuple[dict, str, int]]:
    """只允许同时出现在已保留正文和实际提示词中的完整单元。"""
    allowed = {}
    for record in records:
        for index, unit in enumerate(record.get("procedure_units", []), 1):
            text = str(unit.get("text", ""))
            if (text and unit.get("complete") is True and normalized(text) in normalized(str(record.get("raw_text", "")))
                and normalized(text) in normalized(str(record.get("content", "")))):
                allowed[f"{record['citation_id']}.P{index}"] = (record, text, index)
    return allowed

def _terms(text: str) -> set[str]:
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    grams = {part[index : index + 2] for part in chinese for index in range(len(part) - 1)}
    words = {word.lower() for word in re.findall(r"[A-Za-z]{3,}|\d+(?:\.\d+)?", text)}
    return grams | words

def _overlap(question: str, content: str) -> int:
    return len(_terms(question) & _terms(content))

def _focused_excerpt(question: str, text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    sentences = [(index, part.strip()) for index, part in enumerate(_SENTENCE_RE.split(text)) if part.strip()]
    if not sentences:
        return text[:limit]
    ranked = sorted(sentences, key=lambda item: (-_overlap(question, item[1]), item[0]))
    chosen: list[tuple[int, str]] = []
    used = 0
    for index, sentence in ranked:
        if used + len(sentence) > limit:
            continue
        chosen.append((index, sentence))
        used += len(sentence)
    if not chosen:
        return ranked[0][1][:limit]
    return " … ".join(sentence for _, sentence in sorted(chosen))

def _values(sentence: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for number, unit in _VALUE_RE.findall(sentence):
        found.setdefault(unit.lower(), set()).add(number)
    for number, unit in _CHINESE_VALUE_RE.findall(sentence):
        normalized = _CHINESE_NUMBERS.get(number)
        if normalized:
            found.setdefault(unit.lower(), set()).add(normalized)
    return found

def _semantic_similarity(first: str, second: str) -> float:
    first_terms = _terms(_VALUE_RE.sub("数值", first))
    second_terms = _terms(_VALUE_RE.sub("数值", second))
    if not first_terms or not second_terms:
        return 0.0
    return len(first_terms & second_terms) / len(first_terms | second_terms)

def find_numeric_conflict(
    question: str, records: list[dict[str, Any]],
) -> tuple[tuple[dict[str, Any], str], tuple[dict[str, Any], str]] | None:
    """Conservatively detect two near-equivalent relevant claims with disjoint values."""
    claims: list[tuple[dict[str, Any], str, dict[str, set[str]]]] = []
    for record in records:
        for sentence in _SENTENCE_RE.split(str(record.get("raw_text", ""))):
            sentence = sentence.strip()
            values = _values(sentence)
            if values and _overlap(question, sentence) >= 2:
                claims.append((record, sentence, values))
    for index, (left_record, left_sentence, left_values) in enumerate(claims):
        for right_record, right_sentence, right_values in claims[index + 1 :]:
            if left_record.get("record_id") == right_record.get("record_id"):
                continue
            if _semantic_similarity(left_sentence, right_sentence) < 0.55:
                continue
            shared_units = left_values.keys() & right_values.keys()
            if any(left_values[unit].isdisjoint(right_values[unit]) for unit in shared_units):
                return (left_record, left_sentence), (right_record, right_sentence)
    return None

def format_conflict_answer(
    conflict: tuple[tuple[dict[str, Any], str], tuple[dict[str, Any], str]],
) -> str:
    lines = ["检索到相互冲突的资料，无法确定唯一数值。", "", "依据："]
    for record, quote in conflict:
        page = f"第{record['page_start']}页" if record.get("page_start") is not None else "页码未知"
        section = str(record.get("section_title") or "未命名章节")
        lines.append(f"- “{quote}” [来源：{record['source']}，{page}，{section}]")
    return "\n".join(lines)

class EvidenceSelector:
    """From every retrieved Child, load each distinct Parent once and rank complete evidence."""

    def __init__(self, settings: Settings, document_store: DocumentStore, request_cache: RequestToolCache | None = None):
        self.settings = settings
        self.document_store = document_store
        self.request_cache = request_cache

    def select(self, question: str, results: list[RetrievalResult], request_id: str = "", *, procedure_required: bool = False,
               procedure_only: bool = False) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        asked_ids = {item.lower() for item in _MODEL_ID_RE.findall(question)}
        saved_markdown: dict[str, str] = {}
        for result in results:
            if result.score < self.settings.retrieval_min_score:
                continue
            document = self.document_store.get_document(result.document_id)
            if not document or document.status != DocumentStatus.ready:
                continue
            parent_id = str(result.parent_id)
            if parent_id in seen:
                continue
            seen.add(parent_id)

            def load_parent():
                return self.document_store.get_parent(result.parent_id)

            parent = self.request_cache.run(request_id, f"parent::{parent_id}", load_parent) if self.request_cache else load_parent()
            raw_text = parent.text if parent else (result.text or result.content_preview)
            if not raw_text.strip():
                continue
            evidence_ids = {item.lower() for item in _MODEL_ID_RE.findall(raw_text)}
            if asked_ids and evidence_ids and not asked_ids.issubset(evidence_ids):
                continue
            section_title = parent.section_title if parent else result.section_title
            relevance = _overlap(question, f"{section_title} {raw_text}")
            units = []
            if procedure_required and parent:
                key = str(document.document_id)
                if key not in saved_markdown:
                    saved_markdown[key] = read_saved_markdown(document)
                units = recover_paragraphs(raw_text, saved_markdown[key])
            candidates.append({
                "role": "retrieval_result",
                "record_id": parent_id if parent else str(result.child_id),
                "parent_id": parent_id,
                "document_id": str(result.document_id),
                "source": result.filename,
                "section_title": section_title,
                "page_start": parent.page_start if parent else None,
                "page_end": parent.page_end if parent else None,
                "score": result.score,
                "relevance": relevance,
                "raw_text": raw_text.strip(),
                "source_ordinal": parent.ordinal if parent else 0,
                **({"procedure_units": units} if procedure_required else {}),
            })
        candidates.sort(key=lambda item: (
            max((_overlap(question, unit["text"]) for unit in item.get("procedure_units", [])), default=0)
            if procedure_required else item["relevance"], item["relevance"], item["score"],
        ), reverse=True)
        selected: list[dict[str, Any]] = []
        used_chars = 0
        for item in candidates[: self.settings.retrieval_top_k]:
            if procedure_only:
                if not item.get("procedure_units"):
                    continue
                item = {**item, "source_text": item["raw_text"], "procedure_only": True,
                        "raw_text": "\n\n".join(unit["text"] for unit in item["procedure_units"])}
            remaining = self.settings.max_context_chars - used_chars - 140
            if remaining <= 0:
                break
            # 流程段落原子保留，不能把截取过的片段伪装为完整过程。
            if procedure_required and len(item["raw_text"]) > remaining:
                continue
            excerpt = item["raw_text"] if procedure_required else _focused_excerpt(question, item["raw_text"], remaining)
            if not excerpt:
                continue
            selected.append({**item, "raw_text": excerpt})
            used_chars += len(excerpt) + 140
        return format_evidence_records(selected)

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
        call_context: CallContext | None = None, lease_id: str | None = None,
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
        messages = [
            {"role": "system", "content": get_retrieval_rewrite_prompt()},
            {"role": "user", "content": get_retrieval_rewrite_input(
                question, "；".join(previous_queries[-3:]))},
        ]
        with operation_context(self.settings, budget=self.budget, request_id=request_id,
                               call_context=call_context, lease_id=lease_id) as context:
            provider = self.provider or create_provider(self.settings)
            called = ModelCallRunner(self.settings, provider).invoke(CallSpec("query_rewrite", messages), context)
        if called.result is None:
            return "", {**called.record.to_metadata(), "reason": called.reason}
        result = called.result
        candidate = " ".join(result.content.strip().strip('"“”').split())[: self.settings.max_question_chars]
        if not candidate or normalize_query(candidate) in {normalize_query(item) for item in previous_queries}:
            candidate = ""
        if candidate and self.cache and thread_id and version:
            self.cache.put(key, candidate)
        return candidate, {**called.record.to_metadata(), "node": "orchestrator",
                           "reason": "evidence_gap_query_rewrite"}

    def generate(self, question: str, previous_queries: Sequence[str]) -> str:
        return self.generate_with_result(question, previous_queries)[0]
