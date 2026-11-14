import json
from types import SimpleNamespace
from unittest.mock import Mock
from langchain_core.messages import AIMessage, ToolMessage
from app.core.model_provider import OllamaProvider, OpenAICompatibleProvider


def messages():
    return [{"role": "user", "content": "欠压条件"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "search-1", "name": "search_child_chunks", "args": {"query": "欠压"}}]},
            {"role": "tool", "name": "search_child_chunks", "tool_call_id": "search-1",
             "content": json.dumps({"results": []})}]


def test_ollama_preserves_assistant_tool_ids_and_all_tool_messages(settings):
    settings.ollama_model = "test"
    model = Mock()
    model.bind_tools.return_value = model
    model.invoke.return_value = AIMessage(content="完成")
    OllamaProvider(settings, model=model).complete(messages(), tools=[{"type": "function", "function": {"name": "search_child_chunks"}}])
    sent = model.invoke.call_args.args[0]
    assert isinstance(sent[1], AIMessage)
    assert sent[1].tool_calls[0]["id"] == "search-1"
    assert isinstance(sent[2], ToolMessage)
    assert sent[2].tool_call_id == "search-1"
    assert sent[2].name == "search_child_chunks"


def test_openai_normalizes_tool_calls_and_serializes_canonical_history(settings):
    settings.llm_base_url, settings.llm_api_key, settings.llm_model = "https://example.test/v1", "test", "test"
    call = Mock()
    call.model_dump.return_value = {"id": "p1", "type": "function", "function": {
        "name": "retrieve_parent_chunks", "arguments": '{"parent_id":"abc"}'}}
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content="", tool_calls=[call]))], usage=None)
    result = OpenAICompatibleProvider(settings, client=client).complete(messages())
    assert result.tool_calls == [{"id": "p1", "name": "retrieve_parent_chunks", "args": {"parent_id": "abc"}, "type": "tool_call"}]
    sent = client.chat.completions.create.call_args.kwargs["messages"]
    assert sent[1]["tool_calls"][0]["function"]["name"] == "search_child_chunks"
    assert json.loads(sent[1]["tool_calls"][0]["function"]["arguments"]) == {"query": "欠压"}
    assert sent[2]["tool_call_id"] == "search-1"
