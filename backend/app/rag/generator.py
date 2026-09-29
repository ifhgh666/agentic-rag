from __future__ import annotations

import time
import json
import re
from typing import Any

from ..config import Settings
from .model_provider import ChatProvider, FakeProvider, create_provider, token_details
from .model_schema import GroundedAnswer
from .cost_control import ModelCallBudget


INSUFFICIENT_ANSWER = "当前知识库中没有足够信息回答这个问题。请上传相关 PDF，或换一种更具体的问法。"
BUDGET_FALLBACK_PREFIX = "模型调用预算已用尽"
SYSTEM_PROMPT = "你只能依据提供的知识库上下文，用中文简洁回答。没有依据时必须说明信息不足。不要输出思考过程。"


class AnswerGenerator:
    def __init__(self, settings: Settings, provider: ChatProvider | None = None, budget: ModelCallBudget | None = None):
        self.settings = settings
        self.provider = provider
        self.budget = budget

    def get_provider(self) -> ChatProvider:
        if self.provider is None:
            self.provider = create_provider(self.settings)
        return self.provider

    def generate_with_result(self, question: str, context: str) -> tuple[str, dict[str, Any] | None]:
        if not context.strip():
            return INSUFFICIENT_ANSWER, None
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"问题：{question}\n\n知识库上下文：\n{context}"},
        ]
        try:
            provider = self.get_provider()
            started = time.perf_counter()
            result = provider.complete(messages)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
        except Exception as exc:
            raise RuntimeError(f"模型提供商调用失败：{exc}") from exc
        return result.content or INSUFFICIENT_ANSWER, {
            "node": "collect_answer",
            "reason": "answer_generation",
            "duration_ms": elapsed_ms,
            **token_details(messages, result),
        }

    def generate(self, question: str, context: str) -> str:
        return self.generate_with_result(question, context)[0]

    def generate_grounded_with_result(
        self, question: str, records: list[dict[str, Any]], gaps: str = "", request_id: str = "",
    ) -> tuple[str, list[str], dict[str, Any] | None]:
        if not records:
            return INSUFFICIENT_ANSWER, [], None
        if self.budget and not self.budget.reserve(request_id, "collect_answer"):
            lines = [f"{BUDGET_FALLBACK_PREFIX}，以下仅列出检索到的原文证据，未生成综合结论。", "", "依据："]
            cited: list[str] = []
            for record in records[:3]:
                citation_id = str(record["citation_id"])
                cited.append(citation_id)
                page = f"第{record['page_start']}页" if record.get("page_start") is not None else "页码未知"
                lines.append(f"- “{str(record['raw_text'])[:240]}” [来源：{record['source']}，{page}，{record.get('section_title') or '未命名章节'}]")
            return "\n".join(lines), cited, None
        context = "\n\n".join(str(item["content"]) for item in records)
        provider = self.get_provider()
        if isinstance(provider, FakeProvider):
            answer, trace = self.generate_with_result(question, context)
            return answer, [str(item["citation_id"]) for item in records], trace

        messages = [
            {"role": "system", "content": (
                "你是严格依据 PDF 证据回答的中文助手。只输出 JSON 对象："
                '{"is_answerable":true,"answer":"回答","citations":[{"citation_id":"E1","quote":"原文连续片段"}],"conflict":false}。'
                "逐条回答问题中每个子问题。没有证据的部分明确写资料不足，不得猜测。"
                "每个事实、步骤和数值必须有至少一条对应引文，quote 必须逐字存在于该编号证据正文。"
                "数值、单位、型号要严格按原文抄写。不同来源结论冲突时 conflict=true，"
                "不要省略与答案同句的限定条件，例如持续时间、适用范围、触发前提或后续处理规则。"
                "展示双方内容并说明无法确定，不可擅自选择其一。不要输出思考过程或额外文字。"
            )},
            {"role": "user", "content": f"问题：{question}\n已知缺口：{gaps or '无'}\n\n证据：\n{context}"},
        ]
        try:
            started = time.perf_counter()
            result = provider.complete(messages)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
        except Exception as exc:
            raise RuntimeError(f"模型提供商调用失败：{exc}") from exc
        trace = {
            "node": "collect_answer", "reason": "grounded_answer_generation",
            "duration_ms": elapsed_ms, **token_details(messages, result),
        }

        def reject(reason: str) -> tuple[str, list[str], dict[str, Any]]:
            trace["validation_status"] = reason
            return INSUFFICIENT_ANSWER, [], trace

        try:
            content = result.content
            parsed = GroundedAnswer.model_validate(json.loads(content[content.index("{") : content.rindex("}") + 1]))
        except (ValueError, KeyError, TypeError):
            return reject("invalid_json")
        if not parsed.is_answerable or not parsed.answer.strip():
            return reject("model_declared_insufficient")

        by_id = {str(item["citation_id"]): item for item in records}
        used: list[tuple[dict[str, Any], str]] = []
        rejected_citations = 0
        remapped_citations = 0
        for citation in parsed.citations:
            record = by_id.get(citation.citation_id)
            quote = citation.quote.strip()
            normalized_quote = "".join(quote.split())
            if not quote:
                rejected_citations += 1
                continue
            if not record or normalized_quote not in "".join(str(record["raw_text"]).split()):
                matches = [item for item in records if normalized_quote in "".join(str(item["raw_text"]).split())]
                if not matches:
                    rejected_citations += 1
                    continue
                record = matches[0]
                remapped_citations += 1
            used.append((record, quote))
        if not used:
            return reject("invalid_citation" if rejected_citations else "missing_citation")
        cited_text = "\n".join(quote for _, quote in used)
        answer = parsed.answer.strip()
        # A terse model response such as "16 A" can omit a condition that is
        # already present in its own exact, verified supporting sentence.
        if not parsed.conflict and len(used) == 1 and len(answer) <= 20:
            quote = used[0][1]
            if len(answer) + 8 < len(quote) <= 200 and "".join(answer.split()) in "".join(quote.split()):
                answer = quote
        quoted_normalized = "".join(cited_text.lower().split())

        def unsupported_reason(value: str) -> str:
            clean = re.sub(r"(?m)^\s*\d+[.、]\s*", "", value)
            numeric_facts = re.findall(r"\d+(?:\.\d+)?\s*(?:ms|mA|A|V|Hz|秒|年|天|个月|℃|%)", clean, flags=re.IGNORECASE)
            if any("".join(fact.lower().split()) not in quoted_normalized for fact in numeric_facts):
                return "unsupported_numeric_fact"
            if any(number not in cited_text for number in re.findall(r"\d+(?:\.\d+)?", clean)):
                return "unsupported_number"
            chinese_numbers = re.findall(r"[一二三四五六七八九十百两]+(?:年|个月|天|秒)", clean)
            if any(fact not in cited_text for fact in chinese_numbers):
                return "unsupported_chinese_number"
            return ""

        invalid_reason = unsupported_reason(answer)
        recovered = False
        if invalid_reason and not parsed.conflict and len(used) == 1 and len(used[0][1]) <= 200:
            # The model may mistype a number or model name. Its exact supporting
            # quote is safe to display verbatim; never patch the number by guesswork.
            answer = used[0][1]
            invalid_reason = unsupported_reason(answer)
            recovered = not invalid_reason
        if invalid_reason:
            return reject(invalid_reason)
        if parsed.conflict:
            if len({str(record["citation_id"]) for record, _ in used}) < 2 or not re.search(r"冲突|不一致|不同|无法确定", answer):
                return reject("invalid_conflict")
        lines = [answer, "", "依据："]
        cited_ids: list[str] = []
        for record, quote in used:
            citation_id = str(record["citation_id"])
            if citation_id not in cited_ids:
                cited_ids.append(citation_id)
            page = f"第{record['page_start']}页" if record.get("page_start") is not None else "页码未知"
            section = str(record.get("section_title") or "未命名章节")
            lines.append(f"- “{quote}” [来源：{record['source']}，{page}，{section}]")
        trace["validation_status"] = "extractive_recovery" if recovered else "accepted"
        trace["rejected_citations"] = rejected_citations
        trace["remapped_citations"] = remapped_citations
        return "\n".join(lines), cited_ids, trace
