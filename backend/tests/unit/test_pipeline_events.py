"""Public answer delivery is aggregation-only and reflects native executions."""
from app.core.pipeline import RagPipeline
from app.observability.logger import StructuredLogger
from tests.fakes.reference_helpers import make_service

def test_pipeline_emits_real_reference_nodes_and_aggregation_only(settings):
    service, _, _ = make_service(settings)
    events = list(RagPipeline(service, StructuredLogger(settings.data_dir / "public.jsonl")).run("What voltage?", thread_id="stream"))
    names = [e["event"] for e in events]
    assert names[-2:] == ["usage", "complete"]
    assert not {"verification", "answer_evaluation"}.intersection(names)
    assert events[-1]["data"]["status"] == "completed"
    answers = [e["data"]["answer"] for e in events if e["event"] == "answer"]
    assert answers and all(answers[-1].startswith(text) for text in answers)
    assert answers[-1] == "Final answer: 230 V.\nSources:\n- guide.pdf"
    real = [e["data"] for e in events if e["event"] in {"node", "tool_call", "model_call"}]
    assert real and all(e["replayed"] is False for e in real)
    assert all(e["loop_protocol_version"] == "reference.v1" for e in real)
    assert {e["node"] for e in real} >= {"rewrite_query", "orchestrator", "tools", "aggregate_answers"}

def test_sources_require_final_names_and_this_request_tool_metadata(settings):
    from tests.fakes.reference_helpers import resolver_for
    service, _, _ = make_service(settings, resolver=resolver_for(aggregate="Answer.\nSources:\n- invented.pdf"))
    events = list(RagPipeline(service, StructuredLogger(settings.data_dir / "sources.jsonl")).run("voltage"))
    answer = [e["data"] for e in events if e["event"] == "answer"][-1]
    assert "invented.pdf" in answer["answer"] and answer["sources"] == []
    assert [e["data"] for e in events if e["event"] == "usage"][-1]["model_call_limit"] is None


def test_research_text_does_not_enter_public_answer_or_usage(settings):
    import json
    from langchain_core.messages import AIMessage
    from tests.fakes.reference_helpers import resolver_for
    service, _, _ = make_service(settings, resolver=resolver_for(
        research=lambda *_: AIMessage(content="PRIVATE_RESEARCH_SENTINEL"), aggregate="Public aggregate."))
    events = list(RagPipeline(service, StructuredLogger(settings.data_dir / "privacy.jsonl")).run("q"))
    assert service.get_state(next(e["data"]["thread_id"] for e in events)).values["agent_answers"][0]["answer"] == "PRIVATE_RESEARCH_SENTINEL"
    assert "PRIVATE_RESEARCH_SENTINEL" not in json.dumps(events)
    assert [e["data"]["answer"] for e in events if e["event"] == "answer"][-1] == "Public aggregate."
