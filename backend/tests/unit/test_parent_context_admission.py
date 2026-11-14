"""Full saved Parent retrieval replaces model-selected character windows."""
from uuid import uuid4
from langchain_core.messages import AIMessage, ToolMessage
from tests.fakes.reference_helpers import make_service, resolver_for, run_turn, tool_reply, tool_messages

def test_valid_parent_can_be_read_before_search_and_has_complete_original(settings):
    text = "BEGIN original section " + "full chapter " * 500 + " END"
    service, model, rows = make_service(settings, texts=(text,))
    parent_id = str(rows[0].parent_id)
    def research(messages, *_):
        if any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(content="The whole chapter is available.")
        return tool_reply(("retrieve_parent_chunks", {"parent_id": parent_id}))
    model.resolver = resolver_for(research=research)
    final, _ = run_turn(service)
    reply = tool_messages(model)[0]
    assert text in reply.content and reply.artifact["parent"]["text"] == text
    assert not service.retriever.calls and final["state"]["agent_answers"][0]["contexts"]

def test_unknown_parent_is_not_fabricated_and_invalid_uuid_is_safe(settings):
    service, model, _ = make_service(settings)
    parent = next(t for t in service.tools if t.name == "retrieve_parent_chunks")
    assert parent.invoke({"parent_id": str(uuid4())}) == "NO_PARENT_DOCUMENT"
    assert parent.invoke({"parent_id": "invalid"}) == "PARENT_RETRIEVAL_ERROR: ValueError"

def test_parent_schema_has_no_window_or_request_parameters(settings):
    service, _, _ = make_service(settings)
    parent = next(t for t in service.tools if t.name == "retrieve_parent_chunks")
    assert set(parent.args) == {"parent_id"}
    assert "offset" not in parent.args and "max_chars" not in parent.args

def test_repeated_parent_is_available_without_online_cache_side_effects(settings):
    service, _, rows = make_service(settings, texts=("complete chapter",))
    parent = next(t for t in service.tools if t.name == "retrieve_parent_chunks")
    first = parent.invoke({"parent_id": str(rows[0].parent_id)})
    assert first == parent.invoke({"parent_id": str(rows[0].parent_id)})
    assert first.endswith("Content: complete chapter")
