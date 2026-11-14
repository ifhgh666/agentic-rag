from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event

from langchain_core.messages import AIMessage

from tests.fakes.reference_api import install_model, send, last
from tests.fakes.reference_model import basic_resolver, routing_reply


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
    assert usage['model_calls'] == 5 and usage['model_call_limit'] is None
    assert usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
    assert usage['calls_by_node'] == {'select_tool': 1, 'rewrite_query': 1, 'orchestrator': 2, 'aggregate_answers': 1}
    assert [data['node'] for name, data in stream if name == 'model_call'][:2] == ['select_tool', 'rewrite_query']
    assert not {'verification', 'evaluation', 'answer_evaluation'}.intersection(name for name, _ in stream)
    observed = [data for _, data in stream if 'loop_protocol_version' in data]
    assert observed and all(data['loop_protocol_version'] == 'reference.v1' and data['replayed'] is False for data in observed)
    assert graph.get_state('reference').values['agent_answers']


def test_greeting_streams_direct_answer_without_ready_index_or_retrieval(client, auth_headers):
    reply = '你好！今天有什么我可以帮你的吗？'

    def respond(messages, kwargs, index):
        if 'classify whether the latest user request' in str(messages[0].content):
            assert '你好' in messages[-1].content
            return routing_reply(False)
        assert '文脉 · PDF 知识工作台' in messages[0].content
        assert not kwargs.get('tools')
        if messages[-1].content != '你好':
            assert any(message.type == 'ai' and message.content == reply for message in messages)
        return AIMessage(content=reply)

    graph, _, _ = install_model(client, respond)
    graph.retriever.index_store.ready = False

    def unexpected_search(*args, **kwargs):
        raise AssertionError('Direct replies must not access the knowledge base')

    graph.retriever.search_with_cache = unexpected_search
    for question in ('你好', '你刚才说了什么？'):
        stream = send(client, auth_headers, question)
        assert last(stream, 'complete')['status'] == 'completed'
        answers = [data for name, data in stream if name == 'answer']
        assert len(answers) > 2
        assert all(reply.startswith(data['answer']) and not data['sources'] for data in answers)
        assert answers[-1]['answer'] == reply
        assert not {'analysis', 'clarification', 'tool_start', 'tool_call', 'retrieval'}.intersection(name for name, _ in stream)
        assert last(stream, 'usage')['calls_by_node'] == {'select_tool': 1, 'answer_direct': 1}
        assert not graph.get_state('reference').next


def test_invalid_tool_decision_fails_before_query_analysis(client, auth_headers):
    def invalid_decision(messages, kwargs, index):
        return AIMessage(content='', tool_calls=[{'name': 'ToolRouting', 'id': 'route',
            'args': {'needs_knowledge': 'false'}}])

    graph, model, _ = install_model(client, invalid_decision)
    stream = send(client, auth_headers, '你好')
    assert last(stream, 'complete')['status'] == 'failed'
    assert len(model.calls) == 1
    assert not {'analysis', 'clarification', 'tool_call', 'retrieval'}.intersection(name for name, _ in stream)
    assert not graph.get_state('reference').next


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
