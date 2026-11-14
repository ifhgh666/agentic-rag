"""Answer generation, citation validation and evidence formatting."""
from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID
from ..config import Settings
from .model_call import CallContext, CallSpec, ModelCallBudget, ModelCallRunner, operation_context
from .model_provider import ChatProvider, FakeProvider, create_provider, estimate_tokens
from .legacy_prompts import (
    get_aggregation_instruction,
    get_aggregation_prompt,
    get_answer_generation_prompt,
    get_answer_repair_prompt,
    get_answer_request_input,
    get_branch_synthesis_payload,
    get_grounded_evidence_payload,
    get_grounded_request_input,
)
from .legacy_schemas import BranchAnswer
from ..schemas.chat import SourceRef, VerificationResult


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
        if item.get("procedure_units"):
            unit_text = "可选择的完整原文段落：\n" + "\n\n".join(
                f"{item['citation_id']}.P{index}: {unit['text']}"
                for index, unit in enumerate(item["procedure_units"], 1)
            )
            item["content"] = f"{label}\n{unit_text}" if item.get("procedure_only") else item["content"] + "\n\n" + unit_text
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

FAILURE_TEXT = {
    "invalid_model_output": "模型返回的动作或答案格式无效，有限修正后仍未完成。",
    "verification_failed": "模型候选答案的引文无法定位，有限修正后仍未通过校验。",
    "budget_exceeded": "本轮模型或工具调用预算已用尽，尚未完成回答。",
    "timeout": "本轮执行达到时间上限，尚未完成回答。",
    "model_unavailable": "本地模型调用失败，尚未完成回答。",
    "context_budget_exceeded": "证据和消息超过模型窗口，无法在本轮预算内完整装载。",
    "cancelled": "本轮已取消。",
    "index_not_ready": "知识库索引尚未就绪，无法执行检索。",
}

def parse_json(content: str) -> dict[str, Any]:
    value = content.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return payload

def validate_answer(content: str, records: list[dict[str, Any]]) -> tuple[BranchAnswer, list[tuple[dict, str]]]:
    payload = parse_json(content)
    if "status" not in payload and isinstance(payload.get("is_answerable"), bool):
        payload["status"] = "answered" if payload["is_answerable"] else "insufficient"
    parsed = BranchAnswer.model_validate(payload)
    by_id = {str(record["citation_id"]): record for record in records}
    used = []
    for citation in parsed.citations:
        record = by_id.get(citation.citation_id)
        quote = citation.quote.strip()
        if not record or not quote or "".join(quote.split()) not in "".join(str(record["raw_text"]).split()):
            raise ValueError(f"INVALID_CITATION:{citation.citation_id}: quote must exist in the original evidence")
        used.append((record, quote))
    for claim in parsed.claims:
        if any(key not in by_id for key in claim.citation_ids):
            raise ValueError("INVALID_CLAIM_CITATION")
        if claim.kind == "document_fact" and (not claim.citation_ids or
                not set(claim.citation_ids).issubset({citation.citation_id for citation in parsed.citations})):
            raise ValueError("DOCUMENT_FACT_REQUIRES_CITATION")
        if claim.kind == "document_fact":
            quotes = "\n".join(c.quote for c in parsed.citations if c.citation_id in claim.citation_ids)
            if not set(re.findall(r"\d+(?:\.\d+)?", claim.text)).issubset(set(re.findall(r"\d+(?:\.\d+)?", quotes))):
                raise ValueError("INVALID_CITATION_DOCUMENT_FACT_NUMBER: document fact differs from its quoted numbers")
    return parsed, used

def render_answer(parsed: BranchAnswer, used: list[tuple[dict, str]]) -> str:
    text = parsed.answer.strip() or "缺少资料：" + "；".join(parsed.missing_information)
    if parsed.missing_information and parsed.status != "insufficient":
        text += "\n\n资料缺口：" + "；".join(parsed.missing_information)
    if used:
        lines = [text, "", "依据："]
        for record, quote in used:
            page = f"第{record['page_start']}页" if record.get("page_start") is not None else "页码未知"
            lines.append(f"- “{quote}” [来源：{record['source']}，{page}，{record.get('section_title') or '未命名章节'}]")
        return "\n".join(lines)
    return text

