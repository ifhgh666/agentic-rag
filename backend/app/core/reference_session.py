"""Request actions and thread exclusion around the single reference graph checkpoint."""
from contextlib import contextmanager
from threading import Lock

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from .reference_model import create_reference_model
from ..rag.graph import create_agent_graph
from ..rag.graph_state import GRAPH_RECURSION_LIMIT
from ..rag.tools import create_rag_tools


class AgentGraphService:
    def __init__(self, settings, retriever, document_store, model=None):
        self.settings = settings
        self.retriever = retriever
        self.document_store = document_store
        self.model = model or create_reference_model(settings)
        self.tools = create_rag_tools(retriever, document_store, settings)
        self.main_graph = create_agent_graph(self.model, self.tools)
        self._lock = Lock()
        self._active = set()

    def config(self, thread_id, callbacks=None):
        return {'configurable': {'thread_id': thread_id}, 'recursion_limit': GRAPH_RECURSION_LIMIT,
                'callbacks': callbacks or []}

    def get_state(self, thread_id):
        return self.main_graph.get_state(self.config(thread_id))

    @contextmanager
    def request(self, thread_id):
        with self._lock:
            if thread_id in self._active:
                raise RuntimeError('THREAD_BUSY')
            self._active.add(thread_id)
        try:
            yield
        finally:
            with self._lock:
                self._active.discard(thread_id)

    def _clear_pending(self, config, snapshot):
        values = snapshot.values
        if not snapshot.next:
            return
        messages = values.get('messages', [])
        pending = values.get('pendingQuery', '')
        # The first clarification anchors this unfinished turn. Supplements may
        # repeat the original text, including a failed, still-unnamed supplement.
        clarification = next((index for index, message in enumerate(messages)
                              if isinstance(message, AIMessage) and message.name == 'clarification'), len(messages))
        start = next((index for index in range(clarification - 1, -1, -1)
                      if isinstance(messages[index], HumanMessage) and str(messages[index].content).strip() == pending), len(messages))
        removals = [RemoveMessage(id=message.id) for message in messages[start:] if message.id]
        self.main_graph.update_state(config, {'messages': removals, 'pendingQuery': '',
            'pendingClarifications': [], 'rewrittenQuestions': [], 'questionIsClear': True,
            'originalQuery': '', 'agent_answers': [{'__reset__': True}]}, as_node='aggregate_answers')

    @staticmethod
    def _is_clarification(snapshot):
        # A provider failure while processing a supplement leaves the pending
        # query intact but may checkpoint at rewrite_query.  It is still a
        # resumable clarification; a failed ordinary turn has no pendingQuery.
        return bool(snapshot.values.get('pendingQuery')) and bool(snapshot.next)

    def _clear_interrupted(self, config, snapshot):
        """Discard a failed graph continuation without treating it as clarification."""
        if not snapshot.next or self._is_clarification(snapshot):
            return
        messages = snapshot.values.get('messages', [])
        start = next((index for index in range(len(messages) - 1, -1, -1)
                      if isinstance(messages[index], HumanMessage) and not getattr(messages[index], 'name', None)),
                     len(messages))
        removals = [RemoveMessage(id=message.id) for message in messages[start:] if message.id]
        self.main_graph.update_state(config, {'messages': removals, 'pendingQuery': '',
            'pendingClarifications': [], 'rewrittenQuestions': [], 'questionIsClear': True,
            'originalQuery': '', 'agent_answers': [{'__reset__': True}]}, as_node='aggregate_answers')

    def stream_run(self, question, request_id, thread_id, action='auto', callbacks=None):
        with self.request(thread_id):
            config = self.config(thread_id, callbacks)
            snapshot = self.main_graph.get_state(config)
            pending = self._is_clarification(snapshot)
            if snapshot.next and not pending:
                self._clear_interrupted(config, snapshot)
                snapshot = self.main_graph.get_state(config)
            if action == 'cancel' and not snapshot.values:
                raise RuntimeError('THREAD_NOT_FOUND')
            if action == 'continue_clarification' and not pending:
                raise ValueError('NO_PENDING_QUERY')
            if action in {'new_question', 'cancel'}:
                self._clear_pending(config, snapshot)
                pending = False
                yield {'kind': 'pending_cleared', 'data': {}}
                if action == 'cancel':
                    yield {'kind': 'final', 'data': {'state': self.get_state(thread_id).values,
                                                   'pending': False, 'cancelled': True}}
                    return
            yield {'kind': 'started', 'data': {'continued': pending}}
            if pending:
                self.main_graph.update_state(config, {'messages': [HumanMessage(content=question.strip())]})
                stream_input = None
            else:
                stream_input = {'messages': [HumanMessage(content=question.strip())]}
            try:
                for namespace, mode, data in self.main_graph.stream(
                        stream_input, config, stream_mode=['messages', 'updates', 'custom'], subgraphs=True):
                    yield {'kind': mode, 'namespace': namespace, 'data': data}
            except Exception:
                # A model/provider failure can leave a resumable LangGraph
                # checkpoint.  It is an interrupted run, not a clarification.
                self._clear_interrupted(config, self.main_graph.get_state(config))
                raise
            snapshot = self.main_graph.get_state(config)
            yield {'kind': 'final', 'data': {'state': snapshot.values, 'pending': bool(snapshot.next),
                                           'continued': pending}}
