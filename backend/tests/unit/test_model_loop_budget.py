from concurrent.futures import ThreadPoolExecutor
import time

import pytest

from app.core.model_call import ModelCallBudget


def test_parallel_branches_cannot_consume_each_others_terminal_or_synthesis_slots():
    budget = ModelCallBudget(8, 12, {})
    budget.start("r")
    assert budget.reserve("r", "query_analysis")
    budget.configure_branches("r", 3)
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda _: budget.reserve("r", "orchestrator", branch_id="B1"), range(20)))
    assert sum(results) == 3
    for branch in ("B2", "B3"):
        assert all(budget.reserve("r", "orchestrator", branch_id=branch) for _ in range(3))
    assert budget.reserve("r", "final_synthesis")
    assert budget.reserve("r", "answer_repair")
    assert budget.snapshot("r")["model_calls"] == 12
    assert not budget.reserve("r", "conversation_summary", required=False)


@pytest.mark.parametrize("count, quota, synthesis", [(1, 5, 0), (2, 4, 1), (3, 3, 1)])
def test_branch_quota_and_synthesis_reservation_match_question_count(count, quota, synthesis):
    budget = ModelCallBudget(8, 12, {})
    request_id = f"r-{count}"
    budget.start(request_id)
    budget.reserve(request_id, "query_analysis")
    budget.configure_branches(request_id, count)

    for branch_id in (f"B{i + 1}" for i in range(count)):
        assert all(
            budget.reserve(request_id, "orchestrator", branch_id=branch_id)
            for _ in range(quota)
        )
        assert not budget.reserve(request_id, "orchestrator", branch_id=branch_id)
    assert bool(budget.reserve(request_id, "final_synthesis")) is bool(synthesis)


def test_auxiliary_and_history_cannot_steal_branch_slots():
    budget = ModelCallBudget(8, 12, {})
    budget.start("r")
    budget.reserve("r", "query_analysis")
    budget.configure_branches("r", 3)
    assert not budget.reserve("r", "conversation_summary", required=False)
    assert budget.reserve("r", "answer_repair")
    assert not budget.reserve("r", "answer_repair")
    assert budget.branch_remaining("r", "B1") == 3


def test_deadline_and_tool_quotas():
    budget = ModelCallBudget(8, 12, {}, timeout_seconds=0.01, tool_limit=16)
    budget.start("r")
    budget.configure_branches("r", 3)
    assert all(budget.reserve_tool("r", "B1") for _ in range(5))
    assert not budget.reserve_tool("r", "B1")
    time.sleep(0.02)
    assert budget.remaining_seconds("r") == 0
    assert not budget.reserve("r", "orchestrator", branch_id="B2")