INSUFFICIENT_ANSWER = "当前知识库中没有足够信息回答这个问题。请上传相关 PDF，或换一种更具体的问法。"

BUDGET_FALLBACK_PREFIX = "模型调用预算已用尽"

class AnswerGenerator:
    def __init__(self, settings: Settings, provider: ChatProvider | None = None, budget: ModelCallBudget | None = None):
        self.settings = settings
        self.provider = provider
        self.budget = budget

    def get_provider(self) -> ChatProvider:
        if self.provider is None:
            self.provider = create_provider(self.settings)
        return self.provider

    def generate_with_result(self, question: str, context: str, *, request_id: str = "",
                             call_context: CallContext | None = None, lease_id: str | None = None) -> tuple[str, dict[str, Any] | None]:
        if not context.strip():
            return INSUFFICIENT_ANSWER, None
        messages = [
            {"role": "system", "content": get_answer_generation_prompt()},
            {"role": "user", "content": get_answer_request_input(question, context)},
        ]
        try:
            with operation_context(self.settings, budget=self.budget, request_id=request_id,
                                   call_context=call_context, lease_id=lease_id) as scope:
                called = ModelCallRunner(self.settings, self.get_provider()).invoke(CallSpec("collect_answer", messages), scope)
                if called.result is None:
                    raise RuntimeError(called.reason)
                return called.result.content or INSUFFICIENT_ANSWER, {
                    **called.record.to_metadata(), "reason": "answer_generation"}
        except Exception as exc:
            raise RuntimeError(f"模型提供商调用失败：{exc}") from exc

    def generate(self, question: str, context: str, *, request_id: str = "",
                 call_context: CallContext | None = None, lease_id: str | None = None) -> str:
        return self.generate_with_result(question, context, request_id=request_id,
                                         call_context=call_context, lease_id=lease_id)[0]

    def _grounded_request(self, question: str, records: list[dict[str, Any]],
                          payload: str, request_id: str, node: str, *, lease_id: str | None = None,
                          call_context: CallContext | None = None):
        with operation_context(self.settings, budget=self.budget, request_id=request_id,
                               call_context=call_context, lease_id=lease_id) as scope:
            return self._grounded_calls(question, records, payload, node, scope)

    def _grounded_calls(self, question: str, records: list[dict[str, Any]],
                        payload: str, node: str, context: CallContext):
        traces = []
        runner = ModelCallRunner(self.settings, self.get_provider())
        messages = [
            {"role": "system", "content": get_aggregation_prompt()},
            {"role": "user", "content": get_grounded_request_input(question, payload)},
        ]
        reason = "invalid_model_output"
        for attempt in range(2):
            outcome = runner.invoke(CallSpec(node if attempt == 0 else "answer_repair", messages,
                                              iteration=attempt), context)
            if outcome.record.attempted:
                traces.append(outcome.record.to_trace())
            if outcome.result is None:
                reason = outcome.reason
                break
            result = outcome.result
            try:
                parsed, used = validate_answer(result.content, records)
                traces[-1]["validation_status"] = "accepted"
                traces[-1]["model_status"] = parsed.status
                return render_answer(parsed, used), [r["citation_id"] for r, _ in used], traces, (
                    "completed" if parsed.status == "answered" else parsed.status), (
                    "model_insufficient_evidence" if parsed.status == "insufficient" else "model_answered")
            except ValueError as exc:
                reason = "verification_failed" if "CITATION" in str(exc) else "invalid_model_output"
                traces[-1]["validation_status"] = reason
                messages.extend([{"role": "assistant", "content": result.content},
                                 {"role": "user", "content": get_answer_repair_prompt(str(exc))}])
        return FAILURE_TEXT[reason], [], traces, "failed", reason

    def generate_grounded_with_result(
        self, question: str, records: list[dict[str, Any]], gaps: str = "", request_id: str = "",
        *, procedure_required: bool = False, include_fact_citations: bool = False,
        call_context: CallContext | None = None, lease_id: str | None = None,
    ) -> tuple[str, list[str], dict[str, Any] | None]:
        """Generate with grounded quotes; both legacy flags are accepted but unused.

        procedure_required/include_fact_citations do not classify the question or
        select citations. The model's validated quotes determine the result.
        """
        if not records:
            return INSUFFICIENT_ANSWER, [], None
        # Explicit fake test mode does not claim semantic or numerical validation.
        if isinstance(self.get_provider(), FakeProvider):
            answer, trace = self.generate_with_result(question, "\n\n".join(r["content"] for r in records),
                request_id=request_id, call_context=call_context, lease_id=lease_id)
            return answer, [r["citation_id"] for r in records], trace
        payload = get_grounded_evidence_payload(json.dumps([
            {"citation_id": r["citation_id"], "content": r["raw_text"], "source": r["source"]}
            for r in records], ensure_ascii=False), gaps)
        answer, ids, traces, status, reason = self._grounded_request(
            question, records, payload, request_id, "collect_answer", call_context=call_context, lease_id=lease_id)
        trace = traces[0] if traces else None
        if trace is not None:
            trace["stop_reason"] = reason
            if len(traces) > 1:
                trace["repair_calls"] = traces[1:]
        return answer, ids, trace

    def synthesize_branch_answers(self, question: str, branches: list[dict],
                                  records: list[dict], request_id: str, *, lease_id: str | None = None,
                                  call_context: CallContext | None = None):
        payload = get_branch_synthesis_payload(json.dumps({
            "instruction": get_aggregation_instruction(),
            "original_question": question,
            "branches": [
            {"question": b["question"], "status": b["result"].get("status"),
             "stop_reason": b["result"].get("stop_reason"),
             "branch_answer": b["result"].get("branch_answer"),
             "runtime_message": b["result"].get("final_answer", "") if b["result"].get("status") == "failed" else ""}
            for b in branches]}, ensure_ascii=False))
        return self._grounded_request(question, records, payload, request_id, "final_synthesis", lease_id=lease_id, call_context=call_context)

