"""Native graph test fixtures; never adapt the removed governed loop."""
from types import SimpleNamespace
from uuid import uuid4
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.core.reference_session import AgentGraphService
from app.knowledge.stores import DocumentStore
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit
from tests.fakes.reference_model import ScriptedReferenceModel, basic_resolver

def analysis_reply(questions=(), clarification="Please specify the equipment model."):
    return AIMessage(content="", tool_calls=[{"name": "QueryAnalysis", "id": str(uuid4()),
        "args": {"is_clear": bool(questions), "questions": list(questions),
                 "clarification_needed": "" if questions else clarification}}])

def tool_reply(*calls):
    return AIMessage(content="", tool_calls=[{"name": n, "args": a, "id": str(uuid4())} for n, a in calls])

def branch_question(messages):
    return next((str(m.content) for m in messages if getattr(m, "name", None) == "agent_question"), "")

def resolver_for(*, questions=None, research=None, aggregate=None, rewrite=None):
    def respond(messages, kwargs, index):
        system = str(messages[0].content)
        if "query rewriting specialist" in system:
            if rewrite is not None:
                return rewrite(messages, kwargs, index)
            if questions is not None:
                return analysis_reply(questions)
        if "document-grounded research assistant" in system and research is not None:
            return research(messages, kwargs, index)
        if "final-answer synthesizer" in system and aggregate is not None:
            return AIMessage(content=aggregate) if isinstance(aggregate, str) else aggregate(messages, kwargs, index)
        return basic_resolver(messages, kwargs, index)
    return respond

class ReferenceRetriever:
    def __init__(self, results=(), ready=True, answers=None):
        self.results, self.answers, self.calls = list(results), answers, []
        self.index_store = SimpleNamespace(ready=ready)
    def search(self, query, *, top_k=7, min_score=0):
        self.calls.append((query, top_k, min_score))
        value = self.answers(query) if self.answers else self.results
        if isinstance(value, Exception):
            raise value
        return list(value)[:top_k]

def make_service(settings, texts=("voltage is 230 V.",), *, resolver=None, ready=True, answers=None):
    store, results = DocumentStore(settings.data_dir), []
    for index, text in enumerate(texts):
        did, pid = uuid4(), uuid4()
        filename = f"guide{index or ''}.pdf"
        store.save_document(KnowledgeDocument(document_id=did, filename=filename,
            status=DocumentStatus.ready, size_bytes=1, uploaded_at=utc_now()))
        store.replace_chunks(did, [ParentContextUnit(parent_id=pid, document_id=did, section_title="Voltage",
            text=text, char_count=len(text), ordinal=index, page_start=1, page_end=2)], [])
        results.append(RetrievalResult(child_id=uuid4(), parent_id=pid, document_id=did,
            filename=filename, score=.9, content_preview=text[:240], text=text,
            retrieval_mode="hybrid", section_title="Voltage", page_start=1, page_end=2))
    retriever = ReferenceRetriever(results, ready, answers)
    model = ScriptedReferenceModel(resolver=resolver or basic_resolver)
    return AgentGraphService(settings, retriever, store, model=model), model, results

def run_turn(service, question="What voltage?", *, thread="test", action="auto", callbacks=None):
    frames = list(service.stream_run(question, str(uuid4()), thread, action, callbacks))
    assert frames[-1]["kind"] == "final"
    return frames[-1]["data"], frames

def research_calls(model):
    return [c for c in model.calls if "document-grounded research assistant" in str(c["messages"][0].content)]

def tool_messages(model):
    return [m for c in research_calls(model) for m in c["messages"] if isinstance(m, ToolMessage)]

def conversation(service, thread="test"):
    return [m for m in service.get_state(thread).values.get("messages", [])
            if isinstance(m, (HumanMessage, AIMessage)) and not getattr(m, "name", None)]
