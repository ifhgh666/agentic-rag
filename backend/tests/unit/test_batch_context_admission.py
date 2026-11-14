"""ToolNode batches keep native reply identities; no admission feedback batch."""
from langchain_core.messages import AIMessage, ToolMessage
from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, tool_reply, research_calls

def test_one_native_batch_pairs_valid_empty_and_invalid_tool_replies(settings):
    def research(messages, *_):
        if any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(content="A batch result.")
        return tool_reply(("search_child_chunks", {"query": "voltage"}),
                          ("search_child_chunks", {"query": ""}),
                          ("missing_tool", {}))
    service, model, _ = make_service(settings, resolver=resolver_for(research=research))
    final, _ = run_turn(service)
    replies = [m for m in research_calls(model)[-1]["messages"] if isinstance(m, ToolMessage)]
    assert len(replies) == 3 and len({m.tool_call_id for m in replies}) == 3
    assert "Parent ID:" in replies[0].content
    assert "INVALID_QUERY" in replies[1].content
    assert "not a valid tool" in replies[2].content
    assert final["state"]["agent_answers"][0]["answer"] == "A batch result."

def test_batch_exceeding_eight_requested_tools_goes_to_normal_model_fallback(settings):
    resolver = resolver_for(research=lambda *_: tool_reply(*[("search_child_chunks", {"query": str(i)}) for i in range(9)]))
    service, model, _ = make_service(settings, resolver=resolver)
    final, _ = run_turn(service)
    assert not service.retriever.calls
    assert any("constrained evidence synthesizer" in c["messages"][0].content for c in model.calls)
    assert final["state"]["agent_answers"][0]["answer"]
    assert not final["pending"]

def test_repeated_native_tool_request_is_not_deduplicated_by_old_request_cache(settings):
    def research(messages, *_):
        count = sum(isinstance(m, ToolMessage) for m in messages)
        return tool_reply(("search_child_chunks", {"query": "same"})) if count < 2 else AIMessage(content="done")
    service, model, _ = make_service(settings, resolver=resolver_for(research=research))
    run_turn(service)
    assert [c[0] for c in service.retriever.calls] == ["same", "same"]
    assert len(research_calls(model)) == 3
