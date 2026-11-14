from types import SimpleNamespace
import json

import httpx
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from openai import BadRequestError
import pytest

from app.core.reference_model import create_reference_model
from app.rag.nodes import answer_direct, rewrite_query, select_tool
from app.rag.schemas import QueryAnalysis, ToolRouting


@pytest.mark.parametrize('model_name', ['configured-model', 'deepseek-v4-pro', 'deepseek-reasoner'])
def test_compatible_sdk_uses_native_function_calls_without_product_limits(settings, monkeypatch, model_name):
    created, observed = {}, []
    class SDK:
        def with_structured_output(self, schema, **kwargs):
            observed.append((schema, kwargs))
            return 'native-parser'
        def bind_tools(self, tools):
            return ('native-tools', tools)
    sdk = SDK()
    def factory(**kwargs):
        created.update(kwargs)
        return sdk
    monkeypatch.setattr('langchain_openai.ChatOpenAI', factory)
    configured = settings.model_copy(update={'llm_provider': 'openai_compatible',
        'llm_base_url': 'https://example.invalid/v1', 'llm_api_key': 'test-only', 'llm_model': model_name,
        'llm_timeout_seconds': .001, 'llm_max_output_tokens': 1, 'max_context_tokens': 1})
    model = create_reference_model(configured)
    assert model.model is sdk
    assert created == {'model': model_name, 'base_url': 'https://example.invalid/v1', 'api_key': 'test-only',
        'temperature': settings.llm_temperature, 'seed': settings.llm_seed, 'max_retries': 0,
        'default_headers': {'Accept-Encoding': 'identity'}}
    assert model.with_structured_output(QueryAnalysis) == 'native-parser'
    assert model.with_structured_output(ToolRouting) == 'native-parser'
    assert observed == [(QueryAnalysis, {'method': 'function_calling'}),
                        (ToolRouting, {'method': 'function_calling'})]
    assert model.bind_tools(['actual tool']) == ('native-tools', ['actual tool'])


def test_local_sdk_does_not_inherit_legacy_output_or_context_caps(settings, monkeypatch):
    created = {}
    def factory(**kwargs):
        created.update(kwargs)
        return SimpleNamespace()
    monkeypatch.setattr('langchain_ollama.ChatOllama', factory)
    model = create_reference_model(settings.model_copy(update={'llm_provider': 'ollama',
        'ollama_model': 'configured-local', 'llm_timeout_seconds': .001, 'llm_max_output_tokens': 1}))
    assert model is not None
    assert created == {'model': 'configured-local', 'base_url': settings.ollama_base_url,
        'temperature': settings.llm_temperature, 'seed': settings.llm_seed, 'client_kwargs': {'trust_env': False}}


