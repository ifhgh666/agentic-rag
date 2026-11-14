"""Prompt bindings use scripted replies and temporary data; no inference."""
import json
from copy import deepcopy

import pytest

from app.rag import nodes as reference_nodes
from app.core import legacy_summary as conversation_summary
from app.core import answering as generator, legacy_rag as query_planner, legacy_prompts as prompts
from app.core.conversation import ConversationMemory
from app.core.model_call import ModelCallBudget
from app.core.model_provider import ModelResult


class RecordingProvider:
    def __init__(self, *contents):
        self.contents = iter(contents)
        self.calls = []

    def complete(self, messages, *, tools=None):
        self.calls.append((deepcopy(messages), tools))
        return ModelResult(next(self.contents), "scripted", "prompt-binding", 24, 9)


def binding(monkeypatch, module, name):
    """Change the getter result so a copied/inlined prompt cannot pass."""
    original = getattr(prompts, name)
    calls = []
    marker = f"[binding:{name}]\n"

    def replacement(*args):
        calls.append(args)
        return marker + original(*args)

    monkeypatch.setattr(module, name, replacement, raising=False)
    return marker, calls


@pytest.mark.parametrize("limit", [256, 2000, 4096])
def test_summary_getter_receives_actual_limit_and_pending_stays_out(settings, monkeypatch, limit):
    marker, calls = binding(monkeypatch, conversation_summary, "get_conversation_summary_prompt")
    memory = ConversationMemory(history_messages_to_keep=2, summary_max_chars=limit)
    memory.append("t", "PX-200 的阈值？", "需要资料确认。")
    memory.append("t", "后续流程？", "按手册核对。")
    memory.set_pending("t", "PENDING_SENTINEL", ["SUPPLEMENT_SENTINEL"])
    provider = RecordingProvider(json.dumps({"summary": "用户讨论PX-200的阈值。"}, ensure_ascii=False))
    settings = settings.model_copy(update={"llm_provider": "ollama"})
    trace = conversation_summary.summarize_conversation(memory, "t", "", settings, None, lambda: provider)
    assert trace["status"] == "completed" and calls == [(limit,)]
    assert provider.calls[0][0][0]["content"].startswith(marker)
    assert "PENDING_SENTINEL" not in provider.calls[0][0][1]["content"]
    assert "SUPPLEMENT_SENTINEL" not in provider.calls[0][0][1]["content"]
    assert memory.pending("t") == "PENDING_SENTINEL" and len(provider.calls) == 1


def test_reference_orchestrator_getter_controls_native_messages(monkeypatch):
    from langchain_core.messages import AIMessage
    from tests.fakes.reference_model import ScriptedReferenceModel
    marker = "[REFERENCE_ORCHESTRATOR]"
    monkeypatch.setattr(reference_nodes, "get_orchestrator_prompt", lambda: marker)
    model = ScriptedReferenceModel(resolver=lambda *_: AIMessage(content="Model answer"))
    update = reference_nodes.orchestrator({"question": "q", "messages": []}, model.bind_tools([]))
    assert model.calls[0]["messages"][0].content == marker
    assert update["messages"][-1].content == "Model answer"
    assert update["iteration_count"] == 1

def test_reference_fallback_getter_is_used_without_business_repair(monkeypatch):
    from langchain_core.messages import AIMessage, HumanMessage
    from tests.fakes.reference_model import ScriptedReferenceModel
    monkeypatch.setattr(reference_nodes, "get_fallback_response_prompt", lambda: "[REFERENCE_FALLBACK]")
    model = ScriptedReferenceModel(resolver=lambda *_: AIMessage(content="Final supported gap"))
    result = reference_nodes.fallback_response({"question": "q", "messages": [HumanMessage(content="q")]}, model)
    assert len(model.calls) == 1 and model.calls[0]["messages"][0].content == "[REFERENCE_FALLBACK]"
    assert result["messages"][0].content == "Final supported gap"


