"""保留固定反例；引文定位通过不代表步骤完整，缺失由独立质量探针揭示。"""

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from app.config import Settings
from app.core.answering import (
    AnswerEvaluator,
    format_evidence_records,
    AnswerGenerator,
    INSUFFICIENT_ANSWER,
)
from scripts.replay_v3_6_q3 import (
    DEFAULT_CASE,
    BoundedCaptureProvider,
    FixedResponseProvider,
    clone_index_readonly,
    digest,
    inspect_q3_steps,
    replay_counterexample,
    validate_local_capture_settings,
    validate_sparse_query_scope,
)


def case_data():
    return json.loads(DEFAULT_CASE.read_text(encoding="utf-8"))


def test_valid_short_table_quote_does_not_trigger_program_raw_procedure_replacement():
    replay = replay_counterexample(case_data())
    assert "先断开负载" in replay["model_calls"][0]["messages"][-1]["content"]
    assert "完全放电" in replay["model_calls"][0]["messages"][-1]["content"]
    assert replay["validation_status"] == "accepted"
    assert replay["step_probe"]["missing_steps"] == ["disconnect_load", "wait_discharge"]
    assert replay["counterexample_reproduced"] is True
    assert replay["live_model_calls"] == 0


def test_current_evaluator_does_not_repeat_historical_false_high_score():
    case = case_data()
    records = format_evidence_records(case["records"])
    incomplete = case["counterexample"]["model_response"]["answer"]
    verification = AnswerEvaluator().evaluate(case["question"], incomplete, "\n".join(r["content"] for r in records), records=records)
    assert verification.completeness_status == "not_evaluated"
    assert "overall_score" not in verification.model_dump()


def test_citation_text_cannot_hide_omission_from_answer_body():
    case = case_data()
    answer = case["counterexample"]["model_response"]["answer"]
    full_quote = case["records"][0]["raw_text"]
    probe = inspect_q3_steps(f"{answer}\n\n依据：\n- “{full_quote}”", case)
    assert probe["missing_steps"] == ["disconnect_load", "wait_discharge"]


def test_order_probe_catches_reversed_safety_steps():
    probe = inspect_q3_steps("完全放电后断开负载，检查短路，按确认键，然后重新上电。", case_data())
    assert not probe["missing_steps"]
    assert probe["ordered"] is False


def test_full_flow_with_detail_citation_is_a_positive_control():
    case = case_data()
    records = format_evidence_records(case["records"])
    quote = "应先断开负载，等待设备完全放电，再检查负载端是否短 路。确认负载正常后，按确认键清除告警，最后重新执行上电流程。"
    response = {"is_answerable": True, "answer": quote, "citations": [{"citation_id": "E1", "quote": quote}], "conflict": False,
                "procedure_unit_ids": ["E1.P1"]}
    provider = FixedResponseProvider(response)
    generator = AnswerGenerator(Settings(_env_file=None), provider)
    answer, ids, trace = generator.generate_grounded_with_result(case["question"], records, procedure_required=True)
    probe = inspect_q3_steps(answer, case)
    assert not probe["missing_steps"] and probe["ordered"]
    assert ids == ["E1"] and trace["validation_status"] == "accepted"
    verification = AnswerEvaluator().evaluate(case["question"], answer, "\n\n".join(r["content"] for r in records), records=records)
    assert verification.completeness_status == "not_evaluated"


def test_missing_steps_are_visible_quality_failure_without_false_complete_verification():
    replay = replay_counterexample(case_data())
    assert replay["step_probe"]["missing_steps"]
    assert replay["verification"]["completeness_status"] == "not_evaluated"


@pytest.mark.parametrize("changes", [
    {"llm_provider": "openai_compatible"},
    {"ollama_base_url": "http://example.com:11434"},
    {"ollama_base_url": "http://user:pass@127.0.0.1:11434"},
    {"ollama_base_url": "http://127.0.0.1:11434/?x=1"},
    {"embedding_backend": "deterministic"},
    {"sparse_model": "other/sparse-model"},
])
def test_capture_guard_rejects_nonlocal_or_changed_embedding(changes):
    settings = Settings(_env_file=None, ollama_model="qwen3:4b-instruct", sparse_offline_fallback=True)
    with pytest.raises(ValueError):
        validate_local_capture_settings(settings.model_copy(update=changes))


