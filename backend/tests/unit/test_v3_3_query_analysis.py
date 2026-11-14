from app.core.conversation import ConversationMemory
from app.core.model_provider import ModelResult
from app.core.query_analysis import QueryAnalyzer


class StubProvider:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def complete(self, messages, *, tools=None, response_schema=None):
        self.calls.append(messages)
        return ModelResult(self.content, "fake", "stub", 25, 15)


def test_simple_query_uses_model_and_preserves_original(settings):
    provider = StubProvider('{"is_clear":true,"questions":["PX-200 的阈值是多少？"],"clarification_needed":""}')
    analyzer = QueryAnalyzer(settings, provider)
    prepared = ConversationMemory().prepare("t", "PX-200 的阈值是多少？")
    result = analyzer.analyze("PX-200 的阈值是多少？", prepared)
    assert result.questions == ["PX-200 的阈值是多少？"]
    assert result.is_clear and len(provider.calls) == 1 and result.model_trace is not None


def test_model_splits_complex_question(settings):
    provider = StubProvider('{"is_clear":true,"questions":["PX-200 的过流阈值是多少？","PX-200 运行记录保存多久？"],"clarification_needed":""}')
    analyzer = QueryAnalyzer(settings, provider)
    question = "PX-200 的过流阈值是多少，以及运行记录保存多久？"
    result = analyzer.analyze(question, ConversationMemory().prepare("t", question))
    assert result.questions == ["PX-200 的过流阈值是多少？", "PX-200 运行记录保存多久？"]
    assert result.model_trace["node"] == "query_analysis"
    assert result.model_trace["input_tokens"] == 25
    assert len(provider.calls) == 1


def test_model_can_request_clarification_without_search(settings):
    provider = StubProvider('{"is_clear":false,"questions":[],"clarification_needed":"请说明设备型号。"}')
    analyzer = QueryAnalyzer(settings, provider)
    question = "这个阈值是多少？"
    result = analyzer.analyze(question, ConversationMemory().prepare("t", question))
    assert result.is_clear is False
    assert result.clarification == "请说明设备型号。"
    assert result.questions == []


def test_invalid_model_json_fails_without_inventing_questions(settings):
    provider = StubProvider("not JSON")
    analyzer = QueryAnalyzer(settings, provider)
    question = "比较阈值以及保留期"
    result = analyzer.analyze(question, ConversationMemory().prepare("t", question))
    assert not result.is_clear
    assert result.questions == [] and result.failure_reason == "invalid_model_output"
    assert result.model_trace["node"] == "query_analysis"


def test_structural_validation_does_not_claim_unbound_reference_is_correct(settings):
    provider = StubProvider('{"is_clear":true,"questions":["PX-200 的阈值是多少？"],"clarification_needed":""}')
    question = "这个阈值是多少？"
    result = QueryAnalyzer(settings, provider).analyze(question, ConversationMemory().prepare("t", question))
    assert result.is_clear and result.failure_reason is None
    assert result.model_trace["original_conditions"] == question
    # Accepting injected structured output proves no semantic fidelity.


def test_explicit_model_multi_question_does_not_override_model_clarification(settings):
    provider = StubProvider('{"is_clear":false,"questions":[],"clarification_needed":"请说明设备型号。"}')
    question = "PX-200 的过流保护阈值是多少，以及运行记录默认保留多久？"
    result = QueryAnalyzer(settings, provider).analyze(question, ConversationMemory().prepare("t", question))
    assert not result.is_clear and result.questions == []
    assert result.clarification == "请说明设备型号。"
