"""V3-2 本机 Ollama 最小验收；不读取真实文档、不调用云端。"""

import json

from app.config import Settings
from app.core.answering import AnswerGenerator
from app.core.model_provider import OllamaProvider, create_provider


def main() -> None:
    settings = Settings()
    if settings.llm_provider != "ollama":
        raise RuntimeError("验收前必须设置 LLM_PROVIDER=ollama")
    provider = create_provider(settings)
    assert isinstance(provider, OllamaProvider)
    models = provider.check_connection()
    if settings.ollama_model not in models:
        raise RuntimeError(f"本地 Ollama 未安装模型 {settings.ollama_model}")

    answer, call = AnswerGenerator(settings, provider).generate_with_result(
        "PX-200 的过流保护阈值是多少？",
        "[测试手册，第 1 页]\nPX-200 的过流保护阈值为 16 A。",
    )
    if "16" not in answer:
        raise AssertionError(f"本地模型没有正确回答最小问题：{answer}")
    if "<think>" in answer.lower() or "</think>" in answer.lower():
        raise AssertionError("回答泄露了思考过程")
    if len(answer) > 160:
        raise AssertionError("模型输出过长，可能包含未标记的分析过程")
    if not any("\u4e00" <= char <= "\u9fff" for char in answer):
        raise AssertionError("本地模型没有输出中文")

    tool = {
        "type": "function",
        "function": {
            "name": "search_child_chunks",
            "description": "搜索知识库中的证据片段",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "检索关键词"}},
                "required": ["query"],
            },
        },
    }
    decision = provider.complete(
        [
            {"role": "system", "content": "请先调用 search_child_chunks 工具查找证据，不要直接回答。"},
            {"role": "user", "content": "请检索 PX-200 的过流保护阈值。"},
        ],
        tools=[tool],
    )
    if not any(item.get("name") == "search_child_chunks" for item in decision.tool_calls):
        raise AssertionError("本地模型没有按要求发起工具调用")
    print(json.dumps({"model": settings.ollama_model, "answer": answer, "model_call": call, "tool_call": decision.tool_calls[0]["name"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
