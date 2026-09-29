from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app.rag.generator import AnswerGenerator
from app.rag.model_provider import (
    FakeProvider,
    ModelResult,
    OllamaProvider,
    OpenAICompatibleProvider,
    create_provider,
    visible_content,
)
from app.rag.model_schema import QueryAnalysis


def test_ollama_selected_without_cloud_fallback(settings, monkeypatch):
    settings = settings.model_copy(update={
        "llm_provider": "ollama",
        "ollama_model": "local-test",
        "llm_base_url": "https://cloud.example/v1",
        "llm_api_key": "secret",
        "llm_model": "cloud-test",
    })
    monkeypatch.setattr(
        "app.rag.model_provider.OpenAICompatibleProvider",
        lambda _: pytest.fail("Ollama 模式不应创建云端客户端"),
    )
    assert isinstance(create_provider(settings), OllamaProvider)


def test_no_ollama_model_fails_without_cloud_fallback(settings):
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "", "llm_api_key": "secret"})
    with pytest.raises(RuntimeError, match="OLLAMA_MODEL"):
        AnswerGenerator(settings).generate("问题", "证据")


def test_ollama_rejects_remote_endpoint(settings):
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "local-test", "ollama_base_url": "https://remote.example"})
    with pytest.raises(ValueError, match="只允许本机"):
        create_provider(settings)


def test_ollama_chinese_answer_tool_call_and_usage(settings):
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "local-test"})
    reply = AIMessage(
        content="根据资料，阈值是 16 A。",
        tool_calls=[{"name": "search_child_chunks", "args": {"query": "阈值"}, "id": "call-1"}],
        usage_metadata={"input_tokens": 30, "output_tokens": 12, "total_tokens": 42},
    )
    model = Mock()
    model.invoke.return_value = reply
    model.bind_tools.return_value = model
    provider = OllamaProvider(settings, model=model)
    result = provider.complete([{"role": "user", "content": "请用中文回答"}], tools=[{"type": "function", "function": {"name": "search_child_chunks"}}])
    assert "阈值" in result.content
    assert result.prompt_tokens == 30 and result.completion_tokens == 12
    assert result.tool_calls[0]["name"] == "search_child_chunks"
    model.bind_tools.assert_called_once()


def test_ollama_timeout_is_not_silently_retried_as_cloud(settings):
    settings = settings.model_copy(update={"llm_provider": "ollama", "ollama_model": "local-test"})
    model = Mock()
    model.invoke.side_effect = httpx.ReadTimeout("local timeout")
    with pytest.raises(RuntimeError, match="local timeout"):
        AnswerGenerator(settings, OllamaProvider(settings, model=model)).generate("问题", "证据")


def test_ollama_connection_and_timeout_config(settings, monkeypatch):
    settings = settings.model_copy(update={
        "llm_provider": "ollama",
        "ollama_model": "local-test",
        "llm_timeout_seconds": 7,
    })
    provider = OllamaProvider(settings)
    assert provider.model.client_kwargs["timeout"] == 7
    assert provider.model.client_kwargs["trust_env"] is False
    response = Mock()
    response.json.return_value = {"models": [{"name": "local-test"}]}
    client = MagicMock()
    client.get.return_value = response
    client.__enter__.return_value = client
    monkeypatch.setattr("app.rag.model_provider.httpx.Client", lambda **_: client)
    assert provider.check_connection() == ["local-test"]
    client.get.assert_called_once_with("http://127.0.0.1:11434/api/tags")


def test_generator_reports_node_and_estimated_tokens(settings):
    generator = AnswerGenerator(settings, FakeProvider())
    answer, trace = generator.generate_with_result("阈值是多少", "[来源]\n阈值为 16 A")
    assert "16 A" in answer
    assert trace["node"] == "collect_answer"
    assert trace["provider"] == "fake"
    assert trace["input_tokens_estimate"] > 0
    assert trace["output_tokens_estimate"] > 0
    assert trace["usage_source"] == "estimate_only"


def test_openai_provider_only_when_explicitly_selected(settings):
    settings = settings.model_copy(update={
        "llm_provider": "openai_compatible",
        "llm_base_url": "https://cloud.example/v1",
        "llm_api_key": "secret",
        "llm_model": "cloud-test",
    })
    reply = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="中文结果", tool_calls=[]))],
        usage=SimpleNamespace(prompt_tokens=9, completion_tokens=4),
    )
    client = Mock()
    client.chat.completions.create.return_value = reply
    result = OpenAICompatibleProvider(settings, client=client).complete([{"role": "user", "content": "中文"}])
    assert result == ModelResult("中文结果", "openai_compatible", "cloud-test", 9, 4)
    assert client.chat.completions.create.call_args.kwargs["max_tokens"] == settings.llm_max_output_tokens


def test_query_analysis_schema_accepts_at_most_three_questions():
    assert QueryAnalysis(is_clear=True, questions=["问题一"], clarification_needed=None).questions == ["问题一"]
    with pytest.raises(ValidationError):
        QueryAnalysis(is_clear=True, questions=["一", "二", "三", "四"])


def test_private_thinking_is_removed_before_returning_answer():
    assert visible_content("<think>不可展示的推理</think>结论是 16 A。") == "结论是 16 A。"
    assert visible_content("<think>未闭合的推理") == ""
