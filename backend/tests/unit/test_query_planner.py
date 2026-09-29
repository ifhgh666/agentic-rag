from app.rag.model_provider import ModelResult
from app.rag.query_planner import ModelQueryGenerator, RuleBasedQueryGenerator


def test_query_generator_returns_a_new_non_duplicate_query():
    generator = RuleBasedQueryGenerator()
    first = generator.generate("PN8733 上电过程", [])
    second = generator.generate("PN8733 上电过程", [first])

    assert first
    assert second
    assert second != first


def test_query_generator_stops_when_all_candidates_are_used():
    generator = RuleBasedQueryGenerator()
    candidates = generator.candidates("保护功能")

    assert generator.generate("保护功能", candidates) == ""


def test_model_query_generator_rewrites_on_evidence_gap_and_records_usage(settings):
    class Provider:
        def complete(self, messages, *, tools=None):
            return ModelResult("PX-200 过流保护电流", "fake", "rewrite-stub", 20, 8)

    generator = ModelQueryGenerator(settings, Provider())
    query, trace = generator.generate_with_result("PX-200 过流阈值是多少？", ["PX-200 过流阈值是多少？"])
    assert query == "PX-200 过流保护电流"
    assert trace["node"] == "orchestrator"
    assert trace["input_tokens"] == 20
    assert generator.generate("PX-200 过流阈值是多少？", [query]) == ""