class AnswerEvaluator:
    """只核对可定位的引用；不判断语义完整性，不调用模型或离线 Judge。"""

    def evaluate(self, question: str, answer: str, context: str, *, records: list[dict] | None = None) -> VerificationResult:
        if not context.strip() or answer == INSUFFICIENT_ANSWER:
            return VerificationResult(
                evidence_status="insufficient", citation_status="not_applicable", numeric_status="not_applicable",
                reason="当前证据不足。未核验事实正确性和操作步骤完整性。",
            )
        records = records or []
        citation_status = "not_evaluated"
        ids = re.findall(r"\[(E\d+)\]", answer)
        quotes = re.findall(r"“([^”]+)”\s*\[来源：([^\]\n]+)\]", answer)
        if ids:
            by_id = {item.get("citation_id"): item for item in records}
            if any(key not in by_id for key in ids):
                citation_status = "issue_found"
            # 只有编号能证明引用对象存在，不能证明答案引用了哪段原文。
            # 必须由下面的逐字引文与来源匹配才能报告 verified。
        if quotes:
            matched = all(any(
                "".join(quote.split()) in "".join(str(item.get("raw_text", "")).split())
                and location == f"{item.get('source')}，第{item.get('page_start')}页，{item.get('section_title') or '未命名章节'}"
                and item.get("page_start") is not None
                for item in records
            ) for quote, location in quotes)
            if not matched:
                citation_status = "issue_found" if records else "not_evaluated"
            elif citation_status != "issue_found":
                citation_status = "verified"
        return VerificationResult(
            evidence_status="found", citation_status=citation_status,
            reason=("答案只有引用编号，未核验逐字引文。" if ids and not quotes else "")
                + "已取得检索上下文；引文状态仅表示能定位到本次原文记录，不代表事实正确、数值条件正确或步骤完整。",
        )
