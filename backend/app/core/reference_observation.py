"""Passive request observations. Nothing here authorizes a model or tool action."""
from collections import Counter
import json
import re
from threading import Lock
import time

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.config import get_stream_writer

from ..rag.tools import estimate_context_tokens


NODES = {'select_tool', 'summarize_history', 'answer_direct', 'rewrite_query', 'agent', 'orchestrator', 'tools',
         'should_compress_context', 'compress_context', 'fallback_response',
         'collect_answer', 'aggregate_answers'}


def tool_scope(namespace):
    """A tool-call ID belongs to its Send branch, not to the whole request."""
    parts = namespace.split('|') if isinstance(namespace, str) else namespace
    return next((part for part in (parts or ()) if part.startswith('agent:')), '')


def visible_text(text):
    """Remove private think blocks, including incomplete blocks in a cumulative stream."""
    text = re.sub(r'<think>.*?</think>\s*', '', str(text), flags=re.I | re.S)
    if re.search(r'<think>', text, flags=re.I):
        text = re.split(r'<think>', text, flags=re.I)[0]
    # Hold back a partial opening tag until its identity is known.
    text = re.sub(r'<(?:t(?:h(?:i(?:n(?:k)?)?)?)?)?$', '', text, flags=re.I)
    return text


class RequestObservation(BaseCallbackHandler):
    def __init__(self, settings):
        self.settings = settings
        self.started = time.perf_counter()
        self.models = {}
        self.chains = {}
        self.tools = {}
        self.model_trace = []
        self.tool_trace = []
        self.records = []
        # A callback and a streamed state update can expose the same ToolMessage
        # more than once.  Include its artifact in the identity: a later real
        # execution may legitimately reuse the provider's tool-call ID.
        self._seen = set()
        self._lock = Lock()

    def emit(self, event, node, **details):
        payload = {'event': event, 'node': node, 'details': details,
                   'loop_protocol_version': 'reference.v1', 'replayed': False}
        try:
            get_stream_writer()(payload)
        except RuntimeError:
            # Callbacks outside a graph have no public stream.
            pass

    def on_chain_start(self, serialized, inputs, *, run_id, metadata=None, **kwargs):
        node = (metadata or {}).get('langgraph_node')
        if node in NODES and kwargs.get('name') == node:
            self.chains[run_id] = (node, time.perf_counter())
            self.emit('node', node, status='started')

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        item = self.chains.pop(run_id, None)
        if item:
            self.emit('node', item[0], status='completed', duration_ms=int((time.perf_counter() - item[1]) * 1000))

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        node = (metadata or {}).get('langgraph_node', 'model')
        self.models[run_id] = (node, time.perf_counter(), messages[0])
        self.emit('model_start', node, model_call_id=str(run_id))

    def on_llm_end(self, response, *, run_id, **kwargs):
        item = self.models.pop(run_id, None)
        if item is None:
            return
        node, started, messages = item
        message = response.generations[0][0].message
        usage = getattr(message, 'usage_metadata', None) or {}
        if not usage and response.llm_output:
            reported = response.llm_output.get('token_usage') or {}
            usage = {'input_tokens': reported.get('prompt_tokens'), 'output_tokens': reported.get('completion_tokens')}
        measured = usage.get('input_tokens') is not None and usage.get('output_tokens') is not None
        output = str(message.content or '')
        if getattr(message, 'tool_calls', None):
            output += json.dumps(message.tool_calls, ensure_ascii=False)
        record = {'node': node, 'model_call_id': str(run_id),
            'input_tokens': usage.get('input_tokens') if measured else estimate_context_tokens(messages),
            'output_tokens': usage.get('output_tokens') if measured else estimate_context_tokens([HumanMessage(content=output)]),
            'usage_source': 'provider' if measured else 'estimate',
            'duration_ms': int((time.perf_counter() - started) * 1000)}
        self.model_trace.append(record)
        self.emit('model_call', node, **{key: value for key, value in record.items() if key != 'node'})

    def on_llm_error(self, error, *, run_id, **kwargs):
        item = self.models.pop(run_id, None)
        if item:
            record = {'node': item[0], 'model_call_id': str(run_id), 'input_tokens': 0, 'output_tokens': 0,
                      'usage_source': 'estimate', 'error_type': type(error).__name__,
                      'duration_ms': int((time.perf_counter() - item[1]) * 1000)}
            self.model_trace.append(record)
            self.emit('model_call', item[0], **{key: value for key, value in record.items() if key != 'node'})

    def on_tool_start(self, serialized, input_str, *, run_id, metadata=None, **kwargs):
        name = (serialized or {}).get('name', 'tool')
        scope = tool_scope((metadata or {}).get('langgraph_checkpoint_ns', ''))
        self.tools[run_id] = (name, time.perf_counter(), scope)
        self.emit('tool_start', 'tools', tool=name, tool_run_id=str(run_id))

    def register_message(self, message, namespace=()):
        if not isinstance(message, ToolMessage) or not isinstance(message.artifact, dict):
            return
        with self._lock:
            artifact_key = json.dumps(message.artifact, ensure_ascii=False, sort_keys=True, default=str)
            identity = (tool_scope(namespace), message.tool_call_id, artifact_key)
            if identity in self._seen:
                return
            self._seen.add(identity)
            artifact = message.artifact
            self.tool_trace.append({'tool_call_id': message.tool_call_id, **artifact})
            self.records.extend(artifact.get('results', []))
            if artifact.get('parent'):
                self.records.append(artifact['parent'])

    def on_tool_end(self, output, *, run_id, **kwargs):
        item = self.tools.pop(run_id, ('tool', time.perf_counter(), ''))
        self.register_message(output, item[2])
        self.emit('tool_call', 'tools', tool=item[0], tool_run_id=str(run_id),
                  tool_call_id=getattr(output, 'tool_call_id', None),
                  duration_ms=int((time.perf_counter() - item[1]) * 1000))

    def usage(self):
        kinds = {row['usage_source'] for row in self.model_trace}
        prompt = sum(row['input_tokens'] for row in self.model_trace)
        completion = sum(row['output_tokens'] for row in self.model_trace)
        return {'prompt_tokens': prompt, 'completion_tokens': completion, 'total_tokens': prompt + completion,
                'usage_source': next(iter(kinds)) if len(kinds) == 1 else 'mixed' if kinds else 'estimate',
                'model_calls': len(self.model_trace), 'model_call_limit': None,
                'calls_by_node': dict(Counter(row['node'] for row in self.model_trace)),
                'cache_hits': {}, 'cache_hit_count': 0, 'budget_exceeded': False,
                'model_duration_ms': sum(row['duration_ms'] for row in self.model_trace),
                'duration_ms': int((time.perf_counter() - self.started) * 1000),
                'cloud_calls': len(self.model_trace) if self.settings.llm_provider == 'openai_compatible' else 0}
