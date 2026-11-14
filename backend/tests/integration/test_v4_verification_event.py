"""Independent legacy evaluator checks; current chat has no online verification."""
import pytest
from app.core.answering import AnswerEvaluator
from app.schemas.chat import VerificationResult

def test_missing_evidence_never_claims_verification():
    result = AnswerEvaluator().evaluate("问题", "证据不足", "")
    assert result.evidence_status == "insufficient"
    assert result.citation_status != "verified" and result.completeness_status != "verified"


def test_omitted_safety_steps_are_not_reported_complete():
    result = AnswerEvaluator().evaluate("恢复步骤", "清除告警后重新启动。",
                                        "先断开负载，等待完全放电，再检查负载。")
    assert result.completeness_status == "not_evaluated"
    assert "overall" not in result.model_dump()


def test_unknown_citation_is_flagged_and_valid_id_alone_remains_unverified():
    records = [{"citation_id": "E1", "raw_text": "阈值超过 16 A 持续 100 ms。",
                "document_id": "doc", "source": "guide.pdf", "page_start": 3}]
    evaluator = AnswerEvaluator()
    bad = evaluator.evaluate("阈值", "超过 16 A。[E99]", records[0]["raw_text"], records=records)
    assert bad.citation_status == "issue_found"
    good = evaluator.evaluate("阈值", "超过 16 A。[E1]", records[0]["raw_text"], records=records)
    assert good.citation_status == "not_evaluated"
    assert "只有引用编号" in good.reason
    assert good.numeric_status == "not_evaluated" and good.completeness_status == "not_evaluated"


def test_verification_schema_rejects_legacy_fields():
    with pytest.raises(ValueError):
        VerificationResult(overall=84, evidence_status="found", reason="旧评分不能进入新契约")


@pytest.mark.parametrize("quote,page,expected", [
    ("阈值超过 16 A 持续 100 ms。", 3, "verified"),
    ("阈值超过 26 A。", 3, "issue_found"),
    ("阈值超过 16 A 持续 100 ms。", 4, "issue_found"),
])
def test_generator_quote_format_checks_raw_quote_and_page(quote, page, expected):
    records = [{"raw_text": "阈值超过 16 A 持续 100 ms。", "source": "guide.pdf",
                "page_start": 3, "section_title": "保护功能"}]
    answer = f"“{quote}” [来源：guide.pdf，第{page}页，保护功能]"
    result = AnswerEvaluator().evaluate("阈值", answer, records[0]["raw_text"], records=records)
    assert result.citation_status == expected
    assert result.numeric_status == "not_evaluated"
    assert result.completeness_status == "not_evaluated"

