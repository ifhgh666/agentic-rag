"""Offline artifact integrity only; never call a model or open the formal index."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import fitz
import pytest

from app.core.conversation import ConversationMemory, ThreadState
from scripts.validate_v4_gold_dataset import DEFAULT_DATASET, normalized, validate_dataset


ROOT = Path(__file__).resolve().parents[3]
FEATURE = ROOT / "specs/004-query-clarification-ragas"


def read_json(name):
    return json.loads((FEATURE / name).read_text(encoding="utf-8"))


GOLD = read_json("gold-cases-v2.json")
RUBRICS = read_json("gold-cases-v2-rubrics.json")
STATES = read_json("clarification-state-fixtures-v2.json")
CASES = {case["case_id"]: case for case in GOLD["cases"]}
GUIDES = {case["case_id"]: case for case in RUBRICS["cases"]}


def test_candidate_provenance_is_valid_but_not_formally_approved():
    report = validate_dataset(GOLD)
    assert report["valid"], report["errors"]
    assert report["quotes_checked"] == report["quotes_matched"]
    assert report["case_count"] == 23
    assert not report["formal_ready"]
    assert report["eligible_case_ids"] == report["ragas_case_ids"] == []
    formal = validate_dataset(GOLD, require_reviewed=True)
    assert not formal["valid"] and not formal["formal_ready"]
    assert [error["code"] for error in formal["errors"]] == ["review_required"]


def test_approved_history_and_default_dataset_are_not_replaced():
    original = FEATURE / "gold-cases-v1.json"
    assert DEFAULT_DATASET == original
    assert hashlib.sha256(original.read_bytes()).hexdigest().upper() == (
        "9049A61F71DE950E872125A6A6C78DDFFB36C4FB43D574EDE58F25982AB2B369"
    )
    assert read_json("gold-cases-v1.json")["status"] == "reviewed"


def test_original_case_ids_and_questions_keep_auditable_mapping():
    for original in read_json("gold-cases-v1.json")["cases"]:
        assert CASES[original["case_id"]]["question"] == original["question"]


@pytest.mark.parametrize("case_id", list(CASES))
def test_candidate_review_and_companion_are_consistent(case_id):
    case, guide = CASES[case_id], GUIDES[case_id]
    assert case["dataset_version"] == RUBRICS["dataset_version"] == STATES["dataset_version"] == "candidate-2.0"
    assert case["review_status"] == guide["review_status"] == "draft"
    assert case["reviewer"] is case["reviewed_at"] is case["review_kind"] is None
    assert guide["reviewer"] is guide["reviewed_at"] is None
    assert case["required_facts"] == guide["core_facts"]
    assert case.get("ordered_facts", []) == guide["ordered_facts"]
    assert guide["behavior_criteria"]


def test_scope_only_requires_facts_actually_requested():
    assert CASES["Q2"]["required_facts"] == ["输出电流超过 16 A", "持续 100 ms"]
    assert CASES["Q4"]["required_facts"] == CASES["Q10"]["required_facts"] == ["三年"]
    assert CASES["Q8"]["required_facts"] == ["三年", "每六个月"]
    assert CASES["Q7"]["required_facts"] == ["每六个月"]
    assert CASES["Q14"]["required_facts"] == CASES["Q2"]["required_facts"]
    assert CASES["Q23"]["required_facts"] == ["先进先出"]
    assert "合格的万用表" not in CASES["Q1"]["required_facts"]
    assert GUIDES["Q1"]["optional_facts"] and GUIDES["Q2"]["optional_facts"]


@pytest.mark.parametrize("case_id", ["Q3", "Q9", "Q15"])
def test_safety_preconditions_and_order_are_not_relaxed(case_id):
    steps = ["先断开负载", "等待设备完全放电", "检查负载端是否短路", "确认负载正常", "按确认键清除告警", "重新执行上电流程"]
    assert CASES[case_id]["ordered_facts"] == CASES[case_id]["required_facts"] == steps
    assert all(span["page"] == 3 for span in CASES[case_id]["source_spans"])


def test_safety_negative_and_real_failure_challenges_remain():
    assert CASES["Q15"]["negative_response_fixture"]["expected_missing_facts"] == ["先断开负载", "等待设备完全放电"]
    assert CASES["Q8"]["category"] == "parallel_questions"
    assert CASES["Q14"]["category"] == "numeric_conflicting_premise"
    assert "15 A" in CASES["Q14"]["question"] and "50 ms" in CASES["Q14"]["question"]
    assert "fallback" in " ".join(GUIDES["Q8"]["behavior_criteria"])


def test_pronoun_fixture_contains_no_prefilled_assistant_gold():
    history = CASES["Q7"]["history_fixture"]
    assert len(history) == 1 and history[0]["role"] == "user"
    assert "PX-200" in history[0]["content"]
    assert "16 A" not in history[0]["content"] and "六个月" not in history[0]["content"]


def test_coverage_separates_primary_challenge_flow_and_abstention():
    coverage = RUBRICS["coverage"]
    primary, challenge = set(coverage["primary_case_ids"]), set(coverage["challenge_case_ids"])
    answerable = {case_id for case_id, case in CASES.items() if case["case_type"] == "answerable"}
    assert not primary & challenge and primary | challenge == answerable
    assert len(primary) == 13 and len(challenge) == 5 and len(answerable) == coverage["answerable_count"] == 18
    assert set(coverage["workflow_case_ids"]) == {"Q9", "Q10", "Q11", "Q12"}
    assert coverage["unanswerable_case_ids"] == ["Q13"]
    groups = coverage["knowledge_groups"]
    assert len(groups) == coverage["knowledge_group_count"] == 11
    assert len({group["group_id"] for group in groups}) == 11
    for group in groups:
        assert set(group["primary_case_ids"]).issubset(group["case_ids"])
        assert set(group["case_ids"]).issubset(CASES)
        for case_id in group["case_ids"]:
            assert group["group_id"] in GUIDES[case_id]["knowledge_group_ids"]
    assert set().union(*(set(group["case_ids"]) for group in groups)) == answerable | {"Q9", "Q10"}


@pytest.mark.parametrize("case_id", list(CASES))
def test_optional_facts_also_have_exact_pdf_provenance(case_id):
    path = ROOT / "backend/data/documents" / GOLD["source_document"]["document_id"] / "source.pdf"
    with fitz.open(path) as pdf:
        for optional in GUIDES[case_id]["optional_facts"]:
            assert optional["fact"] and optional["source_spans"]
            for span in optional["source_spans"]:
                assert normalized(span["source_quote"]) in normalized(pdf[span["page"] - 1].get_text())


def test_flow_entry_is_shared_and_failures_block_followup_claims():
    protocol = RUBRICS["flow_protocol"]
    entry = protocol["shared_entry"]
    assert entry["case_ids"] == ["Q9", "Q10", "Q11", "Q12"]
    assert entry["history_fixture"] == [] and not entry["retrieval_expected"]
    assert entry["expected_phase"] == "awaiting_clarification"
    assert "blocked_by_prerequisite" in entry["prerequisite_on_failure"]
    assert protocol["runner_compatibility"]["status"] == "workflow_runner_alignment_pending"
    for case_id in entry["case_ids"]:
        case = CASES[case_id]
        assert case["flow_steps"][0]["question"] == entry["question"]
        assert case["flow_steps"][0]["expected_pending_query"] == entry["expected_pending_query"]
        assert "blocked_by_prerequisite" in case["flow_expectation_basis"]


@pytest.mark.parametrize("fixture", STATES["states"], ids=lambda fixture: fixture["fixture_id"])
def test_synthetic_pending_start_is_a_legal_isolated_thread_state(fixture):
    values = {key: value for key, value in fixture.items() if key != "fixture_id"}
    state = ThreadState.model_validate({"thread_id": "calibration-isolated-test", **values})
    assert state.phase == "awaiting_clarification" and state.pending_query
    assert not state.recent_messages and not state.summary_backlog
    memory = ConversationMemory()
    current = memory.thread_state(state.thread_id)
    loaded = memory.update(state.thread_id, expected_version=current.state_version, **values)
    assert loaded.pending_query == state.pending_query and loaded.state_version == 1
    assert not memory.exists("another-isolated-thread")


@pytest.mark.parametrize("probe", STATES["probes"], ids=lambda probe: probe["probe_id"])
def test_focused_protocol_is_complete_without_claiming_it_was_executed(probe):
    assert probe["fixture_id"] in {state["fixture_id"] for state in STATES["states"]}
    action = probe["followup"]["action"]
    assert action in {"auto", "continue_clarification", "new_question", "cancel"}
    assert action == "cancel" or probe["followup"]["question"]
    expected = probe["expected"]
    assert expected["status"] in {"completed", "clarification", "cancelled"}
    assert expected["phase"] in {"idle", "awaiting_clarification"}
    if expected["status"] == "completed":
        assert expected["retrieval"] and expected["answer_rubric_case_id"] in CASES
        assert not expected["pending_query"] and not expected["pending_clarifications"]
    elif expected["status"] == "cancelled":
        assert action == "cancel" and not expected["retrieval"]
        assert expected["analysis_calls"] == expected["generation_calls"] == 0
        assert not expected["pending_query"] and not expected["pending_clarifications"]
    else:
        assert expected["pending_query"] and not expected["retrieval"]
        assert expected["offered_actions"] == ["continue_clarification", "new_question", "cancel"]


def test_focused_fixtures_are_draft_and_have_two_samples_per_family():
    assert Counter(probe["family"] for probe in STATES["probes"]) == {
        "supplement": 2, "new_question": 2, "cancel": 2, "uncertain": 2
    }
    for artifact in (GOLD, RUBRICS, STATES):
        assert artifact["status"] == "draft_not_for_formal_scoring"
    for artifact in (RUBRICS, STATES):
        assert artifact["review"] == {"status": "pending", "reviewer": None, "reviewed_at": None}


def test_abstention_and_judge_errors_are_not_disguised_as_accuracy():
    assert CASES["Q13"]["reference_answer"] is None
    assert CASES["Q13"]["absence_check"]["pages_checked"] == [1, 2, 3, 4]
    assert "invalid_json" in " ".join(GUIDES["Q13"]["behavior_criteria"])
    assert {lane["lane"] for lane in RUBRICS["reporting_lanes"]} == {"answer_quality", "workflow", "evaluation_runtime"}
    assert "不是 exact-match" in RUBRICS["interpretation"]["query_matching_policy"]

