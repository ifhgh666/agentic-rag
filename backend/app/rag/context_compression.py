from __future__ import annotations

import math
import re
from dataclasses import dataclass


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class CompressionResult:
    context: str
    summary: str
    compressed: bool
    tokens_before: int
    tokens_after: int
    threshold: int
    removed_items: int
    record_messages: list[dict[str, object]]
    record_tokens_before: int
    record_tokens_after: int


def build_context_messages(context: str) -> list[dict[str, object]]:
    """Represent each retrieved context block as an auditable result message."""
    messages: list[dict[str, object]] = []
    for index, block in enumerate((item.strip() for item in context.split("\n\n") if item.strip()), start=1):
        label = block.split("\n", 1)[0].strip() or "证据"
        messages.append(
            {
                "role": "retrieval_result",
                "record_id": f"retrieval-result-{index}",
                "source": label,
                "content": block,
                "tokens": estimate_tokens(block),
            }
        )
    return messages


def _record_token_total(messages: list[dict[str, object]]) -> int:
    return sum(int(message.get("tokens", 0)) for message in messages)


def estimate_tokens(text: str) -> int:
    """Estimate tokens without downloading or loading a tokenizer model.

    Chinese characters are counted individually; Latin words and remaining
    characters use a small deterministic approximation suitable for budgeting.
    This is intentionally a budget guard, not a provider tokenizer.
    """
    if not text or not text.strip():
        return 0
    cjk_count = len(_CJK_RE.findall(text))
    word_chars = sum(len(item) for item in _WORD_RE.findall(text))
    word_tokens = sum(max(1, math.ceil(len(item) / 4)) for item in _WORD_RE.findall(text))
    remaining = max(0, len(text) - cjk_count - word_chars)
    return max(1, cjk_count + word_tokens + math.ceil(remaining / 4))


def dynamic_token_threshold(base_token_threshold: int, token_growth_factor: float, iteration_count: int) -> int:
    """Grow the context budget as retrieval adds more evidence."""
    base = max(1, int(base_token_threshold))
    growth = max(0.0, float(token_growth_factor))
    rounds = max(0, int(iteration_count) - 1)
    return max(base, int(round(base * (1 + growth * rounds))))


def should_compress_context(
    context: str,
    *,
    iteration_count: int,
    base_token_threshold: int,
    token_growth_factor: float,
    context_messages: list[dict[str, object]] | None = None,
) -> bool:
    threshold = dynamic_token_threshold(base_token_threshold, token_growth_factor, iteration_count)
    measured_tokens = _record_token_total(context_messages) if context_messages is not None else estimate_tokens(context)
    return measured_tokens > threshold


def _truncate_to_tokens(text: str, token_limit: int) -> str:
    if token_limit <= 0 or not text:
        return ""
    if estimate_tokens(text) <= token_limit:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if estimate_tokens(text[:middle]) <= token_limit:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip()


def _summary_for_blocks(blocks: list[str]) -> str:
    lines = ["本轮检索证据摘要："]
    for block in blocks:
        parts = block.split("\n", 1)
        label = parts[0].strip() or "证据"
        body = parts[1].strip() if len(parts) > 1 else parts[0].strip()
        excerpt = body[:180].strip()
        if len(body) > len(excerpt):
            excerpt += "……"
        lines.append(f"- {label}：{excerpt}")
    return "\n".join(lines)


def compress_context(
    context: str,
    *,
    context_summary: str,
    iteration_count: int,
    base_token_threshold: int,
    token_growth_factor: float,
    context_messages: list[dict[str, object]] | None = None,
) -> CompressionResult:
    tokens_before = estimate_tokens(context)
    threshold = dynamic_token_threshold(base_token_threshold, token_growth_factor, iteration_count)
    record_messages = context_messages or build_context_messages(context)
    record_tokens_before = _record_token_total(record_messages)
    if max(tokens_before, record_tokens_before) <= threshold:
        return CompressionResult(
            context=context,
            summary=context_summary,
            compressed=False,
            tokens_before=tokens_before,
            tokens_after=tokens_before,
            threshold=threshold,
            removed_items=0,
            record_messages=record_messages,
            record_tokens_before=record_tokens_before,
            record_tokens_after=record_tokens_before,
        )

    blocks = [str(message.get("content", "")).strip() for message in record_messages if str(message.get("content", "")).strip()]
    summary = _summary_for_blocks(blocks)
    if context_summary.strip():
        summary = f"{context_summary.strip()}\n{summary}"

    summary_budget = max(1, threshold // 2)
    evidence_budget = max(1, threshold - summary_budget)
    summary = _truncate_to_tokens(summary, summary_budget)
    evidence_messages: list[dict[str, object]] = []
    per_record_budget = max(1, evidence_budget // max(1, len(record_messages)))
    for message in record_messages:
        excerpt = _truncate_to_tokens(str(message.get("content", "")), per_record_budget)
        if excerpt:
            evidence_messages.append(
                {
                    **message,
                    "content": excerpt,
                    "tokens": estimate_tokens(excerpt),
                    "compressed": True,
                }
            )
    evidence = "\n\n".join(str(message["content"]) for message in evidence_messages)
    evidence = _truncate_to_tokens(evidence, evidence_budget)
    compressed_context = f"[上下文摘要]\n{summary}\n\n[必要证据]\n{evidence}".strip()
    compressed_context = _truncate_to_tokens(compressed_context, threshold)
    record_tokens_after = _record_token_total(evidence_messages)

    return CompressionResult(
        context=compressed_context,
        summary=summary,
        compressed=True,
        tokens_before=tokens_before,
        tokens_after=estimate_tokens(compressed_context),
        threshold=threshold,
        removed_items=sum(
            1
            for before, after in zip(record_messages, evidence_messages, strict=False)
            if str(before.get("content", "")) != str(after.get("content", ""))
        ),
        record_messages=evidence_messages,
        record_tokens_before=record_tokens_before,
        record_tokens_after=record_tokens_after,
    )
