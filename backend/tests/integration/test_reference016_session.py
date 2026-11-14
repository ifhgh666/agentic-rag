from langchain_core.messages import AIMessage
import pytest

from tests.fakes.reference_api import install_model, send, last
from tests.fakes.reference_model import basic_resolver, routing_reply
from tests.fakes.reference_helpers import make_service, run_turn, resolver_for, analysis_reply


def clarification_resolver(messages, kwargs, index):
    if 'query rewriting specialist' in str(messages[0].content):
        context = str(messages[-1].content)
        clear = 'User Clarifications:' in context
        return AIMessage(content='', tool_calls=[{'name': 'QueryAnalysis', 'id': 'clarity', 'args': {
            'is_clear': clear, 'questions': ['PX-200 voltage?'] if clear else [],
            'clarification_needed': '' if clear else '请说明具体设备型号。'}}])
    return basic_resolver(messages, kwargs, index)


@pytest.mark.parametrize('action', ['auto', 'continue_clarification'])
def test_pending_resumes_with_default_or_explicit_supplement(client, auth_headers, action):
    graph, model, _ = install_model(client, clarification_resolver)
    first = send(client, auth_headers, '它的电压是多少？', thread=action)
    assert last(first, 'complete')['status'] == 'clarification'
    assert last(first, 'clarification')['question'] == '请说明具体设备型号。'
    assert [data['node'] for name, data in first if name == 'model_call'] == ['select_tool', 'rewrite_query']
    assert not {'tool_call', 'retrieval'}.intersection(name for name, _ in first)
    assert graph.get_state(action).next == ('request_clarification',)
    second = send(client, auth_headers, '设备是PX-200', thread=action, action=action)
    assert last(second, 'complete')['status'] == 'completed'
    assert 'select_tool' not in last(second, 'usage')['calls_by_node']
    assert last(second, 'answer')['sources']
    assert not graph.get_state(action).next
    entry = [call for call in model.calls if 'query rewriting specialist' in str(call['messages'][0].content)]
    context = entry[-1]['messages'][-1].content
    assert '它的电压是多少？' in context and '设备是PX-200' in context
    assert graph.get_state(action).values['pendingQuery'] == ''


def test_cancel_clears_pending_without_model_calls_and_preserves_completed_history(client, auth_headers):
    graph, model, _ = install_model(client, clarification_resolver)
    send(client, auth_headers, '它的电压？')
    graph.main_graph.update_state(graph.config('reference'), {'conversation_summary': 'Keep this summary.'})
    count = len(model.calls)
    stream = send(client, auth_headers, '', action='cancel')
    assert last(stream, 'complete')['status'] == 'cancelled'
    assert len(model.calls) == count
    state = graph.get_state('reference')
    assert not state.next and not state.values['pendingQuery']
    assert state.values['conversation_summary'] == 'Keep this summary.'
    assert not any(getattr(m, 'content', '') == '它的电压？' for m in state.values['messages'])
    assert last(stream, 'clarification')['pending'] is False


def test_new_question_clears_pending_before_its_model_failure(client, auth_headers):
    graph, model, _ = install_model(client, clarification_resolver)
    send(client, auth_headers, '它的电压？')
    def failing(messages, kwargs, index):
        raise RuntimeError('private-service-error')
    model.resolver = failing
    stream = send(client, auth_headers, 'New standalone question', action='new_question')
    assert last(stream, 'complete')['status'] == 'failed'
    assert last(stream, 'clarification')['pending'] is False
    assert graph.get_state('reference').values['pendingQuery'] == ''


def test_explicit_new_question_can_reply_directly_after_clearing_pending(client, auth_headers):
    graph, model, _ = install_model(client, clarification_resolver)
    assert last(send(client, auth_headers, '它的电压？'), 'complete')['status'] == 'clarification'
    def respond(messages, kwargs, index):
        if 'classify whether the latest user request' in str(messages[0].content):
            assert '它的电压' not in messages[-1].content
            return routing_reply(False)
        return AIMessage(content='你好！')
    model.resolver = respond
    stream = send(client, auth_headers, '你好', action='new_question')
    assert last(stream, 'clarification')['pending'] is False
    assert last(stream, 'complete')['status'] == 'completed'
    assert last(stream, 'answer')['answer'] == '你好！'
    assert graph.get_state('reference').values['pendingQuery'] == ''


