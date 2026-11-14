from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event

from langchain_core.messages import AIMessage

from tests.fakes.reference_api import install_model, send, last
from tests.fakes.reference_model import basic_resolver


def test_current_stream_has_cumulative_final_answers_sources_and_observational_usage(client, auth_headers):
    graph, model, record = install_model(client)
    stream = send(client, auth_headers)
    assert last(stream, 'complete')['status'] == 'completed'
    answers = [payload for name, payload in stream if name == 'answer']
    assert len(answers) > 2
    assert all(answers[index + 1]['answer'].startswith(answers[index]['answer']) for index in range(len(answers) - 1))
    assert answers[-1]['answer'] == 'Final answer: 230 V.\nSources:\n- guide.pdf'
    assert answers[-1]['sources'][0]['document_id'] == str(record.document_id)
    assert answers[-1]['sources'][0]['page_start'] == 2
    usage = last(stream, 'usage')
    assert usage['model_calls'] == 4 and usage['model_call_limit'] is None
    assert usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
    assert usage['calls_by_node'] == {'rewrite_query': 1, 'orchestrator': 2, 'aggregate_answers': 1}
    assert not {'verification', 'evaluation', 'answer_evaluation'}.intersection(name for name, _ in stream)
    observed = [data for _, data in stream if 'loop_protocol_version' in data]
    assert observed and all(data['loop_protocol_version'] == 'reference.v1' and data['replayed'] is False for data in observed)
    assert graph.get_state('reference').values['agent_answers']


def test_actual_graph_progress_arrives_before_blocked_final_generation_finishes(client):
    entered, release, completed = Event(), Event(), Event()
    received = []
    def respond(messages, kwargs, index):
        if 'final-answer synthesizer' in str(messages[0].content):
            entered.set()
            assert release.wait(5)
        return basic_resolver(messages, kwargs, index)
    install_model(client, respond)
    def consume():
        try:
            for item in client.app.state.services.pipeline.run('Question', thread_id='gated'):
                received.append(item)
        finally:
            completed.set()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(consume)
        try:
            assert entered.wait(3)
            assert not completed.is_set()
            assert any(item['event'] == 'model_call' and item['data']['node'] == 'rewrite_query' for item in received)
            assert not any(item['event'] == 'complete' for item in received)
            assert all(not item['data'].get('replayed') for item in received)
        finally:
            release.set()
        future.result(timeout=5)


def test_unknown_model_source_is_not_promoted_to_a_real_document(client, auth_headers):
    def respond(messages, kwargs, index):
        if 'final-answer synthesizer' in str(messages[0].content):
            return AIMessage(content='Answer.\nSources:\n- invented.pdf')
        return basic_resolver(messages, kwargs, index)
    install_model(client, respond)
    assert last(send(client, auth_headers), 'answer')['sources'] == []


def test_private_reasoning_and_provider_error_bodies_never_reach_public_stream(client, auth_headers):
    secret = 'PRIVATE_REASONING_SENTINEL'
    def respond(messages, kwargs, index):
        if 'final-answer synthesizer' in str(messages[0].content):
            return AIMessage(content='<think>' + secret + '</think>Public answer.\nSources:\n- guide.pdf')
        return basic_resolver(messages, kwargs, index)
    install_model(client, respond)
    stream = send(client, auth_headers)
    assert secret not in json.dumps(stream)
    assert last(stream, 'answer')['answer'].startswith('Public answer.')
    def failing(messages, kwargs, index):
        raise RuntimeError('api_key=sk-private-provider-endpoint')
    install_model(client, failing)
    stream = send(client, auth_headers, thread='error')
    assert last(stream, 'complete')['status'] == 'failed'
    assert 'sk-private' not in json.dumps(stream)
