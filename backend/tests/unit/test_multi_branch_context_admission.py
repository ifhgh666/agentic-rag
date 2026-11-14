"""Independent native branches, ordered synthesis and per-turn reducer reset."""
from langchain_core.messages import AIMessage, ToolMessage
from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, tool_reply, branch_question

def test_three_branches_are_ordered_for_synthesis_and_contexts_stay_local(settings):
    questions = ["first voltage?", "second recovery?", "third condition?"]
    def research(messages, *_):
        q = branch_question(messages)
        if any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(content="Answer for " + q)
        return tool_reply(("search_child_chunks", {"query": q}))
    service, model, _ = make_service(settings, resolver=resolver_for(questions=questions, research=research))
    final, _ = run_turn(service, "original 245 V for 400 ms")
    answers = final["state"]["agent_answers"]
    assert {a["question"] for a in answers} == set(questions)
    text = model.calls[-1]["messages"][-1].content
    assert text.index("first voltage") < text.index("second recovery") < text.index("third condition")
    assert "original 245 V for 400 ms" in text
    assert all(a["contexts"] and a["answer"] == "Answer for " + a["question"] for a in answers)

def test_research_calls_can_exceed_old_twelve_call_request_cap(settings):
    def research(messages, *_):
        n = sum(isinstance(m, ToolMessage) for m in messages)
        return tool_reply(("search_child_chunks", {"query": str(n)})) if n < 4 else AIMessage(content="conclusion")
    service, model, _ = make_service(settings, resolver=resolver_for(questions=["a", "b", "c"], research=research))
    final, _ = run_turn(service)
    assert not final["pending"] and len(model.calls) == 17
    assert len(service.retriever.calls) == 12
    assert len(final["state"]["agent_answers"]) == 3

def test_new_turn_resets_all_previous_branch_answers(settings):
    service, model, _ = make_service(settings, resolver=resolver_for(questions=["old-a", "old-b"]))
    run_turn(service, thread="same")
    model.resolver = resolver_for(questions=["new"], research=lambda *_: AIMessage(content="new answer"))
    final, _ = run_turn(service, "next", thread="same")
    assert [a["question"] for a in final["state"]["agent_answers"]] == ["new"]
    assert "old-a" not in model.calls[-1]["messages"][-1].content
