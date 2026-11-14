"""Parallel native research replaces the old analysis/generation service fixtures."""
from threading import Barrier
from langchain_core.messages import AIMessage
from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, branch_question

def test_independent_research_branches_actually_execute_in_parallel(settings):
    barrier = Barrier(3)
    def research(messages, *_):
        question = branch_question(messages)
        barrier.wait(timeout=5)
        return AIMessage(content="Answer " + question)
    service, model, _ = make_service(settings, resolver=resolver_for(questions=["one", "two", "three"], research=research))
    final, _ = run_turn(service, "three needs")
    answers = sorted(final["state"]["agent_answers"], key=lambda r: r["index"])
    assert [(a["question"], a["answer"]) for a in answers] == [("one", "Answer one"), ("two", "Answer two"), ("three", "Answer three")]
    assert len(model.calls) == 5
    assert "Retrieved response 3:" in model.calls[-1]["messages"][-1].content

def test_single_branch_always_uses_the_same_aggregation_path(settings):
    service, model, _ = make_service(settings, resolver=resolver_for(questions=["one"], research=lambda *_: AIMessage(content="Research result")))
    final, _ = run_turn(service)
    assert len(model.calls) == 3
    assert "Research result" in model.calls[-1]["messages"][-1].content
    assert final["state"]["messages"][-1].content.startswith("Final answer:")

def test_model_text_survives_without_programmatic_evidence_substitution(settings):
    conclusion = "245 V for 400 ms causes the modeled protection."
    service, model, _ = make_service(settings, resolver=resolver_for(research=lambda *_: AIMessage(content=conclusion)))
    final, _ = run_turn(service)
    assert final["state"]["agent_answers"][0]["answer"] == conclusion
    assert not service.retriever.calls
