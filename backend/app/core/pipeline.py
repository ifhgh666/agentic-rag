"""Public event adapter for the native reference graph."""
import re
from uuid import uuid4

from langchain_core.messages import AIMessageChunk, ToolMessage

from .reference_observation import RequestObservation, visible_text


_PUBLIC_OBSERVATION_FIELDS = {'status', 'duration_ms', 'model_call_id', 'input_tokens', 'output_tokens',
    'usage_source', 'error_type', 'tool', 'tool_run_id', 'tool_call_id'}


def _public_failure(exc):
    code = str(exc)
    messages = {
        'THREAD_BUSY': '这个会话正在处理上一条消息，请完成后再提交。',
        'THREAD_NOT_FOUND': '该会话已失效，请重新提问。',
        'NO_PENDING_QUERY': '当前没有待补充的问题，请直接开始新问题。',
        'MODEL_NOT_CONFIGURED': '模型接口尚未配置。',
        'LOCAL_MODEL_NOT_CONFIGURED': '本地模型尚未配置。',
    }
    if code in messages:
        return code, messages[code]
    return 'RAG_PIPELINE_FAILED', '问答处理失败，请查看服务端日志。'


def _matching_sources(answer, records):
    match = re.search(r'(?m)^Sources:\s*\n((?:[ \t]*-[^\n]*(?:\n|$))*)', answer)
    names = {line.strip()[1:].strip() for line in match.group(1).splitlines() if line.strip().startswith('-')} if match else set()
    found = {}
    for record in records:
        if record.get('filename') not in names:
            continue
        source = {key: record.get(key) for key in ('document_id', 'filename', 'section_title', 'page_start', 'page_end')}
        source['section_title'] = source['section_title'] or ''
        found.setdefault((source['document_id'], source['section_title'], source['page_start']), source)
    return list(found.values())


