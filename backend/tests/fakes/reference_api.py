"""Isolated data/model helpers for current reference API contracts."""
import json
from types import SimpleNamespace
from uuid import uuid4

from app.core.reference_session import AgentGraphService
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit
from tests.fakes.reference_model import ScriptedReferenceModel, basic_resolver


def events(response):
    assert response.status_code == 200
    return [(block.splitlines()[0].removeprefix('event: '),
             json.loads(next(line[6:] for line in block.splitlines() if line.startswith('data: '))))
            for block in response.text.split('\n\n') if block.strip()]


def last(stream, name):
    return next(data for event, data in reversed(stream) if event == name)


def install_model(client, resolver=basic_resolver, text='voltage is 230 V.', filename='guide.pdf'):
    services = client.app.state.services
    document_id, parent_id, child_id = uuid4(), uuid4(), uuid4()
    services.documents.save_document(KnowledgeDocument(document_id=document_id, filename=filename,
        status=DocumentStatus.ready, size_bytes=10, uploaded_at=utc_now()))
    services.documents.replace_chunks(document_id, [ParentContextUnit(parent_id=parent_id,
        document_id=document_id, text=text, char_count=len(text), ordinal=0,
        section_title='Voltage', page_start=2, page_end=2)], [])
    result = RetrievalResult(child_id=child_id, parent_id=parent_id, document_id=document_id,
        filename=filename, section_title='Voltage', score=.9, content_preview=text[:240],
        text=text, page_start=2, page_end=2)
    services.retriever.index_store = SimpleNamespace(ready=True)
    services.retriever.search_with_cache = lambda *args, **kwargs: ([result], False)
    model = ScriptedReferenceModel(resolver=resolver)
    graph = AgentGraphService(services.settings, services.retriever, services.documents, model)
    services.pipeline.graph_service = graph
    services.pipeline.retriever = services.retriever
    return graph, model, result


def send(client, headers, question='What voltage?', thread='reference', action='auto'):
    return events(client.post('/api/chat/stream', headers=headers,
        json={'question': question, 'thread_id': thread, 'action': action}))
