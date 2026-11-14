import asyncio
import copy
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.evaluate_v4_ragas import (
    METRIC_NAMES, LocalMeter, capture_graph_result, evaluate_record, prepare_evaluation, validate_local_base_url,
)


def record(case_type="answerable"):
    return {"case_id": "Q1", "case_type": case_type, "user_input": "保留多久？",
            "response": "默认保留三年。", "reference": "默认保留三年。",
            "retrieved_contexts": ["候选一", "候选二"],
            "generation_contexts": ["用于生成的三年原文"], "run_error": None}


class Scorer:
    def __init__(self, value=0.75, error=False):
        self.value, self.error, self.inputs = value, error, []

    async def ascore(self, **kwargs):
        self.inputs.append(kwargs)
        if self.error:
            raise RuntimeError("私密异常不能泄露到评估报告")
        return SimpleNamespace(value=self.value, reason="test")


def test_five_metrics_keep_retrieval_order_and_actual_generation_contexts():
    scorers = {name: Scorer() for name in METRIC_NAMES}
    row = record()
    before = copy.deepcopy(row)
    result = asyncio.run(evaluate_record(row, scorers, timeout=1))
    assert row == before and set(result["metrics"]) == set(METRIC_NAMES)
    assert all(metric["value"] == 0.75 for metric in result["metrics"].values())
    assert scorers["context_precision"].inputs[0]["retrieved_contexts"] == row["retrieved_contexts"]
    assert scorers["response_groundedness"].inputs[0]["retrieved_contexts"] == row["generation_contexts"]


@pytest.mark.parametrize("case_type", ["unanswerable", "clarification_flow"])
def test_interaction_and_unanswerable_are_not_scored_as_zero(case_type):
    scorer = Scorer()
    result = asyncio.run(evaluate_record(record(case_type), {name: scorer for name in METRIC_NAMES}))
    assert scorer.inputs == []
    assert all(item["status"] == "not_applicable" and item["value"] is None
               and item["not_applicable_reason"] for item in result["metrics"].values())


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -1, 1.1, True])
def test_invalid_scores_never_become_valid_zero(value):
    result = asyncio.run(evaluate_record(record(), {name: Scorer(value) for name in METRIC_NAMES}))
    assert all(item["status"] == "evaluation_error" and item["value"] is None for item in result["metrics"].values())


def test_judge_errors_are_saved_per_metric():
    result = asyncio.run(evaluate_record(record(), {name: Scorer(error=True) for name in METRIC_NAMES}))
    assert all(item["evaluation_error"] == "RuntimeError" for item in result["metrics"].values())
    assert "私密异常" not in str(result)


def test_pipeline_failure_does_not_call_judge():
    row = record()
    row["run_error"] = "PIPELINE_FAILED"
    scorers = {name: Scorer() for name in METRIC_NAMES}
    result = asyncio.run(evaluate_record(row, scorers))
    assert all(not scorer.inputs for scorer in scorers.values())
    assert all(item["status"] == "evaluation_error" for item in result["metrics"].values())


def test_empty_evidence_is_not_filled_from_reference():
    row = record()
    row.update(retrieved_contexts=[], generation_contexts=[])
    scorers = {name: Scorer() for name in METRIC_NAMES}
    result = asyncio.run(evaluate_record(row, scorers))
    assert result["metrics"]["answer_accuracy"]["status"] == "scored"
    assert result["metrics"]["context_recall"]["status"] == "not_applicable"
    assert result["generation_contexts"] == []


@pytest.mark.parametrize("url", ["https://api.openai.com/v1", "http://example.com/v1", "http://127.0.0.1.evil/v1",
                                  "http://user:pass@127.0.0.1:11434/v1", "http://127.0.0.1:11434/v1?token=x"])
def test_judge_is_loopback_only(url):
    with pytest.raises(ValueError):
        validate_local_base_url(url)


def test_local_url_is_normalized():
    assert validate_local_base_url("http://localhost:11434/v1/") == "http://127.0.0.1:11434/v1/"


def test_draft_gate_runs_before_any_judge_or_capture_import():
    gate = Mock(return_value={"valid": False, "formal_ready": False, "errors": [{"code": "review_required"}]})
    with pytest.raises(ValueError, match="review_required"):
        prepare_evaluation({"cases": []}, {}, validator=gate)
    gate.assert_called_once()