class RagPipeline:
    def __init__(self, graph_service, logger, diagnostics=None):
        self.graph_service = graph_service
        self.retriever = graph_service.retriever
        self.logger = logger
        self.diagnostics = diagnostics

    def run(self, question, request_id=None, thread_id=None, action='auto'):
        request_id = str(request_id or uuid4())
        thread_id = thread_id or f'thread-{uuid4()}'
        identity = {'request_id': request_id, 'thread_id': thread_id}
        observation = RequestObservation(self.graph_service.settings)
        sequence = 0
        accumulated = ''
        final = None
        continuing = False
        tools_sent = 0

        def event(name, data):
            return {'event': name, 'data': {**identity, **data}}

        def record_tool_results():
            nonlocal tools_sent
            fresh = observation.tool_trace[tools_sent:]
            tools_sent += len(fresh)
            if any(row.get('tool') == 'search_child_chunks' for row in fresh):
                children = {record['child_id']: record for record in observation.records if record.get('child_id')}
                yield event('retrieval', {'results': list(children.values())})
            for row in fresh:
                if row.get('tool') == 'retrieve_parent_chunks' and row.get('parent'):
                    yield event('tool_result', {'tool': row['tool'], 'tool_call_id': row['tool_call_id'],
                                              'parent': row['parent']})

        try:
            yield event('step', {'stage': 'query_receipt', 'status': 'completed', 'sequence': 1,
                                 'detail': {'question_length': len(question)}})
            for frame in self.graph_service.stream_run(question, request_id, thread_id, action, [observation]):
                kind, data = frame['kind'], frame['data']
                if kind == 'started':
                    continuing = data['continued']
                elif kind == 'pending_cleared':
                    yield event('clarification', {'schema_version': 1, 'pending': False, 'question': '', 'allowed_actions': []})
                elif kind == 'custom':
                    sequence += 1
                    details = {key: value for key, value in data.get('details', {}).items()
                               if key in _PUBLIC_OBSERVATION_FIELDS}
                    payload = {'node': data.get('node', ''), 'event': data.get('event', 'node'),
                               'details': details, 'event_sequence': sequence, 'replayed': False,
                               'loop_protocol_version': 'reference.v1'}
                    for key in ('tool', 'model_call_id', 'tool_call_id', 'duration_ms'):
                        if key in details:
                            payload[key] = details[key]
                    self.logger.log('INFO', 'rag.execution', '图执行事件', request_id,
                        thread_id=thread_id, node=payload['node'], event=payload['event'],
                        tool=payload.get('tool'), duration_ms=payload.get('duration_ms'),
                        details={**details, 'event_sequence': sequence, 'replayed': False,
                                 'loop_protocol_version': 'reference.v1'})
                    yield event(payload['event'], payload)
                    yield from record_tool_results()
                elif kind == 'messages':
                    chunk, metadata = data
                    if isinstance(chunk, ToolMessage):
                        observation.register_message(chunk, frame.get('namespace', ()))
                    if metadata.get('langgraph_node') == 'aggregate_answers' and isinstance(chunk, AIMessageChunk):
                        if isinstance(chunk.content, str):
                            accumulated += chunk.content
                            yield event('answer', {'answer': visible_text(accumulated), 'sources': []})
                elif kind == 'updates':
                    if '__interrupt__' in data:
                        continue
                    for node, update in data.items():
                        if not isinstance(update, dict):
                            continue
                        for message in update.get('messages', []):
                            observation.register_message(message, frame.get('namespace', ()))
                        if node == 'rewrite_query':
                            yield event('analysis', {'schema_version': 1, 'is_clear': bool(update.get('questionIsClear')),
                                'questions': update.get('rewrittenQuestions', []), 'source': 'model',
                                'relation': 'clarification' if continuing else 'new_question',
                                'relation_source': 'pending_state' if continuing and action == 'auto' else 'action',
                                'action': action, 'replayed': False,
                                'loop_protocol_version': 'reference.v1'})
                    yield from record_tool_results()
                elif kind == 'final':
                    final = data
            state = final['state']
            usage = observation.usage()
            if final.get('cancelled'):
                status, answer = 'cancelled', ''
            elif final['pending']:
                status = 'clarification'
                answer = str(state['messages'][-1].content)
                yield event('clarification', {'schema_version': 1, 'pending': True,
                            'question': visible_text(answer), 'allowed_actions': ['continue_clarification', 'new_question', 'cancel']})
            else:
                status = 'completed'
                answer = visible_text(state['messages'][-1].content)
                yield event('answer', {'answer': answer, 'sources': _matching_sources(answer, observation.records)})
            if self.diagnostics and self.graph_service.settings.execution_logging_enabled:
                try:
                    receipt = self.diagnostics.submit({'request_id': request_id, 'thread_id': thread_id,
                        'original_question': question, 'model_trace': observation.model_trace,
                        'execution_trace': observation.tool_trace, 'retrieval_batches': [],
                        'evidence_registry': observation.records, 'status': status, 'stop_reason': '', 'usage': usage})
                    receipt_details = {'diagnostic_id': receipt.job_id, 'diagnostic_status': receipt.status,
                                       'reason': receipt.reason}
                except Exception:
                    receipt_details = {'diagnostic_status': 'failed', 'reason': 'submit_failed'}
                yield event('node', {'node': 'diagnostics', 'event': 'node', 'details': receipt_details,
                                    'replayed': False, 'loop_protocol_version': 'reference.v1'})
            self.logger.log('INFO', 'rag.usage', '模型用量统计', request_id,
                            thread_id=thread_id, duration_ms=usage['duration_ms'], details=usage)
            yield event('usage', usage)
            yield event('complete', {'status': status, 'reason': '', 'stop_origin': 'model' if status == 'completed' else 'action'})
        except Exception as exc:
            code, message = _public_failure(exc)
            self.logger.log('ERROR', 'rag.pipeline', message, request_id, thread_id=thread_id,
                            details={'code': code, 'exception_type': type(exc).__name__})
            yield event('error', {'code': code, 'message': message})
            yield event('usage', observation.usage())
            yield event('complete', {'status': 'failed', 'reason': code})
