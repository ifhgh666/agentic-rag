"""Model protocols, provider adapters and token estimation."""
from __future__ import annotations

import httpx
import inspect
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field, replace
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel
from typing import Any, Callable, Protocol
from urllib.parse import urlparse
from uuid import uuid4
from ..config import Settings
from .legacy_prompts import (
    get_answer_context_marker,
    get_branch_synthesis_marker,
    get_schema_instruction_prompt,
)


@dataclass(frozen=True)
class ModelResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    structured_output: BaseModel | None = None
    # 本次调用最终生效的结构化输出模式与是否发生回退；仅用于可观测，不参与校验。
    structured_mode: str = "none"
    structured_fallback: bool = False

@dataclass(frozen=True)
class PreparedAttempt:
    messages: list[dict[str, Any]]
    tools: list[dict] | None = None
    response_format: dict | None = None
    attempt_index: int = 1
    structured_mode: str = "none"

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")

def estimate_tokens(text: str) -> int:
    """Estimate tokens for deterministic input-window guards."""
    if not text or not text.strip():
        return 0
    cjk_count = len(_CJK_RE.findall(text))
    words = _WORD_RE.findall(text)
    word_chars = sum(len(item) for item in words)
    word_tokens = sum(max(1, math.ceil(len(item) / 4)) for item in words)
    remaining = max(0, len(text) - cjk_count - word_chars)
    return max(1, cjk_count + word_tokens + math.ceil(remaining / 4))

_MODEL_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="rag-model-call")

class ChatProvider(Protocol):
    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
                 response_schema: type[BaseModel] | None = None) -> ModelResult: ...

BeforeAttempt = Callable[[PreparedAttempt], float]