def capture_fixture(tmp_path):
    document_id = "b8d6bda5-5ff7-4b2c-9e72-1157f199bf8b"
    source_dir = tmp_path / "documents" / document_id
    source_dir.mkdir(parents=True)
    source = source_dir / "source.pdf"
    source.write_bytes(b"synthetic-pdf-for-snapshot-tests-only")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    snapshot = [{"document_id": document_id, "source_sha256": source_hash}]
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode()).hexdigest()
    (tmp_path / "documents.json").write_text(json.dumps([
        {"document_id": document_id, "status": "ready", "source_path": str(source)},
    ]), encoding="utf-8")
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    manifest = index_dir / "manifest.json"
    manifest.write_text(json.dumps({"signature": {}, "documents_sha256": digest}), encoding="utf-8")
    index_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    dataset = {"dataset_version": "synthetic-1", "status": "reviewed",
               "source_document": {"document_id": document_id, "filename": "source.pdf", "sha256": source_hash,
                                   "page_count": 1, "document_version": "test"}, "cases": [{
                   "case_id": "Q1", "document_sha256": source_hash, "case_type": "answerable", "question": "多久？",
                   "reference_answer": "三年", "required_facts": ["三年"], "expected_behavior": "answer",
                   "source_spans": [{"page": 1, "section": "test", "source_quote": "三年"}],
                   "review_status": "reviewed", "reviewer": "synthetic-test-reviewer", "review_kind": "human",
                   "reviewed_at": "2026-10-02T12:00:00+08:00",
               }]}
    result = SimpleNamespace(retrieved_results=[], retrieval_batches=[{"query": "多久？", "results": [
        {"content": "候选一"}, {"content": "候选二"}]}], request_id="r", thread_id="synthetic-thread",
        rewritten_query="多久？", questions=["多久？"], final_answer="三年", status="completed", context="unused",
        context_messages=[{"content": "实际生成上下文", "raw_text": "实际原文"}],
        sources=[], usage={"model_calls": 2, "cloud_calls": 0}, model_trace=[])
    capture = {"schema_version": 1, "capture_kind": "graph_run", "dataset_version": "synthetic-1",
               "document_sha256": source_hash, "index_manifest_sha256": index_hash.upper(),
               "index_version": index_hash, "answer_provider": "ollama", "answer_model": "test",
               "cases": [capture_graph_result(dataset["cases"][0], result, index_version=index_hash, answer_model="test")]}
    validator = Mock(return_value={"valid": True, "formal_ready": True})
    return dataset, capture, manifest, source, validator


def test_actual_graph_capture_keeps_two_context_layers_and_snapshot(tmp_path):
    dataset, capture, manifest, _, validator = capture_fixture(tmp_path)
    rows = prepare_evaluation(dataset, capture, manifest_path=manifest, validator=validator)
    assert rows[0]["response"] == "三年"
    assert rows[0]["retrieved_contexts"] == ["候选一", "候选二"]
    assert rows[0]["generation_contexts"] == ["实际生成上下文"]
    assert rows[0]["reference"] == "三年"
    assert rows[0]["human_review"]["status"] == "pending"


@pytest.mark.parametrize("change", ["case_set", "model", "history", "contexts", "cloud", "index", "pdf"])
def test_mismatched_capture_is_rejected(tmp_path, change):
    dataset, capture, manifest, source, validator = capture_fixture(tmp_path)
    row = capture["cases"][0]
    if change == "case_set":
        capture["cases"].append(copy.deepcopy(row))
    elif change == "model":
        row["answer_model"] = "changed-model"
    elif change == "history":
        row["history_fixture"] = [{"role": "user", "content": "changed"}]
    elif change == "contexts":
        row["retrieved_contexts"].reverse()
    elif change == "cloud":
        row["answer_cost"]["cloud_calls"] = 1
    elif change == "index":
        manifest.write_text("{}", encoding="utf-8")
    else:
        source.write_bytes(b"new-revision")
    with pytest.raises(ValueError):
        prepare_evaluation(dataset, capture, manifest_path=manifest, validator=validator)


def test_metric_timeout_is_error_not_zero():
    class SlowScorer:
        async def ascore(self, **kwargs):
            await asyncio.sleep(0.1)
    result = asyncio.run(evaluate_record(record(), {name: SlowScorer() for name in METRIC_NAMES}, timeout=0.001))
    assert all(item["evaluation_error"] == "TimeoutError" and item["value"] is None
               for item in result["metrics"].values())


def test_transport_budget_and_usage_are_measured_not_estimated():
    import httpx
    async def check():
        meter = LocalMeter("http://127.0.0.1:11434/v1", 1)
        await meter.request(httpx.Request("GET", "http://127.0.0.1:11434/api/tags"))
        assert meter.calls == 0
        request = httpx.Request("POST", "http://127.0.0.1:11434/v1/chat/completions")
        await meter.request(request)
        await meter.response(httpx.Response(200, request=request, json={"usage": {"prompt_tokens": 12, "completion_tokens": 3}}))
        assert meter.difference()["total_tokens"] == 15
        assert meter.difference()["model_calls"] == 1
        with pytest.raises(RuntimeError):
            await meter.request(request)
        with pytest.raises(ValueError):
            await meter.request(httpx.Request("POST", "http://example.com/v1/chat/completions"))
    asyncio.run(check())


def test_metric_progress_reports_only_result_metadata():
    events = []
    result = asyncio.run(evaluate_record(record(), {name: Scorer() for name in METRIC_NAMES}, progress=events.append))
    assert len(events) == 5
    assert [event["metric"] for event in events] == list(METRIC_NAMES)
    assert all(event["event"] == "metric_complete" and "response" not in event for event in events)
    assert all(event["status"] == result["metrics"][event["metric"]]["status"] for event in events)


def test_exhausted_batch_budget_does_not_attempt_more_scoring_calls():
    meter = LocalMeter("http://127.0.0.1:11434/v1/", 1)
    meter.calls = 1
    scorers = {name: Scorer() for name in METRIC_NAMES}
    result = asyncio.run(evaluate_record(record(), scorers, meter=meter))
    assert all(not scorer.inputs for scorer in scorers.values())
    assert all(metric["evaluation_error"] == "judge_call_budget_exceeded" and metric["value"] is None
               for metric in result["metrics"].values())
