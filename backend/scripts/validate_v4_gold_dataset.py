"""Read-only PDF provenance and human-review gates; no model or index imports."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

import fitz
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = BACKEND_ROOT.parent / "specs/004-query-clarification-ragas/gold-cases-v1.json"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value


class SourceDocument(Record):
    document_id: UUID
    filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    page_count: int = Field(ge=1, strict=True)
    document_version: str = Field(min_length=1)


class SourceSpan(Record):
    page: int = Field(ge=1, strict=True)
    section: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)


class HistoryMessage(Record):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class FlowStep(Record):
    question: str = Field(default="", max_length=2000)
    action: Literal["auto", "continue_clarification", "new_question", "cancel"] = "auto"
    expected_status: Literal["clarification", "completed", "cancelled"]
    expected_relation: Literal["new_question", "clarification", "uncertain"] | None = None
    expected_questions: list[str] = Field(default_factory=list, max_length=3)
    expected_pending_query: str = ""
    retrieval_expected: bool = False

    @model_validator(mode="after")
    def check_transition(self):
        if self.action != "cancel" and not self.question:
            raise ValueError("普通消息不得为空")
        if self.expected_status == "clarification":
            if not self.expected_pending_query or self.retrieval_expected or self.expected_questions:
                raise ValueError("澄清必须保留待办且不检索")
        elif self.expected_pending_query:
            raise ValueError("完成或取消后不能留下旧待办")
        if self.action == "cancel" and (self.expected_status != "cancelled" or self.retrieval_expected):
            raise ValueError("取消不能检索或产生普通答案")
        if self.expected_status == "completed" and (not self.expected_questions or not self.retrieval_expected):
            raise ValueError("完成交互须指明独立问题和检索预期")
        return self


class AbsenceCheck(Record):
    pages_checked: list[int] = Field(min_length=1)
    terms: list[str] = Field(min_length=1)


class NegativeResponseFixture(Record):
    response: str = Field(min_length=1)
    expected_missing_facts: list[str] = Field(min_length=1)
    expected_status: Literal["issue_found"] = "issue_found"


class GoldCase(Record):
    case_id: str = Field(min_length=1)
    dataset_version: str | None = None
    document_id: UUID | None = None
    document_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    category: str = Field(default="seed", min_length=1)
    case_type: Literal["answerable", "unanswerable", "clarification_flow"]
    question: str = Field(min_length=1, max_length=2000)
    history_fixture: list[HistoryMessage] = Field(default_factory=list)
    reference_answer: str | None = None
    source_spans: list[SourceSpan] = Field(default_factory=list)
    required_facts: list[str] = Field(default_factory=list)
    ordered_facts: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    expected_behavior: Literal["answer", "insufficient_evidence", "clarification", "cancelled", "choose_action"]
    review_status: Literal["draft", "reviewed"] = "draft"
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    review_kind: Literal["human"] | None = None
    flow_steps: list[FlowStep] = Field(default_factory=list)
    flow_expectation_basis: str | None = None
    unanswerable_reason: str | None = None
    absence_check: AbsenceCheck | None = None
    negative_response_fixture: NegativeResponseFixture | None = None
    notes: str = ""

    @field_validator("required_facts", "ordered_facts", "forbidden_claims")
    @classmethod
    def distinct_facts(cls, values):
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("事实列表不能包含空白或重复项")
        return cleaned

    @model_validator(mode="after")
    def check_case(self):
        if self.review_status == "reviewed":
            if not self.reviewer or not self.reviewed_at or self.review_kind != "human":
                raise ValueError("已审核题须有人工审核者、带时区时间和 human 审核类型")
            if self.reviewed_at.utcoffset() is None:
                raise ValueError("审核时间必须包含时区")
        elif self.reviewer is not None or self.reviewed_at is not None or self.review_kind is not None:
            raise ValueError("草案不能冒填正式审核记录")
        needs_answer = self.case_type == "answerable" or self.expected_behavior == "answer"
        if needs_answer and (not self.reference_answer or not self.source_spans or not self.required_facts):
            raise ValueError("可回答题必须有标准答案、来源和必答事实")
        if self.case_type == "answerable" and self.expected_behavior != "answer":
            raise ValueError("可回答题的预期行为须为 answer")
        if self.case_type == "unanswerable":
            if self.expected_behavior != "insufficient_evidence" or self.reference_answer or not self.unanswerable_reason or not self.absence_check:
                raise ValueError("无答案题须记录全篇核对依据，不能臆造事实答案")
        if self.case_type == "clarification_flow":
            if len(self.flow_steps) < 2 or not self.flow_expectation_basis:
                raise ValueError("交互题必须记录逐轮动作与协议依据")
            if self.flow_steps[0].question != self.question:
                raise ValueError("交互题首轮必须对应原问题")
            terminal = {"answer": "completed", "cancelled": "cancelled", "clarification": "clarification", "choose_action": "clarification"}
            if terminal.get(self.expected_behavior) != self.flow_steps[-1].expected_status:
                raise ValueError("交互题最终状态与预期行为不一致")
        if not set(self.ordered_facts).issubset(self.required_facts):
            raise ValueError("有序步骤必须同时列入必答事实")
        if self.negative_response_fixture:
            missing = self.negative_response_fixture.expected_missing_facts
            if not set(missing).issubset(self.required_facts) or any(not item.strip() for item in missing):
                raise ValueError("漏步骤负例须对应已登记的必答事实")
        return self


class GoldDataset(Record):
    schema_version: Literal[1] = 1
    dataset_version: str = Field(min_length=1)
    status: Literal["draft_not_for_formal_scoring", "reviewed"]
    source_document: SourceDocument
    cases: list[GoldCase] = Field(min_length=1)
    notes: str = ""


def normalized(text: str) -> str:
    """Normalize layout whitespace only; never repair numbers or punctuation."""
    return "".join(text.split())


def validate_dataset(payload: dict, pdf_path: Path | str | None = None, *, require_reviewed: bool = False) -> dict:
    report = {"valid": False, "formal_ready": False, "dataset_version": payload.get("dataset_version") if isinstance(payload, dict) else None,
              "case_count": 0, "quotes_checked": 0, "quotes_matched": 0, "eligible_case_ids": [],
              "ragas_case_ids": [], "unreviewed_case_ids": [], "case_results": [], "errors": [], "warnings": []}

    def error(code, message, case_id=None):
        report["errors"].append({"code": code, "message": message, **({"case_id": case_id} if case_id else {})})

    try:
        dataset = GoldDataset.model_validate(payload)
    except ValidationError as exc:
        for item in exc.errors(include_url=False, include_context=False, include_input=False):
            error("schema_invalid", f"{'.'.join(map(str, item['loc']))}: {item['msg']}")
        return report
    report["case_count"] = len(dataset.cases)
    report["unreviewed_case_ids"] = [case.case_id for case in dataset.cases if case.review_status != "reviewed"]
    seen = set()
    for case in dataset.cases:
        if case.case_id in seen:
            error("duplicate_case_id", "题目编号重复", case.case_id)
        seen.add(case.case_id)
        if (case.document_sha256.upper() != dataset.source_document.sha256.upper()
            or case.document_id is not None and case.document_id != dataset.source_document.document_id
            or case.dataset_version is not None and case.dataset_version != dataset.dataset_version):
            error("case_document_mismatch", "题目文档指纹、身份或题集版本与清单不一致", case.case_id)
    path = Path(pdf_path) if pdf_path is not None else BACKEND_ROOT / "data/documents" / str(dataset.source_document.document_id) / "source.pdf"
    try:
        with path.open("rb") as source:
            actual_hash = hashlib.file_digest(source, "sha256").hexdigest().upper()
        report["actual_document_sha256"] = actual_hash
        if actual_hash != dataset.source_document.sha256.upper():
            error("document_hash_mismatch", "PDF 内容已变化，禁止沿用旧题集正式评分")
            return report
        with fitz.open(path) as pdf:
            pages = [page.get_text() for page in pdf]
    except (OSError, RuntimeError, ValueError):
        error("pdf_unreadable", "无法读取指定 PDF")
        return report
    if len(pages) != dataset.source_document.page_count:
        error("page_count_mismatch", "PDF 页数与题集清单不一致")
    normalized_pages = [normalized(text) for text in pages]
    for case in dataset.cases:
        for span in case.source_spans:
            report["quotes_checked"] += 1
            if span.page > len(pages):
                error("page_out_of_range", "来源页码不存在", case.case_id)
            elif normalized(span.source_quote) not in normalized_pages[span.page - 1]:
                error("quote_not_found", "逐字引文不在声明页；只允许归一化排版空白", case.case_id)
            else:
                report["quotes_matched"] += 1
        if case.ordered_facts:
            reference = normalized(case.reference_answer or "")
            positions = [reference.find(normalized(item)) for item in case.ordered_facts]
            if any(position < 0 for position in positions) or positions != sorted(set(positions)):
                error("ordered_facts_invalid", "标准答案遗漏或颠倒已登记的安全步骤", case.case_id)
        if case.absence_check:
            check = case.absence_check
            if sorted(check.pages_checked) != list(range(1, len(pages) + 1)):
                error("absence_review_incomplete", "无答案依据必须记录对全部页面的检查", case.case_id)
            for term in check.terms:
                if not term.strip() or any(normalized(term).casefold() in page.casefold() for page in normalized_pages):
                    error("absence_term_found", "声明未出现的检索词实际存在或为空", case.case_id)
        if case.negative_response_fixture:
            response = normalized(case.negative_response_fixture.response)
            if any(normalized(item) in response for item in case.negative_response_fixture.expected_missing_facts):
                error("negative_fixture_invalid", "负例实际包含了被声明遗漏的步骤", case.case_id)
        report["case_results"].append({"case_id": case.case_id, "case_type": case.case_type,
                                       "review_status": case.review_status,
                                       "source_checks_passed": not any(item.get("case_id") == case.case_id for item in report["errors"])})
    integrity_valid = not report["errors"]
    report["formal_ready"] = integrity_valid and dataset.status == "reviewed" and not report["unreviewed_case_ids"]
    if report["formal_ready"]:
        report["eligible_case_ids"] = [case.case_id for case in dataset.cases]
        report["ragas_case_ids"] = [case.case_id for case in dataset.cases if case.case_type == "answerable"]
    else:
        report["warnings"].append("自动引文与格式核对不是人工审核；无答案语义及标准答案正确性仍须维护者逐题确认。")
    if require_reviewed and not report["formal_ready"]:
        error("review_required", "正式评估要求题集和全部题目已人工审核，且 PDF 指纹与来源检查通过")
    report["valid"] = not report["errors"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只读核对标准答案题集、PDF 引文和人工审核门槛")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--pdf", type=Path, help="默认按文档 ID 定位 backend/data/documents 下的 PDF")
    parser.add_argument("--require-reviewed", action="store_true", help="检查正式评估准入，草案返回非零状态")
    parser.add_argument("--json", action="store_true", help="输出 ASCII 转义 JSON，便于 Windows 工具读取")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(json.dumps({"valid": False, "formal_ready": False, "errors": [{"code": "dataset_unreadable", "message": "无法读取 UTF-8 JSON 题集"}]}, ensure_ascii=True))
        return 2
    report = validate_dataset(payload, args.pdf, require_reviewed=args.require_reviewed)
    print(json.dumps(report, ensure_ascii=args.json, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
