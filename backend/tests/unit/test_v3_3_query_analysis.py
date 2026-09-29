from app.rag.conversation_memory import ConversationMemory
from app.rag.model_provider import ModelResult
from app.rag.query_analysis import QueryAnalyzer


class StubProvider:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def complete(self, messages, *, tools=None):
        self.calls.append(messages)
        return ModelResult(self.content, "fake", "stub", 25, 15)


def test_simple_query_skips_model(settings):
    provider = StubProvider("invalid")
    analyzer = QueryAnalyzer(settings, provider)
    prepared = ConversationMemory().prepare("t", "PX-200 的阈值是多少？")
    result = analyzer.analyze("PX-200 的阈值是多少？", prepared)
    assert result.questions == ["PX-200 的阈值是多少？"]
    assert result.is_clear and not provider.calls and result.model_trace is None


def test_model_splits_complex_question_and_deduplicates(settings):
    provider = StubProvider('{"is_clear":true,"questions":["PX-200 的过流阈值是多少？","PX-200 运行记录保存多久？","PX-200 的过流阈值是多少？"],"clarification_needed":null}')
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


def test_invalid_model_json_falls_back_without_inventing_questions(settings):
    provider = StubProvider("not JSON")
    analyzer = QueryAnalyzer(settings, provider)
    question = "比较阈值以及保留期"
    result = analyzer.analyze(question, ConversationMemory().prepare("t", question))
    assert result.is_clear
    assert result.questions == [question]
    assert result.model_trace["node"] == "query_analysis"


def test_model_cannot_resolve_unbound_reference_by_guessing(settings):
    provider = StubProvider('{"is_clear":true,"questions":["PX-200 的阈值是多少？"],"clarification_needed":null}')
    question = "这个阈值是多少？"
    result = QueryAnalyzer(settings, provider).analyze(question, ConversationMemory().prepare("t", question))
    assert result.is_clear is False
    assert result.questions == []


def test_explicit_model_multi_question_ignores_spurious_model_clarification(settings):
    provider = StubProvider('{"is_clear":false,"questions":[],"clarification_needed":"请说明设备型号。"}')
    question = "PX-200 的过流保护阈值是多少，以及运行记录默认保留多久？"
    result = QueryAnalyzer(settings, provider).analyze(question, ConversationMemory().prepare("t", question))
    assert result.is_clear and len(result.questions) == 2
    assert all("PX-200" in item for item in result.questions)