def test_fixture_is_utf8_and_keeps_real_parent_records_when_available():
    case = case_data()
    assert case["expected_sequence"][0]["description"] == "先断开负载"
    assert "\ufffd" not in DEFAULT_CASE.read_text(encoding="utf-8")
    # Pure tests can run on another machine without this user's formal data.
    parents = Path(__file__).resolve().parents[2] / "data/parents.json"
    if parents.is_file():
        actual = {item["parent_id"]: item for item in json.loads(parents.read_text(encoding="utf-8"))}
        for record in case["records"]:
            if record["parent_id"] in actual:
                assert actual[record["parent_id"]]["text"] == record["raw_text"]


def test_replay_does_not_mutate_fixture():
    case = case_data()
    before = copy.deepcopy(case)
    replay_counterexample(case)
    assert case == before


def test_snapshot_copies_existing_sqlite_without_modifying_source(tmp_path, monkeypatch):
    production = tmp_path / "production"
    output = tmp_path / "diagnostics"
    monkeypatch.setattr("scripts.replay_v3_6_q3.OUTPUT_ROOT", output)
    for name in ("documents.json", "parents.json", "children.json", "index/children.json", "index/manifest.json"):
        path = production / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")
    db = production / "qdrant/collection/children/storage.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE example (value TEXT)")
        connection.execute("INSERT INTO example VALUES ('existing-vector')")
    lock = production / "qdrant/.lock"
    lock.write_text("do-not-copy", encoding="utf-8")
    before = digest(db)
    target = output / "run"
    clone_index_readonly(Settings(_env_file=None, data_dir=production, qdrant_db_path=production / "qdrant"), target)
    assert digest(db) == before
    with sqlite3.connect(target / "qdrant/collection/children/storage.sqlite") as connection:
        assert connection.execute("SELECT value FROM example").fetchall() == [("existing-vector",)]
    assert not (target / "qdrant/.lock").exists()


def test_snapshot_rejects_target_outside_diagnostic_root(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.replay_v3_6_q3.OUTPUT_ROOT", tmp_path / "diagnostics")
    with pytest.raises(ValueError, match="快照必须"):
        clone_index_readonly(Settings(_env_file=None), tmp_path / "outside")
    assert not (tmp_path / "outside").exists()


def test_local_diagnostic_cannot_issue_more_than_two_calls():
    delegate = FixedResponseProvider({"ok": True})
    bounded = BoundedCaptureProvider(delegate)
    messages = [{"role": "user", "content": "本机测试"}]
    bounded.complete(messages)
    bounded.complete(messages)
    with pytest.raises(RuntimeError, match="两次"):
        bounded.complete(messages)
    assert len(delegate.calls) == 2


def test_offline_sparse_scope_allows_literal_model_but_not_english_prose():
    validate_sparse_query_scope("AB-300 的阈值是多少？")
    validate_sparse_query_scope("设备多久维护？")
    with pytest.raises(ValueError, match="一般英文"):
        validate_sparse_query_scope("How to recover AB-300?")


def test_saved_observation_matches_actual_capture_when_available():
    root = Path(__file__).resolve().parents[3]
    observation = json.loads((root / "specs/003-v3-ollama-rag-quality/v3-6-q3-observation.json").read_text(encoding="utf-8"))
    raw = root / observation["raw_capture"]
    if not raw.is_file():
        pytest.skip("完整运行记录为本机临时产物；固定反例仍可独立重放")
    assert digest(raw) == observation["raw_capture_sha256"]
    actual = json.loads(raw.read_text(encoding="utf-8"))
    assert observation["response"] == actual["response"]
    assert observation["request_id"] == actual["request_id"]
    assert observation["raw_model_answer_json"] == json.loads(actual["model_calls"][-1]["response"]["content"])
    assert observation["detail_fragment_in_actual_generator_input"] in actual["model_calls"][-1]["messages"][-1]["content"]
    assert observation["verification"] == actual["verification"]
    assert [row["child_id"] for row in observation["retrieval_ranking"]] == [row["child_id"] for row in actual["retrieval_batches"][0]["results"]]
    assert [row["record_id"] for row in observation["generation_records"]] == [row["record_id"] for row in actual["generation_records"]]
    assert observation["usage"]["total_tokens"] == actual["answer_cost"]["total_tokens"]
    assert observation["protected_files_unchanged"] == actual["protected_files_unchanged"]
