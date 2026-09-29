from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep

import pytest

from app.knowledge.stores import DocumentStore
from app.rag.tools import RequestToolCache, create_rag_tools
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class FakeIndex:
    def __init__(self, ready=True):
        self.ready = ready


class FakeRetriever:
    def __init__(self, result, ready=True):
        self.index_store = FakeIndex(ready)
        self.result = result
        self.calls = []

    def search(self, query, top_k=None, min_score=None):
        self.calls.append((query, top_k, min_score))
        return self.result


def _ready_document(document_store, document_id):
    document_store.save_document(
        KnowledgeDocument(
            document_id=document_id,
            filename="guide.pdf",
            status=DocumentStatus.ready,
            size_bytes=10,
            uploaded_at=utc_now(),
        )
    )


def test_search_child_chunks_validates_and_returns_auditable_evidence(settings):
    document_store = DocumentStore(settings.data_dir)
    document_id, parent_id, child_id = uuid4(), uuid4(), uuid4()
    _ready_document(document_store, document_id)
    result = RetrievalResult(
        child_id=child_id,
        parent_id=parent_id,
        document_id=document_id,
        filename="guide.pdf",
        score=0.9,
        content_preview="系统先检查输入电压。",
        text="系统先检查输入电压。",
        retrieval_mode="hybrid",
    )
    retriever = FakeRetriever([result])
    search_tool, _parent_tool = create_rag_tools(retriever, document_store, settings)

    response = search_tool.invoke({"query": "输入电压", "limit": 3})

    assert response["tool"] == "search_child_chunks"
    assert response["results"][0]["child_id"] == str(child_id)
    assert retriever.calls == [("输入电压", 3, settings.retrieval_min_score)]


def test_tools_reject_unready_index_and_read_parent_without_pdf(settings):
    document_store = DocumentStore(settings.data_dir)
    retriever = FakeRetriever([], ready=False)
    search_tool, parent_tool = create_rag_tools(retriever, document_store, settings)

    with pytest.raises(ValueError, match="INDEX_NOT_READY"):
        search_tool.invoke({"query": "问题", "limit": 3})
    with pytest.raises(ValueError, match="INVALID_QUERY"):
        search_tool.invoke({"query": "", "limit": 3})

    document_id, parent_id = uuid4(), uuid4()
    _ready_document(document_store, document_id)
    document_store.replace_chunks(
        document_id,
        [ParentContextUnit(parent_id=parent_id, document_id=document_id, text="父级上下文", char_count=5, ordinal=0)],
        [],
    )
    response = parent_tool.invoke({"parent_id": str(parent_id)})
    assert response["tool"] == "retrieve_parent_chunks"
    assert response["content"] == "父级上下文"


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
