"""批量采集测试只用 fake Graph；不调用模型、不打开正式索引。"""

import copy
from types import SimpleNamespace

import pytest

from app.core.conversation import ConversationMemory
from scripts.capture_v4_formal import BatchCaptureProvider, capture_case, close_snapshot


class StubGraph:
    def __init__(self, statuses):
        self.memory = ConversationMemory()
        self.statuses = iter(statuses)
        self.calls = []

    def run(self, question, *, thread_id, action):
        self.calls.append((question, thread_id, action))
        status = next(self.statuses)
        if status == "clarification":
            self.memory.set_pending(thread_id, question)
        else:
            self.memory.clear_pending(thread_id)
        return SimpleNamespace(
            retrieved_results=[], retrieval_batches=[], request_id=f"r-{len(self.calls)}", thread_id=thread_id,
            rewritten_query=question, questions=[question] if status == "completed" else [],
            final_answer="真实模拟输出" if status == "completed" else "", status=status,
            context_messages=[], sources=[], model_trace=[],
            tool_trace=["search_child_chunks"] if status == "completed" else [],
            analysis_relation="new_question", evaluation=None, usage={"model_calls": 1, "cloud_calls": 0,
                "prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "duration_ms": 3})


def case():
    return {"case_id": "SYNTHETIC", "question": "多久？", "case_type": "answerable",
            "history_fixture": [{"role": "user", "content": "型号 PX-200。"}],
            "reference_answer": "不要复制这条标准答案"}


def test_capture_preserves_single_user_history_and_never_uses_reference_as_response():
    graph = StubGraph(["completed"])
    item = case()
    before = copy.deepcopy(item)
    result = capture_case(graph, item, index_version="index", answer_model="test")
    assert result["response"] == "真实模拟输出" != item["reference_answer"]
    assert result["history_fixture"] == before["history_fixture"] and item == before
    assert [message.role for message in graph.memory.thread_state(result["thread_id"]).recent_messages] == ["user"]
    assert result["human_review"]["status"] == "pending"


def test_flow_preserves_all_actual_turns_and_does_not_force_expected_decisions():
    graph = StubGraph(["completed", "cancelled"])
    item = case()
    item.update(case_type="clarification_flow", history_fixture=[], flow_steps=[
        {"question": "它？", "action": "auto", "expected_status": "clarification",
         "expected_pending_query": "它？", "retrieval_expected": False, "expected_questions": []},
        {"question": "", "action": "cancel", "expected_status": "cancelled",
         "expected_pending_query": "", "retrieval_expected": False, "expected_questions": []}])
    result = capture_case(graph, item, index_version="index", answer_model="test")
    assert [turn["status"] for turn in result["flow_turns"]] == ["completed", "cancelled"]
    assert not result["flow_checks"][0]["status_matches"]
    assert result["answer_cost"]["model_calls"] == 2
    assert result["question"] == item["question"]
    assert len({call[1] for call in graph.calls}) == 1


def test_unexpected_clarification_is_not_scored_as_successful_answer():
    result = capture_case(StubGraph(["clarification"]), case(), index_version="index", answer_model="test")
    assert result["run_error"] == "unexpected_clarification"


def test_cases_have_different_threads():
    graph = StubGraph(["completed", "completed"])
    one = capture_case(graph, case(), index_version="index", answer_model="test")
    two = capture_case(graph, case(), index_version="index", answer_model="test")
    assert one["thread_id"] != two["thread_id"]


def test_batch_provider_enforces_budget_and_retains_failed_attempt_cost_as_unknown():
    class Failure:
        def complete(self, *args, **kwargs):
            raise RuntimeError("test_failure")
    provider = BatchCaptureProvider(Failure(), max_calls=1)
    with pytest.raises(RuntimeError, match="test_failure"):
        provider.complete([])
    assert len(provider.calls) == 1 and provider.calls[0]["usage_recorded"] is False
    with pytest.raises(RuntimeError, match="capture_batch_budget_exceeded"):
        provider.complete([])
    assert len(provider.calls) == 1


def test_cleanup_closes_qdrant_client_not_vector_manager():
    closed = []
    index = SimpleNamespace(vector_db=SimpleNamespace(client=SimpleNamespace(close=lambda: closed.append(True))))
    close_snapshot(index)
    assert closed == [True]
