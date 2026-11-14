"""Stage A regression examples: desired behavior is currently expected to fail.

These tests document known defects without changing production behavior.
Remove xfail only when the corresponding later stage implements and verifies the fix.
"""

from app.core.conversation import ConversationMemory
from app.core.answering import AnswerEvaluator


def test_explicit_model_is_not_clarified_by_reference_regex():
    memory = ConversationMemory()

    prepared = memory.prepare("phase-a-model", "PX-200该如何维护？")

    assert prepared.question_is_clear is True


def test_new_topic_does_not_become_pending_clarification():
    memory = ConversationMemory()
    memory.set_pending("phase-a-pending", "过流保护后如何恢复？")

    prepared = memory.prepare("phase-a-pending", "运行记录默认保留多久？")

    assert "原问题：过流保护后如何恢复？" not in prepared.rewritten_query
    assert prepared.rewritten_query == "运行记录默认保留多久？"


def test_omitted_safety_steps_do_not_receive_high_completeness():
    context = (
        "过流保护后如何恢复？"
        "如果故障代码为 OC-16，应先断开负载，等待设备完全放电，"
        "再检查负载端是否短路。确认负载正常后，按确认键清除告警，"
        "最后重新执行上电流程。"
    )
    answer = "检查负载，按确认键清除告警，然后重新启动。"

    result = AnswerEvaluator().evaluate("过流保护后如何恢复？", answer, context)

    assert result.completeness_status == "not_evaluated"
    assert "overall" not in result.model_dump()
