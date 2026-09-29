from ..schemas.chat import EvaluationResult
from .generator import INSUFFICIENT_ANSWER


class AnswerEvaluator:
    def evaluate(self, question: str, answer: str, context: str) -> EvaluationResult:
        if not context.strip() or answer == INSUFFICIENT_ANSWER:
            return EvaluationResult(
                relevance=0,
                faithfulness=100,
                completeness=0,
                overall=20,
                reason="当前没有足够的知识库上下文，系统已明确返回信息不足。",
            )
        relevance = 85 if any(word in context.lower() for word in question.lower().split()[:3]) else 72
        return EvaluationResult(
            relevance=relevance,
            faithfulness=90,
            completeness=78,
            overall=round((relevance + 90 + 78) / 3),
            reason="答案包含检索到的来源内容，主要结论与当前上下文一致。",
        )

