from uuid import uuid4
from threading import Event
import pytest

from langchain_core.messages import ToolMessage

from app.core.reference_observation import RequestObservation
from tests.fakes.reference_api import install_model, send, last
from tests.fakes.reference_model import basic_resolver
from langchain_core.messages import AIMessage


def test_reused_tool_ids_in_independent_branches_keep_both_artifacts(settings):
    observer = RequestObservation(settings)
    for branch in ['one', 'two']:
        run_id = uuid4()
        observer.on_tool_start({'name': 'search_child_chunks'}, '{}', run_id=run_id,
            metadata={'langgraph_checkpoint_ns': f'agent:{branch}|tools:step'})
        message = ToolMessage(content='evidence', tool_call_id='same-id',
            artifact={'tool': 'search_child_chunks', 'results': [{'document_id': branch}]})
        observer.on_tool_end(message, run_id=run_id)
    assert [row['document_id'] for row in observer.records] == ['one', 'two']


def test_actual_request_logs_link_model_and_tool_events(client, auth_headers):
    install_model(client)
    stream = send(client, auth_headers)
    request_id = last(stream, 'complete')['request_id']
    logs = client.get('/api/logs', headers=auth_headers, params={'request_id': request_id}).json()['items']
    model_events = [row for row in logs if row.get('event') == 'model_call']
    assert len(model_events) == 4
    assert {row['node'] for row in model_events} == {'rewrite_query', 'orchestrator', 'aggregate_answers'}
    assert all(row['details']['model_call_id'] and row['thread_id'] == 'reference' for row in model_events)
    assert any(row.get('event') == 'tool_call' and row['details']['tool_call_id'] == 'search' for row in logs)


def test_empty_search_is_observable_without_forcing_an_answer_guard(client, auth_headers):
    install_model(client)
    client.app.state.services.retriever.search_with_cache = lambda *args, **kwargs: ([], False)
    stream = send(client, auth_headers)
    assert last(stream, 'retrieval')['results'] == []
    assert last(stream, 'complete')['status'] == 'completed'
    assert last(stream, 'answer')['sources'] == []


def test_parent_original_text_is_delivered_from_the_actual_tool_artifact(client, auth_headers):
    full_text = '  Start of chapter.\n' + 'Full context. ' * 1000 + '\nEnd of chapter.  '
    parent_id = None
    def respond(messages, kwargs, index):
        if 'document-grounded research assistant' in str(messages[0].content):
            if any('COMPRESSED CONTEXT FROM PRIOR RESEARCH' in str(message.content) for message in messages):
                return AIMessage(content='The chapter gives the answer.\nSources:\n- guide.pdf')
            if not any(message.type == 'tool' for message in messages):
                return AIMessage(content='', tool_calls=[{'name': 'retrieve_parent_chunks', 'id': 'parent',
                    'args': {'parent_id': parent_id}}])
        return basic_resolver(messages, kwargs, index)
    _, _, record = install_model(client, respond, text=full_text)
    parent_id = str(record.parent_id)
    stream = send(client, auth_headers)
    artifact = last(stream, 'tool_result')
    assert artifact['tool'] == 'retrieve_parent_chunks' and artifact['tool_call_id'] == 'parent'
    assert artifact['parent']['text'] == full_text
    assert artifact['parent']['document_id'] == str(record.document_id)
    assert artifact['parent']['page_start'] == 2
    assert last(stream, 'answer')['sources'][0]['document_id'] == str(record.document_id)


def test_native_parallel_branches_keep_both_sources_despite_reused_tool_ids(client, auth_headers):
    def respond(messages, kwargs, index):
        system = str(messages[0].content)
        if 'query rewriting specialist' in system:
            return AIMessage(content='', tool_calls=[{'name': 'QueryAnalysis', 'id': 'analysis', 'args': {
                'is_clear': True, 'questions': ['one', 'two'], 'clarification_needed': ''}}])
        if 'document-grounded research assistant' in system and not any(message.type == 'tool' for message in messages):
            question = next(message.content for message in messages if message.name == 'agent_question')
            return AIMessage(content='', tool_calls=[{'name': 'search_child_chunks', 'id': 'reused-id', 'args': {'query': question}}])
        if 'final-answer synthesizer' in system:
            return AIMessage(content='Combined answer.\nSources:\n- one.pdf\n- two.pdf')
        return basic_resolver(messages, kwargs, index)
    _, _, first = install_model(client, respond, filename='one.pdf')
    _, _, second = install_model(client, respond, filename='two.pdf')
    # Retriever.search forwards top_k/min_score positionally; keep this fake
    # compatible with that public call shape while selecting by branch query.
    client.app.state.services.retriever.search_with_cache = lambda query, *args, **kwargs: ([first if query == 'one' else second], False)
    stream = send(client, auth_headers)
    sources = last(stream, 'answer')['sources']
    assert {row['filename'] for row in sources} == {'one.pdf', 'two.pdf'}
    assert {row['filename'] for row in last(stream, 'retrieval')['results']} == {'one.pdf', 'two.pdf'}
    assert len([data for name, data in stream if name == 'tool_call']) == 2
    assert last(stream, 'usage')['model_calls'] == 6


def test_api_does_not_apply_old_request_or_per_model_deadlines(client, auth_headers):
    def slow(messages, kwargs, index):
        Event().wait(.02)
        return basic_resolver(messages, kwargs, index)
    graph, _, _ = install_model(client, slow)
    graph.settings.request_timeout_seconds = .001
    graph.settings.llm_timeout_seconds = .001
    graph.settings.max_simple_llm_calls = 0
    graph.settings.llm_max_output_tokens = 1
    stream = send(client, auth_headers)
    assert last(stream, 'complete')['status'] == 'completed'
    assert last(stream, 'usage')['model_calls'] == 4
    assert last(stream, 'usage')['duration_ms'] > 1
    assert len(last(stream, 'answer')['answer']) > 1


@pytest.mark.parametrize('reuse_id', [False, True])
def test_reused_tool_id_in_later_iteration_keeps_each_real_result_once(client, auth_headers, reuse_id):
    def respond(messages, kwargs, index):
        system = str(messages[0].content)
        if 'document-grounded research assistant' in system:
            count = sum(message.type == 'tool' for message in messages)
            if count < 2:
                return AIMessage(content='', tool_calls=[{'name': 'search_child_chunks', 'id': 'call_0' if reuse_id else f'call_{count}',
                    'args': {'query': ['one', 'two'][count]}}])
        if 'final-answer synthesizer' in system:
            return AIMessage(content='Combined answer.\nSources:\n- one.pdf\n- two.pdf')
        return basic_resolver(messages, kwargs, index)
    _, _, first = install_model(client, respond, filename='one.pdf')
    _, _, second = install_model(client, respond, filename='two.pdf')
    client.app.state.services.retriever.search_with_cache = lambda query, *args, **kwargs: (
        [first if query == 'one' else second], False)
    stream = send(client, auth_headers)
    assert last(stream, 'complete')['status'] == 'completed'
    assert {row['filename'] for row in last(stream, 'answer')['sources']} == {'one.pdf', 'two.pdf'}
    assert {row['filename'] for row in last(stream, 'retrieval')['results']} == {'one.pdf', 'two.pdf'}
    assert len([data for name, data in stream if name == 'tool_call']) == 2
    assert len([data for name, data in stream if name == 'retrieval']) >= 2
