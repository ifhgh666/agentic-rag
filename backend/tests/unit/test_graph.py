"""016 online graph: checkpoint, native research, and mandatory synthesis."""
from langchain_core.messages import AIMessage, ToolMessage
from tests.fakes.reference_helpers import (make_service, run_turn, resolver_for, research_calls,
                                         tool_reply, tool_messages, conversation)

def test_reference_service_search_answer_and_aggregate(settings):
    service, model, results = make_service(settings)
    final, frames = run_turn(service)
    assert not final["pending"]
    assert final["state"]["messages"][-1].content == "Final answer: 230 V.\nSources:\n- guide.pdf"
    assert len(model.calls) == 5
    assert service.retriever.calls == [("voltage", 7, settings.retrieval_min_score)]
    message = tool_messages(model)[0]
    assert str(results[0].parent_id) in message.content and message.artifact["results"]
    assert any("aggregate_answers" in f["data"] for f in frames if f["kind"] == "updates")

def test_same_thread_reuses_checkpoint_without_old_answers(settings):
    service, model, _ = make_service(settings)
    run_turn(service, "First voltage?", thread="same")
    final, _ = run_turn(service, "Second voltage?", thread="same")
    assert len(final["state"]["agent_answers"]) == 1
    assert final["state"]["agent_answers"][0]["question"] == "Second voltage?"
    assert any(m.content == "First voltage?" for m in conversation(service, "same"))
    isolated, _ = run_turn(service, "Unrelated?", thread="other")
    assert all("First voltage?" not in str(m.content) for m in isolated["state"]["messages"])

def test_empty_search_and_unready_index_are_distinct(settings):
    for ready, marker in [(True, "NO_RELEVANT_CHUNKS"), (False, "RETRIEVAL_ERROR: INDEX_NOT_READY")]:
        service, model, _ = make_service(settings, texts=(), ready=ready)
        final, _ = run_turn(service)
        assert not final["pending"] and tool_messages(model)[0].content == marker
        assert len(model.calls) == 5

def test_model_may_choose_second_search(settings):
    def research(messages, *_):
        replies = [m for m in messages if isinstance(m, ToolMessage)]
        if len(replies) < 2:
            return tool_reply(("search_child_chunks", {"query": ["missing", "voltage"][len(replies)]}))
        return AIMessage(content="Model conclusion without BranchAnswer JSON.")
    service, model, _ = make_service(settings, resolver=resolver_for(research=research), answers=lambda q: [])
    final, _ = run_turn(service)
    assert [c[0] for c in service.retriever.calls] == ["missing", "voltage"]
    assert final["state"]["agent_answers"][0]["answer"] == "Model conclusion without BranchAnswer JSON."
    assert len(research_calls(model)) == 3

def test_parent_is_model_selected_without_automatic_read(settings):
    service, model, _ = make_service(settings)
    run_turn(service)
    assert all(m.name == "search_child_chunks" for m in tool_messages(model))
