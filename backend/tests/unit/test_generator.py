from app.core.answering import AnswerGenerator, INSUFFICIENT_ANSWER


def test_generator_returns_insufficient_answer_without_context(settings):
    assert AnswerGenerator(settings).generate("问题", "") == INSUFFICIENT_ANSWER


def test_generator_uses_context_without_provider(settings):
    answer = AnswerGenerator(settings).generate("问题", "[来源]\n答案证据")
    assert "答案证据" in answer

