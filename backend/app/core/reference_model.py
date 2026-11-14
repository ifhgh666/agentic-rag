"""Native LangChain models for the reference graph; legacy call governance is separate."""
import json
import re
from typing import Any
from urllib.parse import urlparse

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool


class FakeReferenceModel(BaseChatModel):
    """Explicit engineering model. Its replies never establish real QA quality."""
    @property
    def _llm_type(self):
        return 'fake-reference'

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(tool) for tool in tools])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        prompt = str(messages[0].content)
        if 'classify whether the latest user request requires the PDF knowledge base' in prompt:
            reply = AIMessage(content='', tool_calls=[{'name': 'ToolRouting', 'id': 'fake-route',
                'args': {'needs_knowledge': True}}])
        elif 'query rewriting specialist' in prompt:
            current = str(messages[-1].content)
            question = current.split('User Query:\n')[-1] if 'User Query:\n' in current else current
            reply = AIMessage(content='', tool_calls=[{'name': 'QueryAnalysis', 'id': 'fake-analysis',
                'args': {'is_clear': True, 'questions': [question], 'clarification_needed': ''}}])
        elif 'compact memory manager' in prompt:
            reply = AIMessage(content=str(messages[-1].content)[-300:])
        elif 'research context compressor' in prompt:
            reply = AIMessage(content=str(messages[-1].content)[-1200:])
        elif 'final-answer synthesizer' in prompt:
            text = str(messages[-1].content).split('Retrieved response 1:\n')[-1].strip()
            reply = AIMessage(content=text or "I couldn't find any information to answer your question in the available sources.")
        else:
            results = [str(item.content) for item in messages if isinstance(item, ToolMessage)]
            if not results:
                question = next((str(m.content) for m in messages if getattr(m, 'name', None) == 'agent_question'), 'query')
                reply = AIMessage(content='', tool_calls=[{'name': 'search_child_chunks', 'id': 'fake-search', 'args': {'query': question}}])
            elif all(text.startswith(('NO_', 'RETRIEVAL_ERROR:', 'PARENT_RETRIEVAL_ERROR:')) for text in results):
                reply = AIMessage(content='当前知识库中没有足够信息回答这个问题。')
            else:
                filenames = list(dict.fromkeys(re.findall(r'^File Name: (.+)$', '\n'.join(results), re.M)))
                facts = [text.split('Content:', 1)[-1].strip() for text in results]
                reply = AIMessage(content='根据知识库资料：\n' + '\n'.join(facts) + '\nSources:\n' + '\n'.join('- ' + name for name in filenames))
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self._generate(messages, stop, run_manager, **kwargs).generations[0].message
        if reply.tool_calls:
            yield ChatGenerationChunk(message=AIMessageChunk(content='', tool_call_chunks=[
                {'name': call['name'], 'args': json.dumps(call['args']), 'id': call['id'], 'index': index}
                for index, call in enumerate(reply.tool_calls)]))
        else:
            for index in range(0, len(str(reply.content)), 24):
                yield ChatGenerationChunk(message=AIMessageChunk(content=str(reply.content)[index:index + 24]))


class CompatibleReferenceModel:
    """Select the SDK's native function-calling parser without changing prompts."""
    def __init__(self, model):
        self.model = model

    def bind_tools(self, tools):
        return self.model.bind_tools(tools)

    def with_structured_output(self, schema):
        return self.model.with_structured_output(schema, method='function_calling')

    def invoke(self, messages, **kwargs):
        return self.model.invoke(messages, **kwargs)


def create_reference_model(settings):
    if settings.llm_provider == 'fake':
        return FakeReferenceModel()
    if settings.llm_provider == 'openai_compatible':
        if not all((settings.llm_base_url, settings.llm_api_key, settings.llm_model)):
            raise ValueError('MODEL_NOT_CONFIGURED')
        from langchain_openai import ChatOpenAI
        provider_options: dict[str, Any] = {}
        if settings.llm_model == 'deepseek-flash':
            # Thinking rejects forced schema tools and needs provider-specific tool history.
            provider_options['extra_body'] = {'thinking': {'type': 'disabled'}}
        return CompatibleReferenceModel(ChatOpenAI(
            model=settings.llm_model, base_url=settings.llm_base_url, api_key=settings.llm_api_key,
            temperature=settings.llm_temperature, seed=settings.llm_seed, max_retries=0,
            default_headers={'Accept-Encoding': 'identity'}, **provider_options))
    if settings.llm_provider == 'ollama':
        endpoint = urlparse(settings.ollama_base_url)
        if (endpoint.scheme != 'http' or endpoint.hostname not in {'localhost', '127.0.0.1', '::1'}
                or endpoint.username or endpoint.password or not settings.ollama_model.strip()):
            raise ValueError('LOCAL_MODEL_NOT_CONFIGURED')
        from langchain_ollama import ChatOllama
        return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url,
                          temperature=settings.llm_temperature, seed=settings.llm_seed,
                          client_kwargs={'trust_env': False})
    raise ValueError('UNKNOWN_MODEL_PROVIDER')
