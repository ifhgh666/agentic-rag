"""核验事实边界：引用存在不能证明数值正确或流程完整。"""

import copy

from app.config import Settings
from app.core.answering import AnswerEvaluator, AnswerGenerator, INSUFFICIENT_ANSWER
from app.core.legacy_rag import find_numeric_conflict, format_conflict_answer
from scripts.replay_v3_6_q3 import FixedResponseProvider


def records():
    return [{"citation_id": "E1", "raw_text": "先切断输入，等待完全放电，再确认回路无故障，最后按确认键复位。",
             "source": "guide.pdf", "page_start": 3, "section_title": "恢复"}]


def test_citation_id_alone_is_not_a_verified_quote():
    evidence = records()
    result = AnswerEvaluator().evaluate("恢复", "立即复位。[E1]", evidence[0]["raw_text"], records=evidence)
    assert result.citation_status == "not_evaluated"
    assert result.numeric_status == result.completeness_status == "not_evaluated"


def test_exact_quote_can_be_located_even_when_answer_omits_safety_steps():
    evidence = records()
    answer = "按确认键复位。\n\n依据：\n- “最后按确认键复位。” [来源：guide.pdf，第3页，恢复]"
    result = AnswerEvaluator().evaluate("恢复", answer, evidence[0]["raw_text"], records=evidence)
    assert result.citation_status == "verified"
    assert result.completeness_status == "not_evaluated"
    assert not {"overall", "faithfulness", "completeness", "relevance"}.intersection(result.model_dump())


def test_unknown_id_does_not_get_hidden_by_a_valid_quote():
    evidence = records()
    answer = "请复位。[E99] “最后按确认键复位。” [来源：guide.pdf，第3页，恢复]"
    result = AnswerEvaluator().evaluate("恢复", answer, evidence[0]["raw_text"], records=evidence)
    assert result.citation_status == "issue_found" and result.completeness_status != "verified"


def test_no_evidence_does_not_call_answer_model_or_claim_completion():
    provider = FixedResponseProvider({"is_answerable": True, "answer": "猜测"})
    answer, ids, trace = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
        "未知问题", [], procedure_required=True)
    result = AnswerEvaluator().evaluate("未知问题", answer, "")
    assert answer == INSUFFICIENT_ANSWER and not ids and trace is None and not provider.calls
    assert result.evidence_status == "insufficient" and result.completeness_status == "not_evaluated"


def test_numeric_conflict_exposes_both_sources_not_a_correctness_score():
    evidence = [{"record_id": "first", "source": "a.pdf", "page_start": 2, "section_title": "记录",
                 "raw_text": "运行记录默认保留三年，超过期限后按先进先出原则删除。"},
                {"record_id": "second", "source": "b.pdf", "page_start": 4, "section_title": "记录",
                 "raw_text": "运行记录默认保留五年，超过期限后按先进先出原则删除。"}]
    original = copy.deepcopy(evidence)
    conflict = find_numeric_conflict("运行记录默认保留多久？", evidence)
    assert conflict is not None
    answer = format_conflict_answer(conflict)
    result = AnswerEvaluator().evaluate("保留期", answer, "\n".join(r["raw_text"] for r in evidence), records=evidence)
    assert "三年" in answer and "五年" in answer and "无法确定" in answer
    assert result.citation_status == "verified"
    assert result.numeric_status == result.completeness_status == "not_evaluated"
    assert evidence == original