def normalize_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for call in calls:
        function = call.get("function") or {}
        args = call.get("args", function.get("arguments", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_invalid_arguments": args}
        if not isinstance(args, dict):
            args = {"_invalid_arguments": args}
        normalized.append({"id": str(call.get("id") or f"generated-{uuid4().hex}"),
                           "name": str(call.get("name") or function.get("name") or ""),
                           "args": args, "type": "tool_call"})
    return normalized

def langchain_messages(messages: list[dict[str, Any]]) -> list:
    converted = []
    for item in messages:
        role, content = item["role"], item.get("content") or ""
        if role == "assistant":
            converted.append(AIMessage(content=content, tool_calls=normalize_tool_calls(item.get("tool_calls", []))))
        elif role == "tool":
            converted.append(ToolMessage(content=content, tool_call_id=item["tool_call_id"], name=item.get("name")))
        else:
            converted.append((SystemMessage if role == "system" else HumanMessage)(content=content))
    return converted

def openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted = []
    for item in messages:
        value = {key: item[key] for key in ("role", "content", "name", "tool_call_id") if key in item}
        if item.get("tool_calls"):
            value["tool_calls"] = [{"id": call["id"], "type": "function", "function": {
                "name": call["name"], "arguments": json.dumps(call["args"], ensure_ascii=False)}}
                for call in normalize_tool_calls(item["tool_calls"])]
        converted.append(value)
    return converted

def complete_model(provider: ChatProvider, messages: list[dict[str, Any]], *,
                   tools: list[dict] | None = None, timeout_seconds: float | None = None,
                   response_schema: type[BaseModel] | None = None,
                   before_attempt: BeforeAttempt | None = None) -> ModelResult:
    kwargs: dict[str, Any] = {}
    if response_schema is not None:
        if tools:
            raise ValueError("structured_output_cannot_mix_with_tools")
        kwargs["response_schema"] = response_schema
    if tools is not None:
        kwargs["tools"] = tools
    if timeout_seconds is not None and "timeout_seconds" in inspect.signature(provider.complete).parameters:
        kwargs["timeout_seconds"] = max(0.01, timeout_seconds)
    def invoke():
        call_kwargs = dict(kwargs)
        parameters = inspect.signature(provider.complete).parameters
        if before_attempt is not None:
            if "before_attempt" in parameters:
                call_kwargs["before_attempt"] = before_attempt
            else:
                remaining = before_attempt(PreparedAttempt(messages, tools,
                    response_schema.model_json_schema() if response_schema else None,
                    structured_mode="schema" if response_schema else "none"))
                if "timeout_seconds" in parameters:
                    call_kwargs["timeout_seconds"] = remaining
        return provider.complete(messages, **call_kwargs)

    if timeout_seconds is None:
        result = invoke()
    else:
        if timeout_seconds <= 0:
            raise TimeoutError("model_total_timeout")
        # Transport read timeouts reset as streamed chunks arrive. Bound the whole
        # wait separately; late provider results never update request state/history.
        future = _MODEL_EXECUTOR.submit(invoke)
        try:
            result = future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError("model_total_timeout") from None
    if response_schema is not None:
        try:
            parsed = response_schema.model_validate_json(result.content)
        except (ValueError, TypeError):
            parsed = None
        # Retain the first raw reply even when custom field invariants fail.
        # No parsing exception, model retry or synthesized answer is exposed.
        result = replace(result, structured_output=parsed)
    return result

def schema_instruction(schema: type[BaseModel]) -> str:
    """把结构要求写成提示词文本，供不支持严格结构模式的端点回退时使用。"""
    spec = json.dumps(schema.model_json_schema(), ensure_ascii=False, sort_keys=True)
    return get_schema_instruction_prompt(spec)

def with_schema_instruction(messages: list[dict[str, Any]], schema: type[BaseModel]) -> list[dict[str, Any]]:
    """回退时在既有系统消息后追加结构要求；没有系统消息时补一条。"""
    instruction = schema_instruction(schema)
    converted = [dict(item) for item in messages]
    for item in converted:
        if item.get("role") == "system":
            item["content"] = f"{item.get('content') or ''}\n\n{instruction}".strip()
            return converted
    converted.insert(0, {"role": "system", "content": instruction})
    return converted

def rejects_structured_format(exc: Exception) -> bool:
    """仅端点以“该 response_format 类型不可用”拒绝时返回 True；其他异常不回退。"""
    if getattr(exc, "status_code", None) != 400:
        return False
    text = str(exc).lower()
    return "response_format" in text or "json_schema" in text

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
        self._external_model = model is not None
        if model is None:
            from langchain_ollama import ChatOllama

            model = ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.llm_temperature,
                seed=settings.llm_seed,
                num_predict=settings.llm_max_output_tokens,
                num_ctx=settings.model_context_window,
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

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
                 timeout_seconds: float | None = None,
                 response_schema: type[BaseModel] | None = None,
                 before_attempt: BeforeAttempt | None = None) -> ModelResult:
        if response_schema is not None and tools:
            raise ValueError("structured_output_cannot_mix_with_tools")
        converted = langchain_messages(messages)

        def transport(seconds):
            from langchain_ollama import ChatOllama
            return ChatOllama(model=self.settings.ollama_model, base_url=self.settings.ollama_base_url,
                temperature=self.settings.llm_temperature, seed=self.settings.llm_seed,
                num_predict=self.settings.llm_max_output_tokens, num_ctx=self.settings.model_context_window,
                reasoning=False, client_kwargs={"timeout": min(seconds, self.settings.llm_timeout_seconds), "trust_env": False})

        def prepare(base):
            if response_schema is not None:
                return base.with_structured_output(response_schema, method="json_schema", include_raw=True)
            return base.bind_tools(tools) if tools else base

        base = transport(timeout_seconds) if timeout_seconds is not None and not self._external_model else self.model
        model = prepare(base)
        if before_attempt is not None:
            remaining = before_attempt(PreparedAttempt(messages, tools,
                response_schema.model_json_schema() if response_schema else None,
                structured_mode="json_schema" if response_schema else "none"))
            if not self._external_model:
                # Fresh transport uses the granted remaining time; original messages,
                # tools and schema remain the prepared input. No shared client mutation.
                model = prepare(transport(min(timeout_seconds or self.settings.llm_timeout_seconds, remaining)))
        parsed = None
        if response_schema is not None:
            response = model.invoke(converted)
            reply, parsed = response["raw"], response["parsed"]
        else:
            reply = model.invoke(converted)
        usage = reply.usage_metadata or {}
        return ModelResult(
            content=visible_content(str(reply.content or "")),
            provider="ollama",
            model=self.settings.ollama_model,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            tool_calls=normalize_tool_calls(list(reply.tool_calls or [])),
            structured_output=parsed,
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
                # 不依赖响应体压缩：本机部分解压绑定与 HTTP 客户端版本不兼容，
                # 压缩响应会在解码阶段中断整次调用。JSON 接口的体积代价可忽略。
                default_headers={"Accept-Encoding": "identity"},
            )
        self.client = client

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
                 timeout_seconds: float | None = None,
                 response_schema: type[BaseModel] | None = None,
                 before_attempt: BeforeAttempt | None = None) -> ModelResult:
        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": openai_messages(messages),
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_output_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if response_schema is not None and tools:
            raise ValueError("structured_output_cannot_mix_with_tools")
        if timeout_seconds is not None:
            kwargs["timeout"] = min(timeout_seconds, self.settings.llm_timeout_seconds)
        if response_schema is None:
            if before_attempt is not None:
                kwargs["timeout"] = min(kwargs.get("timeout", self.settings.llm_timeout_seconds),
                                        before_attempt(PreparedAttempt(messages, tools)))
            return self._request(kwargs, structured_mode="none")
        strict = dict(kwargs)
        strict["response_format"] = {"type": "json_schema", "json_schema": {
            "name": response_schema.__name__, "schema": response_schema.model_json_schema(), "strict": True,
        }}
        if before_attempt is not None:
            strict["timeout"] = min(kwargs.get("timeout", self.settings.llm_timeout_seconds),
                before_attempt(PreparedAttempt(messages, tools, strict["response_format"], structured_mode="json_schema")))
        try:
            return self._request(strict, structured_mode="json_schema")
        except Exception as exc:
            # 只有端点明确拒绝该 response_format 类型才回退；超时、鉴权与传输错误不回退。
            if not rejects_structured_format(exc):
                raise
        fallback = dict(kwargs)
        fallback_messages = with_schema_instruction(messages, response_schema)
        fallback["messages"] = openai_messages(fallback_messages)
        fallback["response_format"] = {"type": "json_object"}
        if before_attempt is not None:
            fallback["timeout"] = min(kwargs.get("timeout", self.settings.llm_timeout_seconds),
                before_attempt(PreparedAttempt(fallback_messages, tools,
                    fallback["response_format"], attempt_index=2, structured_mode="json_object")))
        return self._request(fallback, structured_mode="json_object", structured_fallback=True)

    def _request(self, kwargs: dict[str, Any], *, structured_mode: str,
                 structured_fallback: bool = False) -> ModelResult:
        reply = self.client.chat.completions.create(**kwargs)
        choice = reply.choices[0].message
        usage = reply.usage
        return ModelResult(
            content=visible_content(choice.content or ""),
            provider="openai_compatible",
            model=self.settings.llm_model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            tool_calls=normalize_tool_calls([item.model_dump() for item in (choice.tool_calls or [])]),
            structured_mode=structured_mode,
            structured_fallback=structured_fallback,
        )