def test_same_thread_busy_other_threads_independent_and_invalid_actions_are_clear(client, auth_headers):
    graph, _, _ = install_model(client, clarification_resolver)
    with graph.request('busy'):
        stream = send(client, auth_headers, thread='busy')
    assert last(stream, 'error')['code'] == 'THREAD_BUSY'
    assert last(send(client, auth_headers, thread='different'), 'complete')['status'] == 'clarification'
    assert last(send(client, auth_headers, thread='no-pending', action='continue_clarification'), 'error')['code'] == 'NO_PENDING_QUERY'
    assert last(send(client, auth_headers, '', thread='absent', action='cancel'), 'error')['code'] == 'THREAD_NOT_FOUND'


@pytest.mark.parametrize('failed_node', ['routing', 'rewrite', 'research', 'aggregate'])
def test_failed_execution_is_not_a_pending_clarification(client, auth_headers, failed_node):
    markers = {'routing': 'classify whether the latest user request', 'rewrite': 'query rewriting specialist',
               'research': 'document-grounded research assistant',
               'aggregate': 'final-answer synthesizer'}
    def failing(messages, kwargs, index):
        if markers[failed_node] in str(messages[0].content):
            raise RuntimeError('isolated-model-failure')
        return basic_resolver(messages, kwargs, index)
    graph, model, _ = install_model(client, failing)
    first = send(client, auth_headers, 'First question')
    assert last(first, 'complete')['status'] == 'failed'
    if failed_node == 'routing':
        assert not {'analysis', 'clarification', 'tool_call', 'retrieval'}.intersection(name for name, _ in first)
    before = len(model.calls)
    rejected = send(client, auth_headers, 'Supplement', action='continue_clarification')
    assert last(rejected, 'error')['code'] == 'NO_PENDING_QUERY'
    assert len(model.calls) == before
    model.resolver = basic_resolver
    second = send(client, auth_headers, 'Second standalone question')
    assert last(second, 'complete')['status'] == 'completed'
    analysis = last(second, 'analysis')
    assert analysis['relation'] == 'new_question'
    assert analysis['questions'] == ['Second standalone question']
    if failed_node == 'routing':
        assert 'First question' not in model.calls[before]['messages'][-1].content
    assert not graph.get_state('reference').next


@pytest.mark.parametrize('action', ['cancel', 'new_question'])
@pytest.mark.parametrize('failed_repeat', [False, True])
def test_pending_clear_removes_the_whole_turn_when_supplement_repeats_original(settings, action, failed_repeat):
    service, model, _ = make_service(settings)
    run_turn(service, 'Completed question')
    completed_ids = [message.id for message in service.get_state('test').values['messages']]
    original = 'UNRESOLVED_REPEAT_SENTINEL'
    model.resolver = resolver_for(rewrite=lambda *_: analysis_reply())
    run_turn(service, original)
    run_turn(service, 'EARLIER_SUPPLEMENT_SENTINEL', action='auto')
    run_turn(service, original, action='auto')
    if failed_repeat:
        def failing(*_):
            raise TimeoutError('isolated supplement transport failure')
        model.resolver = failing
        with pytest.raises(TimeoutError):
            run_turn(service, original, action='auto')
    count = len(model.calls)
    model.resolver = basic_resolver
    final, _ = run_turn(service, '' if action == 'cancel' else 'New standalone question', action=action)
    assert not final['pending'] and final['state']['pendingQuery'] == ''
    assert all(original not in str(message.content) and 'EARLIER_SUPPLEMENT_SENTINEL' not in str(message.content)
               for message in final['state']['messages'])
    if action == 'cancel':
        assert len(model.calls) == count
        assert [message.id for message in final['state']['messages']] == completed_ids
    else:
        assert all(original not in str(message.content) and 'EARLIER_SUPPLEMENT_SENTINEL' not in str(message.content)
                   for call in model.calls[count:] for message in call['messages'])


def test_cancel_preserves_a_completed_question_with_the_same_text_as_pending(settings):
    service, model, _ = make_service(settings)
    original = 'Same question in a later turn'
    run_turn(service, original)
    completed_ids = [message.id for message in service.get_state('test').values['messages']]
    model.resolver = resolver_for(rewrite=lambda *_: analysis_reply())
    run_turn(service, original)
    run_turn(service, original, action='auto')
    final, _ = run_turn(service, '', action='cancel')
    assert not final['pending']
    assert [message.id for message in final['state']['messages']] == completed_ids
