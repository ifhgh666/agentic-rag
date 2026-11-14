"""Native chat-model script for reference graph contract tests; no network."""
import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field


class ScriptedReferenceModel(BaseChatModel):
    resolver: Any = Field(exclude=True)
    calls: list = Field(default_factory=list, exclude=True)

    @property
    def _llm_type(self):
        return 'scripted-reference016'

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(tool) for tool in tools], **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append({'messages': list(messages), 'kwargs': kwargs})
        reply = self.resolver(messages, kwargs, len(self.calls))
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self._generate(messages, stop, run_manager, **kwargs).generations[0].message
        if reply.tool_calls:
            yield ChatGenerationChunk(message=AIMessageChunk(content=reply.content,
                tool_call_chunks=[{'name': call['name'], 'args': json.dumps(call['args']),
                                  'id': call['id'], 'index': i} for i, call in enumerate(reply.tool_calls)]))
        else:
            text = str(reply.content)
            for i in range(0, len(text), 7):
                yield ChatGenerationChunk(message=AIMessageChunk(content=text[i:i + 7]))


def routing_reply(needs_knowledge: bool):
    return AIMessage(content='', tool_calls=[{'name': 'ToolRouting', 'id': 'route',
        'args': {'needs_knowledge': needs_knowledge}}])


def basic_resolver(messages, kwargs, call_number):
    system = str(messages[0].content)
    if 'classify whether the latest user request requires the PDF knowledge base' in system:
        return routing_reply(True)
    if 'query rewriting specialist' in system:
        text = str(messages[-1].content).split('User Query:\n')[-1]
        return AIMessage(content='', tool_calls=[{'name': 'QueryAnalysis', 'id': 'analysis',
            'args': {'is_clear': True, 'questions': [text], 'clarification_needed': ''}}])
    if 'compact memory manager' in system:
        return AIMessage(content='Previous conversation summary.')
    if 'research context compressor' in system:
        return AIMessage(content='## guide.pdf\nEvidence: voltage is 230 V.')
    if 'final-answer synthesizer' in system:
        return AIMessage(content='Final answer: 230 V.\nSources:\n- guide.pdf')
    if any(getattr(message, 'type', '') == 'tool' for message in messages):
        return AIMessage(content='The voltage is 230 V.\nSources:\n- guide.pdf')
    return AIMessage(content='', tool_calls=[{'name': 'search_child_chunks', 'id': 'search',
        'args': {'query': 'voltage'}}])