class FakeProvider:
    """显式测试模式；不会建立网络连接。"""

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict] | None = None,
                 response_schema: type[BaseModel] | None = None) -> ModelResult:
        synthesis_marker = get_branch_synthesis_marker()
        if not tools and synthesis_marker in messages[-1]["content"]:
            branches = json.loads(messages[-1]["content"].split(synthesis_marker, 1)[1])["branches"]
            answers = [b["branch_answer"] for b in branches if b.get("branch_answer")]
            citations = [c for a in answers for c in a.get("citations", [])]
            status = "answered" if citations and all(b["status"] == "completed" for b in branches) else "partial" if citations else "insufficient"
            return ModelResult(json.dumps({"status": status,
                "answer": "\n\n".join(f"{index}. " + b["question"] + "\n" + (b.get("branch_answer") or {}).get("answer", b.get("runtime_message", "资料不足")) for index, b in enumerate(branches, 1)),
                "citations": citations, "missing_information": []}, ensure_ascii=False), "fake", "fake")
        if tools:
            tool_messages = [m for m in messages if m["role"] == "tool"]
            if not tool_messages:
                question = next((m["content"] for m in messages if m["role"] == "user" and "本分支完整问题：" in m["content"]), messages[-1]["content"])
                question = question.split("本分支完整问题：")[-1].split("\n分支：")[0]
                return ModelResult("", "fake", "fake", tool_calls=[{"id": f"fake-{uuid4().hex}",
                    "name": "search_child_chunks", "args": {"query": question, "limit": 3}, "type": "tool_call"}])
            evidence = []
            for m in tool_messages:
                payload = json.loads(m["content"])
                evidence.extend(payload.get("results", []))
            if not evidence:
                payload = {"status": "insufficient", "answer": "当前知识库中没有足够信息回答这个问题。", "missing_information": ["未检索到相关资料"]}
            else:
                payload = {"status": "answered", "answer": "根据知识库资料：\n" + "\n".join(e["content"] for e in evidence),
                    "citations": [{"citation_id": e["citation_id"], "quote": e["content"]} for e in evidence]}
            return ModelResult(json.dumps(payload, ensure_ascii=False), "fake", "fake")
        context = messages[-1]["content"].split(get_answer_context_marker(), 1)[-1]
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

def token_details(messages: list[dict[str, Any]], result: ModelResult) -> dict[str, Any]:
    prompt_estimate = estimate_tokens(json.dumps(messages, ensure_ascii=False))
    completion_estimate = estimate_tokens(result.content + json.dumps(result.tool_calls, ensure_ascii=False))
    return {
        "provider": result.provider,
        "model": result.model,
        "input_tokens_estimate": prompt_estimate,
        "output_tokens_estimate": completion_estimate,
        "input_tokens": result.prompt_tokens,
        "output_tokens": result.completion_tokens,
        "usage_source": "provider" if result.prompt_tokens is not None and result.completion_tokens is not None else "estimate_only",
    }
