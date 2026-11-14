from app.core.answering import AnswerEvaluator


def test_evaluator_marks_missing_context_insufficient():
    result = AnswerEvaluator().evaluate("问题", "当前知识库中没有足够信息回答这个问题。请上传相关 PDF，或换一种更具体的问法。", "")
    assert result.evidence_status == "insufficient"
    assert result.completeness_status == "not_evaluated"
    assert "overall" not in result.model_dump()

