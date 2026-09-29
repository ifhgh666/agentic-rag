from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from ..config import Settings
from .context_compression import estimate_tokens


@dataclass(frozen=True)
class ModelResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class ChatProvider(Protocol):
    def complete(self, messages: list[dict[str, str]], *, tools: list[dict] | None = None) -> ModelResult: ...


def visible_content(content: str) -> str:
    """不要把模型的 <think> 私有推理交给回答和前端。"""
    cleaned = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.IGNORECASE | re.DOTALL)
    if re.search(r"<think>", cleaned, flags=re.IGNORECASE):
        cleaned = re.split(r"<think>", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
    return cleaned.strip()


class OllamaProvider:
    def __init__(self, settings: Settings, model: Any = None):
        if not settings.ollama_model.strip():
            raise ValueError("OLLAMA_MODEL 未配置；请先安装 Ollama 并确认已下载的模型名称。")
        endpoint = urlparse(settings.ollama_base_url)
        if endpoint.scheme != "http" or endpoint.hostname not in {"localhost", "127.0.0.1", "::1"} or endpoint.username or endpoint.password:
            raise ValueError("Ollama 模式只允许本机 HTTP 地址，防止知识库内容发送到云端。")
        self.settings = settings
        if model is None:
            from langchain_ollama import ChatOllama

            model = ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.llm_temperature,
                seed=settings.llm_seed,
                num_predict=settings.llm_max_output_tokens,
                reasoning=False,
                client_kwargs={"timeout": settings.llm_timeout_seconds, "trust_env": False},
            )
        self.model = model

    def check_connection(self) -> list[str]:
        # 本地健康检查不得被进程代理转送出去。
        with httpx.Client(timeout=min(self.settings.llm_timeout_seconds, 5), trust_env=False) as client:
            response = client.get(f"{self.settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
        return [str(item["name"]) for item in response.json().get("models", [])]

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict] | None = None) -> ModelResult:
        model = self.model.bind_tools(tools) if tools else self.model
        reply = model.invoke([(item["role"], item["content"]) for item in messages])
        usage = reply.usage_metadata or {}
        return ModelResult(
            content=visible_content(str(reply.content or "")),
            provider="ollama",
            model=self.settings.ollama_model,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            tool_calls=list(reply.tool_calls or []),
        )


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings, client: Any = None):
        if not all((settings.llm_base_url, settings.llm_api_key, settings.llm_model)):
            raise ValueError("云模型需要 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL。")
        self.settings = settings
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
        self.client = client

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict] | None = None) -> ModelResult:
        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_output_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        reply = self.client.chat.completions.create(**kwargs)
        choice = reply.choices[0].message
        usage = reply.usage
        return ModelResult(
            content=visible_content(choice.content or ""),
            provider="openai_compatible",
            model=self.settings.llm_model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            tool_calls=[item.model_dump() for item in (choice.tool_calls or [])],
        )


class FakeProvider:
    """显式测试模式；不会建立网络连接。"""

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict] | None = None) -> ModelResult:
        context = messages[-1]["content"].split("知识库上下文：\n", 1)[-1]
        first_block = context.split("\n\n", 1)[0]
        evidence = first_block.split("\n", 1)[-1].strip()
        return ModelResult(content=f"根据知识库中的相关内容：\n\n{evidence[:900]}", provider="fake", model="fake")


def create_provider(settings: Settings) -> ChatProvider:
    # 显式白名单；ollama 不读取 LLM_BASE_URL/LLM_API_KEY，也不暗中回退到云端。
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings)
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleProvider(settings)
    if settings.llm_provider == "fake":
        return FakeProvider()
    raise ValueError(f"未知的 LLM_PROVIDER：{settings.llm_provider}")


def token_details(messages: list[dict[str, str]], result: ModelResult) -> dict[str, Any]:
    prompt_estimate = sum(estimate_tokens(item["content"]) for item in messages)
    completion_estimate = estimate_tokens(result.content) if result.content else 0
    return {
        "provider": result.provider,
        "model": result.model,
        "input_tokens_estimate": prompt_estimate,
        "output_tokens_estimate": completion_estimate,
        "input_tokens": result.prompt_tokens,
        "output_tokens": result.completion_tokens,
        "usage_source": "provider" if result.prompt_tokens is not None and result.completion_tokens is not None else "estimate_only",
    }
