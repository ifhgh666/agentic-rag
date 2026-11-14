"""Reference strings and artifact provenance; standalone legacy cache retained."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
from uuid import uuid4
import pytest
from langchain_core.messages import ToolMessage
from app.core.legacy_cache import RequestToolCache
from app.schemas.documents import DocumentStatus
from tests.fakes.reference_helpers import make_service

def invoke_artifact(tool, args):
    return tool.invoke({"type": "tool_call", "name": tool.name, "id": "tool-id", "args": args})

def test_child_tool_returns_reference_text_and_real_artifact(settings):
    service, _, rows = make_service(settings)
    tool = service.tools[0]
    reply = invoke_artifact(tool, {"query": "voltage", "limit": 1})
    assert isinstance(reply, ToolMessage) and reply.tool_call_id == "tool-id"
    assert reply.content == f"Parent ID: {rows[0].parent_id}\nFile Name: guide.pdf\nContent: voltage is 230 V."
    assert reply.artifact["results"][0]["child_id"] == str(rows[0].child_id)
    assert set(tool.args) == {"query", "limit"}
    assert service.retriever.calls == [("voltage", 1, settings.retrieval_min_score)]

@pytest.mark.parametrize("args", [{"query": ""}, {"query": "q", "limit": 0}, {"query": "q", "limit": 21}])
def test_invalid_search_is_a_safe_reference_error(settings, args):
    service, _, _ = make_service(settings)
    assert service.tools[0].invoke(args) == "RETRIEVAL_ERROR: INVALID_QUERY"
    assert not service.retriever.calls

def test_index_readiness_and_private_search_failure_are_not_empty_results(settings):
    service, _, _ = make_service(settings, ready=False)
    assert service.tools[0].invoke({"query": "q"}) == "RETRIEVAL_ERROR: INDEX_NOT_READY"
    service.retriever.index_store.ready = True
    service.retriever.answers = lambda q: OSError("PRIVATE_PATH_AND_KEY")
    reply = service.tools[0].invoke({"query": "q"})
    assert reply == "RETRIEVAL_ERROR: OSError" and "PRIVATE" not in reply

def test_parent_is_complete_and_ready_document_boundary_is_preserved(settings):
    service, _, rows = make_service(settings, texts=("complete section " * 300,))
    parent = service.tools[1]
    reply = invoke_artifact(parent, {"parent_id": str(rows[0].parent_id)})
    assert reply.artifact["parent"]["text"] == rows[0].text
    assert reply.content.endswith(rows[0].text.strip())
    assert set(parent.args) == {"parent_id"}
    document = service.document_store.get_document(rows[0].document_id)
    service.document_store.save_document(document.model_copy(update={"status": DocumentStatus.failed}))
    assert parent.invoke({"parent_id": str(rows[0].parent_id)}) == "NO_PARENT_DOCUMENT"

def test_request_tool_cache_executes_same_key_once_even_when_parallel():
    cache = RequestToolCache()
    guard = Lock()
    calls = []

    def load():
        with guard:
            calls.append(1)
        sleep(0.02)
        return {"content": "证据"}

    with ThreadPoolExecutor(max_workers=3) as pool:
        values = list(pool.map(lambda _: cache.run("request-1", "parent::p", load), range(3)))
    assert values == [{"content": "证据"}] * 3
    assert len(calls) == 1
    cache.clear("request-1")
    assert cache.run("request-1", "parent::p", load) == {"content": "证据"}
    assert len(calls) == 2
