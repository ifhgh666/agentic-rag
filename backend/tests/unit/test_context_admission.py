"""016 replaces pre-admission with model compression of retrieved messages."""
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, RemoveMessage
from app.rag.nodes import should_compress_context, compress_context
from tests.fakes.reference_helpers import make_service, run_turn, tool_messages
from tests.fakes.reference_model import ScriptedReferenceModel

def state_for(text, summary=""):
    return {"question": "voltage", "messages": [HumanMessage(content="q", id="q"),
        AIMessage(content="", id="a", tool_calls=[{"name": "search_child_chunks", "id": "s", "args": {"query": "voltage"}}]),
        ToolMessage(content=text, name="search_child_chunks", tool_call_id="s", id="t")],
        "context_summary": summary, "retrieval_keys": {"parent::p"}}

def test_exact_reference_threshold_and_one_more_token(monkeypatch):
    state = state_for("original evidence")
    values = iter([2000, 0, 2001, 0])
    monkeypatch.setattr("app.rag.nodes.estimate_context_tokens", lambda _: next(values))
    assert should_compress_context(state).goto == "orchestrator"
    command = should_compress_context(state)
    assert command.goto == "compress_context"
    assert command.update["retrieval_keys"] == {"parent::p", "search::voltage"}

def test_existing_summary_grows_threshold_by_reference_factor(monkeypatch):
    state = state_for("evidence", "prior summary")
    values = iter([1989, 100, 1991, 100])
    monkeypatch.setattr("app.rag.nodes.estimate_context_tokens", lambda _: next(values))
    assert should_compress_context(state).goto == "orchestrator"
    assert should_compress_context(state).goto == "compress_context"

def test_compression_is_one_model_call_and_removes_old_tool_history():
    state = state_for("complete evidence", "old summary")
    state["retrieval_keys"].add("search::voltage")
    model = ScriptedReferenceModel(resolver=lambda *_: AIMessage(content="guide.pdf: 230 V."))
    update = compress_context(state, model)
    assert len(model.calls) == 1
    assert "complete evidence" in model.calls[0]["messages"][-1].content
    assert "old summary" in model.calls[0]["messages"][-1].content
    assert "Parent chunks retrieved:\n- p" in update["context_summary"]
    assert "Search queries already run:\n- voltage" in update["context_summary"]
    assert [m.id for m in update["messages"]] == ["a", "t"]
    assert all(isinstance(m, RemoveMessage) for m in update["messages"])

def test_evidence_is_loaded_before_compression_without_old_input_gate(settings):
    service, model, _ = make_service(settings.model_copy(update={"max_context_tokens": 1}), texts=("x" * 12000,))
    final, _ = run_turn(service)
    summaries = [c for c in model.calls if "research context compressor" in c["messages"][0].content]
    assert summaries and "x" * 12000 in summaries[0]["messages"][-1].content
    assert final["state"]["agent_answers"][0]["contexts"]
    assert any("Already executed" in str(m.content) for c in model.calls for m in c["messages"])
