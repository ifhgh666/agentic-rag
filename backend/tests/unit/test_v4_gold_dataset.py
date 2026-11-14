"""Read-only gold dataset gates; synthetic PDFs never touch the knowledge index."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

from scripts.validate_v4_gold_dataset import validate_dataset


@pytest.fixture
def gold_fixture(tmp_path):
    path = tmp_path / "source.pdf"
    with fitz.open() as pdf:
        pdf.new_page().insert_text((72, 72), "The threshold exceeds 16 A for 100 ms. Disconnect load first.")
        pdf.new_page().insert_text((72, 72), "Wait for complete discharge. Then inspect the load.")
        pdf.save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    case = {
        "case_id": "Q1", "case_type": "answerable", "category": "seed",
        "document_sha256": digest, "question": "What is the threshold?",
        "reference_answer": "The threshold exceeds 16 A for 100 ms.",
        "source_spans": [{"page": 1, "section": "Threshold", "source_quote": "The threshold exceeds 16 A for 100 ms."}],
        "required_facts": ["exceeds 16 A", "100 ms"], "forbidden_claims": ["15 A"],
        "expected_behavior": "answer", "review_status": "draft", "reviewer": None, "reviewed_at": None,
    }
    dataset = {
        "schema_version": 1, "dataset_version": "test-1", "status": "draft_not_for_formal_scoring",
        "source_document": {"document_id": "b8d6bda5-5ff7-4b2c-9e72-1157f199bf8b", "filename": "source.pdf",
                            "sha256": digest, "page_count": 2, "document_version": "test-only"},
        "cases": [case],
    }
    return dataset, path


def reviewed(dataset):
    value = copy.deepcopy(dataset)
    value["status"] = "reviewed"
    for case in value["cases"]:
        case.update(review_status="reviewed", reviewer="synthetic-test-reviewer",
                    reviewed_at="2026-10-02T12:00:00+08:00", review_kind="human")
    return value


def codes(report):
    return {error["code"] for error in report["errors"]}


def test_draft_can_be_checked_but_never_formally_scored(gold_fixture):
    dataset, pdf = gold_fixture
    original = copy.deepcopy(dataset)
    report = validate_dataset(dataset, pdf)
    assert report["valid"] and report["quotes_matched"] == 1
    assert not report["formal_ready"] and report["eligible_case_ids"] == []
    assert report["unreviewed_case_ids"] == ["Q1"] and dataset == original
    formal = validate_dataset(dataset, pdf, require_reviewed=True)
    assert not formal["valid"] and "review_required" in codes(formal)


def test_reviewed_matching_pdf_is_eligible(gold_fixture):
    dataset, pdf = gold_fixture
    report = validate_dataset(reviewed(dataset), pdf, require_reviewed=True)
    assert report["valid"] and report["formal_ready"]
    assert report["eligible_case_ids"] == ["Q1"]


@pytest.mark.parametrize("mutate", [
    lambda data: data["cases"][0].update(case_type="invented"),
    lambda data: data["cases"][0].update(question=" "),
    lambda data: data["cases"][0].update(reference_answer=""),
    lambda data: data["cases"][0].update(source_spans=[]),
    lambda data: data["cases"][0].update(required_facts=[]),
    lambda data: data["source_document"].update(sha256="not-a-hash"),
    lambda data: data["cases"][0].update(expected_behavior="cancelled"),
])
def test_invalid_schema_is_rejected(gold_fixture, mutate):
    dataset, pdf = gold_fixture
    mutate(dataset)
    assert "schema_invalid" in codes(validate_dataset(dataset, pdf))


@pytest.mark.parametrize("change", [
    {"reviewer": None}, {"reviewed_at": None}, {"review_kind": "automated"},
    {"reviewed_at": "2026-10-02T12:00:00"},
])
def test_reviewed_requires_explicit_human_record(gold_fixture, change):
    dataset, pdf = gold_fixture
    dataset = reviewed(dataset)
    dataset["cases"][0].update(change)
    assert "schema_invalid" in codes(validate_dataset(dataset, pdf))


def test_duplicate_case_ids_are_rejected(gold_fixture):
    dataset, pdf = gold_fixture
    dataset["cases"].append(copy.deepcopy(dataset["cases"][0]))
    assert "duplicate_case_id" in codes(validate_dataset(dataset, pdf))


def test_pdf_replacement_is_rejected_without_changing_dataset(gold_fixture, tmp_path):
    dataset, original_pdf = gold_fixture
    replacement = tmp_path / "replacement.pdf"
    with fitz.open(original_pdf) as pdf:
        pdf[0].insert_text((72, 150), "Different document revision.")
        pdf.save(replacement)
    assert "document_hash_mismatch" in codes(validate_dataset(reviewed(dataset), replacement, require_reviewed=True))


def test_case_hash_and_document_identity_must_match(gold_fixture):
    dataset, pdf = gold_fixture
    dataset["cases"][0]["document_sha256"] = "0" * 64
    assert "case_document_mismatch" in codes(validate_dataset(dataset, pdf))
    dataset["cases"][0]["document_sha256"] = dataset["source_document"]["sha256"]
    dataset["cases"][0]["document_id"] = "00000000-0000-0000-0000-000000000000"
    assert "case_document_mismatch" in codes(validate_dataset(dataset, pdf))


@pytest.mark.parametrize("page,quote,code", [
    (3, "The threshold exceeds 16 A for 100 ms.", "page_out_of_range"),
    (2, "The threshold exceeds 16 A for 100 ms.", "quote_not_found"),
    (1, "The threshold exceeds 15 A for 100 ms.", "quote_not_found"),
    (1, "The threshold exceeds 16 A for 100 ms!", "quote_not_found"),
])
def test_quotes_must_match_the_stated_page_not_a_different_page(gold_fixture, page, quote, code):
    dataset, pdf = gold_fixture
    dataset["cases"][0]["source_spans"][0].update(page=page, source_quote=quote)
    assert code in codes(validate_dataset(dataset, pdf))


def test_pdf_layout_whitespace_can_be_normalized(gold_fixture):
    dataset, pdf = gold_fixture
    dataset["cases"][0]["source_spans"][0]["source_quote"] = "The threshold exceeds\n16 A for 100 ms."
    assert validate_dataset(dataset, pdf)["valid"]


def test_page_count_is_part_of_document_identity(gold_fixture):
    dataset, pdf = gold_fixture
    dataset["source_document"]["page_count"] = 99
    assert "page_count_mismatch" in codes(validate_dataset(dataset, pdf))


def unanswerable(dataset):
    case = dataset["cases"][0]
    case.update(case_type="unanswerable", question="Where is the firmware download?", reference_answer=None,
                source_spans=[], required_facts=[], expected_behavior="insufficient_evidence",
                unanswerable_reason="All pages lack firmware download instructions.",
                absence_check={"pages_checked": [1, 2], "terms": ["firmware", "download"]})


def test_unanswerable_requires_full_document_absence_record(gold_fixture):
    dataset, pdf = gold_fixture
    unanswerable(dataset)
    assert validate_dataset(dataset, pdf)["valid"]
    dataset["cases"][0]["absence_check"]["pages_checked"] = [1]
    assert "absence_review_incomplete" in codes(validate_dataset(dataset, pdf))


def test_absence_search_cannot_hide_existing_terms(gold_fixture):
    dataset, pdf = gold_fixture
    unanswerable(dataset)
    dataset["cases"][0]["absence_check"]["terms"] = ["16 A"]
    assert "absence_term_found" in codes(validate_dataset(dataset, pdf))


def test_unanswerable_cannot_contain_a_factual_reference(gold_fixture):
    dataset, pdf = gold_fixture
    unanswerable(dataset)
    dataset["cases"][0]["reference_answer"] = "Visit an invented download site."
    assert "schema_invalid" in codes(validate_dataset(dataset, pdf))


def test_ordered_safety_facts_cannot_be_reversed(gold_fixture):
    dataset, pdf = gold_fixture
    case = dataset["cases"][0]
    case["ordered_facts"] = ["Disconnect load first", "Wait for complete discharge"]
    case["required_facts"] = list(case["ordered_facts"])
    case["reference_answer"] = "Wait for complete discharge. Disconnect load first."
    assert "ordered_facts_invalid" in codes(validate_dataset(dataset, pdf))


def test_interaction_fixture_requires_explicit_actions_and_transitions(gold_fixture):
    dataset, pdf = gold_fixture
    case = dataset["cases"][0]
    case.update(case_type="clarification_flow", question="Which equipment?", reference_answer=None,
                source_spans=[], required_facts=[], expected_behavior="cancelled",
                flow_expectation_basis="Stage B protocol, not PDF facts.",
                flow_steps=[{"question": "Which equipment?", "action": "auto", "expected_status": "clarification",
                             "expected_relation": "new_question", "expected_pending_query": "Which equipment?"},
                            {"question": "", "action": "cancel", "expected_status": "cancelled"}])
    assert validate_dataset(dataset, pdf)["valid"]
    case["flow_steps"][1]["action"] = "invalid"
    assert "schema_invalid" in codes(validate_dataset(dataset, pdf))


def test_cli_is_read_only_and_enforces_review_gate(gold_fixture, tmp_path):
    dataset, pdf = gold_fixture
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")
    before = {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in [path, pdf]}
    command = [sys.executable, "-m", "scripts.validate_v4_gold_dataset", "--dataset", str(path), "--pdf", str(pdf), "--json"]
    check = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert check.returncode == 0 and json.loads(check.stdout)["valid"]
    formal = subprocess.run([*command, "--require-reviewed"], capture_output=True, text=True, encoding="utf-8")
    assert formal.returncode == 1 and not json.loads(formal.stdout)["formal_ready"]
    assert before == {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in [path, pdf]}


def test_candidate_covers_seed_questions_and_ten_different_scenarios():
    path = Path(__file__).resolve().parents[3] / "specs/004-query-clarification-ragas/gold-cases-v1.json"
    if not path.is_file():
        pytest.skip("历史题集需要本地 Spec Kit 归档")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    assert {f"Q{i}" for i in range(1, 6)}.issubset({case["case_id"] for case in dataset["cases"]})
    extra = [case for case in dataset["cases"] if case["case_id"] not in {f"Q{i}" for i in range(1, 6)}]
    assert len(extra) >= 10 and len({case["category"] for case in extra}) >= 10
    for case in dataset["cases"]:
        if case["review_status"] == "draft":
            assert case["reviewer"] is None and case["reviewed_at"] is None
        else:
            assert case["review_kind"] == "human" and case["reviewer"] and case["reviewed_at"]
    if any(case["review_status"] == "draft" for case in dataset["cases"]):
        assert not validate_dataset(dataset, require_reviewed=True)["formal_ready"]


def test_invalid_json_and_missing_pdf_are_reported(gold_fixture, tmp_path):
    dataset, _ = gold_fixture
    assert "pdf_unreadable" in codes(validate_dataset(dataset, tmp_path / "missing.pdf"))
    path = tmp_path / "broken.json"
    path.write_text("not json", encoding="utf-8")
    check = subprocess.run([sys.executable, "-m", "scripts.validate_v4_gold_dataset", "--dataset", str(path), "--json"],
                           capture_output=True, text=True, encoding="utf-8")
    assert check.returncode == 2
    assert json.loads(check.stdout)["errors"][0]["code"] == "dataset_unreadable"


def test_mixed_review_does_not_silently_skip_unreviewed_cases(gold_fixture):
    dataset, pdf = gold_fixture
    value = reviewed(dataset)
    unreviewed = copy.deepcopy(dataset["cases"][0])
    unreviewed["case_id"] = "Q2"
    value["cases"].append(unreviewed)
    report = validate_dataset(value, pdf, require_reviewed=True)
    assert not report["formal_ready"] and not report["valid"]
    assert report["unreviewed_case_ids"] == ["Q2"] and report["eligible_case_ids"] == []
