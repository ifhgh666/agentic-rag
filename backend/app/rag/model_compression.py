from __future__ import annotations

import json
import time
from typing import Any

from .context_compression import CompressionResult, estimate_tokens
from .evidence import _focused_excerpt
from .model_provider import ChatProvider, token_details
from .cost_control import ModelCallBudget


def _normalized(text: str) -> str:
    return "".join(text.split())


def _short_label(record: dict[str, Any]) -> str:
    page = f"第{record['page_start']}页" if record.get("page_start") is not None else "页码未知"
    return f"[{record['citation_id']} | 来源：{record['source']} | {page}]"


class ModelContextCompressor:
    """Over-threshold only: ask the model to select exact quotes, then validate every quote."""

    def __init__(self, provider: ChatProvider, budget: ModelCallBudget | None = None):
        self.provider = provider
        self.budget = budget

    def compress(
        self, question: str, records: list[dict[str, Any]], threshold: int, request_id: str = "",
    ) -> tuple[CompressionResult, dict[str, Any] | None]:
        context = "\n\n".join(str(record["content"]) for record in records)
        tokens_before = estimate_tokens(context)
        record_tokens_before = sum(int(record.get("tokens", estimate_tokens(str(record["content"])))) for record in records)
        if max(tokens_before, record_tokens_before) <= threshold:
            return CompressionResult(
                context=context, summary="", compressed=False,
                tokens_before=tokens_before, tokens_after=tokens_before,
                threshold=threshold, removed_items=0, record_messages=records,
                record_tokens_before=record_tokens_before, record_tokens_after=record_tokens_before,
            ), None

        if self.budget and not self.budget.reserve(request_id, "context_compression"):
            selected: list[dict[str, Any]] = []
            used = 0
            for record in records:
                label = _short_label(record)
                available = max(0, threshold - used - estimate_tokens(label) - 2)
                if available <= 0:
                    break
                # A contiguous excerpt remains an auditable quote from the PDF.
                quote = str(record["raw_text"])[:available].strip()
                if not quote:
                    continue
                item = {**record, "raw_text": quote, "content": f"{label}\n{quote}"}
                item["tokens"] = estimate_tokens(item["content"])
                if used + item["tokens"] > threshold:
                    continue
                selected.append(item)
                used += item["tokens"] + estimate_tokens("\n\n")
            compressed = "\n\n".join(str(item["content"]) for item in selected)
            return CompressionResult(
                context=compressed, summary="模型调用预算已用尽，仅保留原文摘录。", compressed=True,
                tokens_before=tokens_before, tokens_after=estimate_tokens(compressed), threshold=threshold,
                removed_items=max(0, len(records) - len(selected)), record_messages=selected,
                record_tokens_before=record_tokens_before,
                record_tokens_after=sum(int(item["tokens"]) for item in selected),
            ), None

        messages = [
            {"role": "system", "content": (
                "你是 PDF 证据压缩器。只输出 JSON 对象："
                '{"excerpts":[{"citation_id":"E1","quote":"原文连续片段"}],"gaps":[]}。'
                "为回答问题，从每个有关来源抽取最短的原文连续片段；不要改写或添加事实。"
                "保留型号、全部相关数值及单位、步骤、否定条件和来源；证据没有覆盖的问题写入 gaps。"
                "quote 必须逐字存在于所给证据正文中。"
            )},
            {"role": "user", "content": f"问题：{question}\n\n证据：\n{context}"},
        ]
        started = time.perf_counter()
        reply = self.provider.complete(messages)
        trace = {
            "node": "context_compression", "reason": "context_over_token_threshold",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            **token_details(messages, reply),
        }
        by_id = {str(record["citation_id"]): record for record in records}
        selections: dict[str, str] = {}
        gaps: list[str] = []
        try:
            raw = reply.content
            payload = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
            for item in payload.get("excerpts", []):
                citation_id = str(item.get("citation_id", ""))
                quote = str(item.get("quote", "")).strip()
                record = by_id.get(citation_id)
                if record and quote and _normalized(quote) in _normalized(str(record["raw_text"])):
                    selections[citation_id] = quote
            gaps = [str(item).strip()[:160] for item in payload.get("gaps", []) if str(item).strip()]
        except (ValueError, TypeError, KeyError, AttributeError):
            pass

        # The model may omit a relevant record. Preserve an extractive excerpt of each
        # missing record instead of silently dropping it or trusting an invented quote.
        for record in records:
            citation_id = str(record["citation_id"])
            if citation_id not in selections:
                selections[citation_id] = _focused_excerpt(question, str(record["raw_text"]), 240)

        selected_records: list[dict[str, Any]] = []
        used = 0
        for record in records:
            quote = selections.get(str(record["citation_id"]), "").strip()
            if not quote:
                continue
            item = {**record, "raw_text": quote}
            item["content"] = f"{_short_label(item)}\n{quote}"
            item["tokens"] = estimate_tokens(item["content"])
            separator_tokens = estimate_tokens("\n\n") if selected_records else 0
            if used + separator_tokens + item["tokens"] > threshold:
                gaps.append(f"{record['source']} 的部分证据超出上下文长度，未纳入回答。")
                continue
            selected_records.append(item)
            used += separator_tokens + item["tokens"]

        if not selected_records and records:
            # Even a tiny configured budget should not induce fabricated summaries.
            first = records[0]
            limit = max(1, threshold - estimate_tokens(_short_label(first)) - 2)
            quote = _focused_excerpt(question, str(first["raw_text"]), limit)
            item = {**first, "raw_text": quote}
            item["content"] = f"{_short_label(item)}\n{quote}"
            item["tokens"] = estimate_tokens(item["content"])
            if item["tokens"] <= threshold:
                selected_records = [item]
            gaps.append("上下文预算过小，部分原文证据未纳入。")

        compressed_context = "\n\n".join(str(item["content"]) for item in selected_records)
        summary = "；".join(dict.fromkeys(gaps))
        return CompressionResult(
            context=compressed_context,
            summary=summary,
            compressed=True,
            tokens_before=tokens_before,
            tokens_after=estimate_tokens(compressed_context),
            threshold=threshold,
            removed_items=sum(1 for original in records if original not in selected_records),
            record_messages=selected_records,
            record_tokens_before=record_tokens_before,
            record_tokens_after=sum(int(item["tokens"]) for item in selected_records),
        ), trace
