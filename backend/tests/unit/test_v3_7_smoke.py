"""冒烟验收不能让引用中的答案冒充正文，也不能隐藏调用超额。"""

from scripts.smoke_v3_7 import inspect_capture


def sample():
    return {"case_id": "Q2", "question": "阈值？", "response": "16 A 持续 100 ms。\n\n依据：\n阈值原文",
            "status": "completed", "sources": [{"page_start": 3}], "verification": {},
            "protected_files_unchanged": True,
            "answer_cost": {"model_calls": 2, "cloud_calls": 0, "budget_exceeded": False}}


def test_fixture_facts_are_checked_in_answer_body_not_citations():
    capture = sample()
    assert inspect_capture(capture, {})["literal_checks_passed"]
    capture["response"] = "请看引用。\n\n依据：\n16 A 持续 100 ms。"
    assert not inspect_capture(capture, {})["literal_checks_passed"]


def test_excess_call_or_changed_source_fails_even_with_correct_literal_answer():
    for changes in ({"model_calls": 3}, {"cloud_calls": 1}, {"budget_exceeded": True}):
        capture = sample()
        capture["answer_cost"].update(changes)
        assert not inspect_capture(capture, {})["literal_checks_passed"]
    capture = sample()
    capture["protected_files_unchanged"] = False
    assert not inspect_capture(capture, {})["literal_checks_passed"]