def test_deepseek_flash_native_sdk_keeps_non_thinking_mode_through_tool_round_trip(settings, monkeypatch):
    """Replay the real 400 condition at the HTTP boundary, after SDK serialization."""
    requests = []
    question = 'ZX-731 的巡检周期是多久？'

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if body.get('thinking') != {'type': 'disabled'}:
            return httpx.Response(400, json={'error': {
                'message': 'Thinking mode does not support this tool_choice',
                'type': 'invalid_request_error', 'code': 'invalid_request_error'}})
        choice = body.get('tool_choice')
        if isinstance(choice, dict) and choice.get('function', {}).get('name') == 'QueryAnalysis':
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{
                'id': 'analysis-1', 'type': 'function', 'function': {'name': 'QueryAnalysis',
                'arguments': json.dumps({'is_clear': True, 'questions': [question], 'clarification_needed': ''})}}]}
        elif body.get('tools') and body['messages'][-1]['role'] != 'tool':
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{
                'id': 'search-1', 'type': 'function', 'function': {'name': 'search_child_chunks',
                'arguments': json.dumps({'query': question})}}]}
        else:
            message = {'role': 'assistant', 'content': '72 小时'}
        return httpx.Response(200, json={'id': 'test-only', 'object': 'chat.completion',
            'created': 0, 'model': body['model'], 'choices': [{'index': 0, 'message': message,
            'finish_reason': 'tool_calls' if message.get('tool_calls') else 'stop'}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}})

    configured = settings.model_copy(update={'llm_provider': 'openai_compatible',
        'llm_model': 'deepseek-flash', 'llm_base_url': 'https://example.invalid/v1', 'llm_api_key': 'test-only'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr('langchain_openai.ChatOpenAI', lambda **kwargs: ChatOpenAI(**kwargs, http_client=client))
        model = create_reference_model(configured)
        analysis = rewrite_query({'messages': [HumanMessage(content=question)]}, model)
        assert analysis['questionIsClear'] and analysis['rewrittenQuestions'] == [question]
        tool_model = model.bind_tools([{'type': 'function', 'function': {'name': 'search_child_chunks',
            'description': 'Search test chunks.', 'parameters': {'type': 'object',
            'properties': {'query': {'type': 'string'}}, 'required': ['query']}}}])
        start = HumanMessage(content=question)
        call = tool_model.invoke([start])
        assert call.tool_calls[0]['name'] == 'search_child_chunks'
        reply = tool_model.invoke([start, call, ToolMessage(content='72 小时', tool_call_id='search-1')])
        assert reply.content == '72 小时'
        assert model.invoke([start]).content == '72 小时'
    assert len(requests) == 4
    assert all(body['thinking'] == {'type': 'disabled'} for body in requests)
    assert requests[0]['tool_choice'] == {'type': 'function', 'function': {'name': 'QueryAnalysis'}}
    assert requests[2]['messages'][-1]['tool_call_id'] == 'search-1'
    assert all(body['model'] == 'deepseek-flash' for body in requests)


def test_deepseek_flash_provider_failure_is_not_retried_or_replaced(settings, monkeypatch):
    requests = []

    def reject(request):
        requests.append(json.loads(request.content))
        return httpx.Response(400, json={'error': {'message': 'Invalid test request',
            'type': 'invalid_request_error', 'code': 'invalid_request_error'}})

    configured = settings.model_copy(update={'llm_provider': 'openai_compatible',
        'llm_model': 'deepseek-flash', 'llm_base_url': 'https://example.invalid/v1', 'llm_api_key': 'test-only'})
    with httpx.Client(transport=httpx.MockTransport(reject)) as client:
        monkeypatch.setattr('langchain_openai.ChatOpenAI', lambda **kwargs: ChatOpenAI(**kwargs, http_client=client))
        with pytest.raises(BadRequestError):
            rewrite_query({'messages': [HumanMessage(content='A test question')]}, create_reference_model(configured))
    assert len(requests) == 1


@pytest.mark.parametrize('question', ['你好', '你是谁', '你是什么模型'])
def test_deepseek_flash_sdk_routes_with_a_schema_and_answers_with_no_bound_tools(settings, monkeypatch, question):
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{
                'id': 'route-1', 'type': 'function', 'function': {'name': 'ToolRouting',
                'arguments': json.dumps({'needs_knowledge': False})}}]}
        else:
            message = {'role': 'assistant', 'content': '你好！'}
        return httpx.Response(200, json={'id': 'test-only', 'object': 'chat.completion',
            'created': 0, 'model': body['model'], 'choices': [{'index': 0, 'message': message,
            'finish_reason': 'tool_calls' if message.get('tool_calls') else 'stop'}]})

    configured = settings.model_copy(update={'llm_provider': 'openai_compatible',
        'llm_model': 'deepseek-flash', 'llm_base_url': 'https://example.invalid/v1', 'llm_api_key': 'test-only'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr('langchain_openai.ChatOpenAI', lambda **kwargs: ChatOpenAI(**kwargs, http_client=client))
        model = create_reference_model(configured)
        state = {'messages': [HumanMessage(content=question)]}
        assert select_tool(state, model) == {'needs_knowledge': False}
        assert answer_direct(state, model)['messages'][-1].content == '你好！'

    assert len(requests) == 2
    assert all(body['thinking'] == {'type': 'disabled'} for body in requests)
    assert requests[0]['tool_choice'] == {'type': 'function', 'function': {'name': 'ToolRouting'}}
    assert not requests[1].get('tools') and not requests[1].get('tool_choice')
    assert 'underlying model also take the direct path' in requests[0]['messages'][0]['content']
    system_message = requests[1]['messages'][0]
    assert system_message['role'] == 'system'
    assert '文脉 · PDF 知识工作台' in system_message['content']
    assert '“你是谁” or “你是什么模型”' in system_message['content']
    assert 'only when verified in the system context' in system_message['content']
    assert requests[1]['messages'][-1] == {'role': 'user', 'content': question}
