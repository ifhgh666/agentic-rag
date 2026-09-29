from app.rag.evaluator import AnswerEvaluator


def test_evaluator_scores_missing_context_low():
    result = AnswerEvaluator().evaluate("问题", "当前知识库中没有足够信息回答这个问题。请上传相关 PDF，或换一种更具体的问法。", "")
    assert result.overall < 50
    assert 0 <= result.relevance <= 100