def evidence():
    return [{"citation_id": "E1", "raw_text": "PX-200 阈值16 A。", "content": "PX-200 阈值16 A。", "source": "test.pdf"}]


def terminal():
    return json.dumps({"status": "answered", "answer": "阈值16 A。",
                       "citations": [{"citation_id": "E1", "quote": "PX-200 阈值16 A。"}]}, ensure_ascii=False)


def test_legacy_answer_uses_getter_without_extra_call(settings, monkeypatch):
    marker, calls = binding(monkeypatch, generator, "get_answer_generation_prompt")
    provider = RecordingProvider("根据资料答复")
    text, trace = generator.AnswerGenerator(settings, provider).generate_with_result("问题", "证据")
    assert text == "根据资料答复" and trace["input_tokens"] == 24
    assert calls == [()] and provider.calls[0][0][0]["content"].startswith(marker)
    assert len(provider.calls) == 1


def test_grounded_answer_and_repair_use_getters_with_original_payload(settings, monkeypatch):
    aggregation_marker, aggregation_calls = binding(monkeypatch, generator, "get_aggregation_prompt")
    repair_marker, repair_calls = binding(monkeypatch, generator, "get_answer_repair_prompt")
    provider = RecordingProvider("bad-json", terminal())
    text, ids, trace = generator.AnswerGenerator(settings, provider).generate_grounded_with_result("PX-200阈值？", evidence())
    assert text.startswith("阈值16 A") and ids == ["E1"]
    assert aggregation_calls == [()] and len(repair_calls) == 1
    assert provider.calls[0][0][0]["content"].startswith(aggregation_marker)
    assert "已检索证据：" in provider.calls[0][0][1]["content"]
    assert provider.calls[1][0][-1]["role"] == "user" and provider.calls[1][0][-1]["content"].startswith(repair_marker)
    assert len(provider.calls) == 2 and len(trace["repair_calls"]) == 1


def test_synthesis_getters_keep_original_question_and_branches(settings, monkeypatch):
    aggregation_marker, aggregation_calls = binding(monkeypatch, generator, "get_aggregation_prompt")
    instruction_marker, instruction_calls = binding(monkeypatch, generator, "get_aggregation_instruction")
    provider = RecordingProvider(terminal())
    original = "PX-200在245 V持续400 ms时的保护和条件性恢复？"
    branches = [{"question": "保护？", "result": {"status": "completed", "branch_answer": {"answer": "模拟分支"}}},
                {"question": "恢复？", "result": {"status": "failed", "stop_reason": "timeout", "final_answer": "本轮超时"}}]
    from app.core.model_call import build_model_budget
    budget = build_model_budget(settings)
    budget.start("r")
    budget.configure_branches("r", 2)
    result = generator.AnswerGenerator(settings, provider, budget).synthesize_branch_answers(original, branches, evidence(), "r")
    assert result[3] == "completed" and aggregation_calls == [()] and instruction_calls == [()]
    messages, tools = provider.calls[0]
    assert tools is None and messages[0]["content"].startswith(aggregation_marker)
    payload = json.loads(messages[1]["content"].split("分支汇总：", 1)[1])
    assert payload["instruction"].startswith(instruction_marker) and payload["original_question"] == original
    assert payload["branches"][1]["runtime_message"] == "本轮超时" and len(provider.calls) == 1


def test_legacy_query_rewriter_uses_getter_without_restoring_graph_routing(settings, monkeypatch):
    marker, calls = binding(monkeypatch, query_planner, "get_retrieval_rewrite_prompt")
    provider = RecordingProvider("PX-200 过流保护电流")
    result, trace = query_planner.ModelQueryGenerator(settings, provider).generate_with_result("PX-200 阈值？", ["PX-200 阈值？"])
    assert result == "PX-200 过流保护电流" and trace["input_tokens"] == 24
    assert calls == [()] and provider.calls[0][0][0]["content"].startswith(marker)
    assert len(provider.calls) == 1

