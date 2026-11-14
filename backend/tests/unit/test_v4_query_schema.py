import pytest
from pydantic import ValidationError
from jsonschema import Draft202012Validator

from app.core.legacy_schemas import QueryAnalysis


def test_clear_decision_preserves_one_to_three_distinct_questions():
    decision = QueryAnalysis(
        is_clear=True,
        questions=["  PX-200 的阈值是多少？  ", "运行记录保留多久？"],
        clarification_needed="",
    )

    assert decision.questions == ["PX-200 的阈值是多少？", "运行记录保留多久？"]
    assert decision.clarification_needed == ""


@pytest.mark.parametrize(
    "questions",
    [[], ["问题一", "问题二", "问题三", "问题四"], ["问题一", " 问题一 "], [" "]],
)
def test_clear_decision_rejects_missing_excess_duplicate_or_blank_questions(questions):
    with pytest.raises(ValidationError):
        QueryAnalysis(is_clear=True, questions=questions, clarification_needed="")


def test_unclear_decision_requires_one_clarification_and_no_questions():
    decision = QueryAnalysis(
        is_clear=False,
        questions=[],
        clarification_needed="请说明设备型号。",
    )
    assert decision.questions == []
    assert decision.clarification_needed == "请说明设备型号。"

    with pytest.raises(ValidationError):
        QueryAnalysis(is_clear=False, questions=["已经清楚的问题"], clarification_needed="请补充型号。")
    with pytest.raises(ValidationError):
        QueryAnalysis(is_clear=False, questions=[], clarification_needed="  ")


@pytest.mark.parametrize("extra", ["relation", "source", "failure_reason", "requires_procedure"])
def test_runtime_metadata_is_not_a_model_output_field(extra):
    with pytest.raises(ValidationError):
        QueryAnalysis.model_validate({"is_clear": True, "questions": ["问题一"], "clarification_needed": "", extra: "value"})


def test_clear_decision_cannot_also_request_clarification():
    with pytest.raises(ValidationError):
        QueryAnalysis(
            is_clear=True,
            questions=["问题一"],
            clarification_needed="请补充型号。",
        )


@pytest.mark.parametrize("payload, valid", [
    ({"is_clear": True, "questions": ["问题一"], "clarification_needed": ""}, True),
    ({"is_clear": True, "questions": ["一", "二", "三"], "clarification_needed": ""}, True),
    ({"is_clear": False, "questions": [], "clarification_needed": "请说明所指设备。"}, True),
    ({"is_clear": True, "questions": ["问题一"], "clarification_needed": "无"}, False),
    ({"is_clear": True, "questions": ["问题一"], "clarification_needed": "否"}, False),
    ({"is_clear": True, "questions": ["问题一"], "clarification_needed": "记录保留期限"}, False),
    ({"is_clear": True, "questions": [], "clarification_needed": ""}, False),
    ({"is_clear": False, "questions": ["问题一"], "clarification_needed": "请补充型号。"}, False),
    ({"is_clear": False, "questions": [], "clarification_needed": ""}, False),
    ({"is_clear": True, "questions": ["一", "二", "三", "四"], "clarification_needed": ""}, False),
    ({"is_clear": "true", "questions": ["问题一"], "clarification_needed": ""}, False),
    ({"is_clear": True, "questions": ["问题一"], "clarification_needed": None}, False),
    ({"is_clear": True, "questions": ["问题一"], "clarification_needed": "", "extra": 1}, False),
    ({"is_clear": True, "questions": ["问题一"]}, False),
])
def test_generation_schema_enforces_clarity_without_pydantic_validators(payload, valid):
    # Validate the actual format schema independently, not the runtime model.
    schema = QueryAnalysis.model_json_schema()
    Draft202012Validator.check_schema(schema)
    assert Draft202012Validator(schema).is_valid(payload) is valid


@pytest.mark.parametrize("clarification", ["无", "否", "记录保留期限"])
def test_runtime_does_not_silently_erase_nonempty_clear_clarification(clarification):
    with pytest.raises(ValidationError):
        QueryAnalysis(is_clear=True, questions=["问题一"], clarification_needed=clarification)
