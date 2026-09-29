from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from ..config import Settings
from ..knowledge.stores import DocumentStore
from ..schemas.chat import RetrievalResult, SourceRef
from ..schemas.documents import DocumentStatus
from .context_compression import estimate_tokens
from .tools import RequestToolCache


_MODEL_ID_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,12}[-_]?\d{2,}[A-Za-z0-9-]*(?![A-Za-z0-9])")
_SENTENCE_RE = re.compile(r"(?<=[。！？；;\n])")
_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(个月|mA|ms|Hz|A|V|秒|年|天|℃|%)", re.IGNORECASE)
_CHINESE_VALUE_RE = re.compile(r"([一二三四五六七八九十两]+)(个月|秒|年|天)")
_CHINESE_NUMBERS = {"一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}


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


def format_evidence_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign stable display IDs for a final answer and retain auditable source metadata."""
    formatted: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        item = dict(record)
        item["citation_id"] = f"E{index}"
        page_start, page_end = item.get("page_start"), item.get("page_end")
        if page_start is None:
            page = "页码未知"
        elif page_end is not None and page_end != page_start:
            page = f"第{page_start}-{page_end}页"
        else:
            page = f"第{page_start}页"
        label = f"[{item['citation_id']} | 来源：{item['source']} | {page} | 章节：{item.get('section_title') or '未命名章节'}]"
        item["content"] = f"{label}\n{item['raw_text']}"
        item["tokens"] = estimate_tokens(item["content"])
        formatted.append(item)
    return formatted


def source_from_record(record: dict[str, Any]) -> SourceRef:
    return SourceRef(
        document_id=UUID(str(record["document_id"])),
        filename=str(record["source"]),
        section_title=str(record.get("section_title", "")),
        page_start=record.get("page_start"),
        page_end=record.get("page_end"),
    )


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

    def select(self, question: str, results: list[RetrievalResult], request_id: str = "") -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        asked_ids = {item.lower() for item in _MODEL_ID_RE.findall(question)}
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
            })
        candidates.sort(key=lambda item: (item["relevance"], item["score"]), reverse=True)
        selected: list[dict[str, Any]] = []
        used_chars = 0
        for item in candidates[: self.settings.retrieval_top_k]:
            remaining = self.settings.max_context_chars - used_chars - 140
            if remaining <= 0:
                break
            excerpt = _focused_excerpt(question, item["raw_text"], remaining)
            if not excerpt:
                continue
            selected.append({**item, "raw_text": excerpt})
            used_chars += len(excerpt) + 140
        return format_evidence_records(selected)
