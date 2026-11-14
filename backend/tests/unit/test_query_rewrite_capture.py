"""Capture safety tests use a scripted provider; no real model or index."""
import json
import hashlib
from pathlib import Path

import pytest

from app.config import Settings
from app.core.model_provider import ModelResult
from scripts.capture_query_rewrite_v1 import ENTRANCE_ORDER, capture_run, load_cases


FIXTURE = Path(__file__).parents[1] / "fixtures/query_rewrite_v1_cases.json"


class ScriptedProvider:
    def __init__(self, contents):
        self.contents = iter(contents)
        self.messages = []
        self.timeouts = []
        self.response_schemas = []

    def complete(self, messages, *, timeout_seconds=None, response_schema=None):
        self.messages.append(messages)
        self.timeouts.append(timeout_seconds)
        self.response_schemas.append(response_schema)
        value = next(self.contents)
        if isinstance(value, Exception):
            raise value
        return ModelResult(value, "ollama", "qwen3:4b-instruct", 100, 20)


def local_settings():
    return Settings(_env_file=None, llm_provider="ollama", ollama_model="qwen3:4b-instruct",
                    llm_timeout_seconds=120, request_timeout_seconds=300)


def review(status="passed", rationale="Manually inspected the fixed rubric."):
    return {"status": status, "reviewer": "test_manual_stub", "rationale": rationale}


def clear(question):
    return json.dumps({"is_clear": True, "questions": [question], "clarification_needed": ""}, ensure_ascii=False)


def test_frozen_order_and_fixture_rejected_before_any_call(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert tuple(item["id"] for item in load_cases(FIXTURE)["selected_cases"]) == ENTRANCE_ORDER
    data["real_entrance_order"].reverse()
    changed = tmp_path / "wrong.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    provider = ScriptedProvider([])
    with pytest.raises(ValueError, match="frozen_order"):
        capture_run(cases_path=changed, output=tmp_path / "run", settings=local_settings(),
                    provider=provider, reviewer=lambda *_: review())
    assert not provider.messages and not (tmp_path / "run").exists()


def test_manual_failure_stops_and_preserves_first_output_without_gold_input(tmp_path):
    provider = ScriptedProvider([clear("PN8733 的启动电压是多少？"), clear("ZX-900 的报警阈值是多少？")])
    reviewed = []

    def inspect(record, case):
        reviewed.append(case["id"])
        assert (tmp_path / "run" / f"{case['id']}.raw.json").is_file()
        return review("failed" if len(reviewed) == 2 else "passed", "Semantic failure in the second case.")

    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=local_settings(),
                          provider=provider, reviewer=inspect)
    assert reviewed == ["RW01", "RW02"] and len(provider.messages) == 2
    assert [item["status"] for item in summary["cases"]] == ["passed", "failed"] + ["not_run"] * 15
    assert summary["model_calls"] == 2 and summary["stop_case"] == "RW02"
    one = json.loads((tmp_path / "run/RW01.raw.json").read_text(encoding="utf-8"))
    assert one["raw_output"] == clear("PN8733 的启动电压是多少？")
    assert one["model_call_id"] and one["request_id"] and one["thread_id"]
    assert one["usage"]["usage_source"] == "provider" and one["usage"]["total_tokens"] == 120
    assert one["usage"]["model_calls"] == 1 and one["usage"]["cloud_calls"] == 0
    assert one["context_source"]["kind"] == "frozen_fixture"
    assert all(0 < timeout <= 120 for timeout in provider.timeouts)
    sent = json.dumps(provider.messages, ensure_ascii=False)
    assert "clarification_needed" not in provider.messages[0][0]["content"]
    assert set(provider.response_schemas[0].model_json_schema()["properties"]) == {
        "is_clear", "questions", "clarification_needed",
    }
    assert "expected" not in sent and "test_manual_stub" not in sent
    assert "本轮最多处理三个独立需求，请选择启动电压" not in sent


@pytest.mark.parametrize("content,reason", [("not JSON", "invalid_model_output"),
                                             (TimeoutError("private failure"), "timeout")])
def test_protocol_or_timeout_stops_without_review_retry_or_sensitive_error(tmp_path, content, reason):
    provider = ScriptedProvider([content])
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=local_settings(),
                          provider=provider, reviewer=lambda *_: pytest.fail("Must not review a failed protocol"))
    assert summary["stop_reason"] == reason and len(provider.messages) == 1
    assert all(item["status"] == "not_run" for item in summary["cases"][1:])
    raw = (tmp_path / "run/RW01.raw.json").read_text(encoding="utf-8")
    assert "private failure" not in raw
    assert json.loads(raw)["failure_reason"] == reason


def test_refuses_existing_output_before_call_even_if_empty(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    (output / "evidence.txt").write_text("first evidence", encoding="utf-8")
    provider = ScriptedProvider([])
    with pytest.raises(FileExistsError):
        capture_run(cases_path=FIXTURE, output=output, settings=local_settings(),
                    provider=provider, reviewer=lambda *_: review())
    assert not provider.messages and (output / "evidence.txt").read_text() == "first evidence"


@pytest.mark.parametrize("decision", [None, {"status": "passed"}, review("uncertain")])
def test_missing_invalid_or_uncertain_manual_review_cannot_start_next_case(tmp_path, decision):
    provider = ScriptedProvider([clear("PN8733 的启动电压是多少？")])
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=local_settings(),
                          provider=provider, reviewer=lambda *_: decision)
    assert summary["status"] == "stopped" and summary["cases"][0]["status"] != "passed"
    assert len(provider.messages) == 1 and not (tmp_path / "run/RW02.attempt.json").exists()


def test_full_scripted_run_has_separate_context_and_no_pending_leak(tmp_path):
    selected = load_cases(FIXTURE)["selected_cases"]
    provider = ScriptedProvider([clear(item["question"]) for item in selected])
    fixture_before = FIXTURE.read_bytes()
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=local_settings(),
                          provider=provider, reviewer=lambda *_: review())
    assert summary["status"] == "completed" and summary["model_calls"] == 17
    assert len({item["request_id"] for item in summary["cases"]}) == 17
    assert len({item["thread_id"] for item in summary["cases"]}) == 17
    assert FIXTURE.read_bytes() == fixture_before
    assert "MN-42" in provider.messages[9][1]["content"]
    assert "上电前检查哪些内容？" in provider.messages[9][1]["content"]
    assert "过流保护后如何恢复？" not in provider.messages[-1][1]["content"]
    assert "40 ms" in provider.messages[15][1]["content"] and "400 ms" in provider.messages[15][1]["content"]
    # Stub reviewers exercise the gate, not the semantic quality of these outputs.


@pytest.mark.parametrize("changes", [{"llm_provider": "fake"}, {"llm_provider": "openai_compatible"},
                                     {"llm_timeout_seconds": 121}, {"ollama_model": "another-model"}])
def test_unapproved_provider_model_or_wait_rejected_before_call(tmp_path, changes):
    settings = local_settings().model_copy(update=changes)
    provider = ScriptedProvider([])
    with pytest.raises(ValueError):
        capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=settings,
                    provider=provider, reviewer=lambda *_: review())
    assert not provider.messages and not (tmp_path / "run").exists()


def stopped_run_and_addendum(tmp_path):
    prior = tmp_path / "prior"
    selected = load_cases(FIXTURE)["selected_cases"]
    provider = ScriptedProvider([clear(item["question"]) for item in selected[:3]])
    capture_run(cases_path=FIXTURE, output=prior, settings=local_settings(), provider=provider,
                reviewer=lambda _, case: review("failed" if case["id"] == "RW03" else "passed"))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    amendment = {"source_run": str(prior), "source_summary_sha256": digest(prior / "summary.json"),
                 "human_authorization": "Explicit synthetic authorization for this capture safety test.",
                 "reviews": [{**review(), "case_id": "RW03", "raw_sha256": digest(prior / "RW03.raw.json"),
                              "review_sha256": digest(prior / "RW03.review.json")}]}
    addendum = tmp_path / "addendum.json"
    addendum.write_text(json.dumps(amendment), encoding="utf-8")
    return prior, addendum


def test_continuation_runs_only_remaining_first_outputs_and_preserves_old_records(tmp_path):
    prior, addendum = stopped_run_and_addendum(tmp_path)
    before = {p.name: p.read_bytes() for p in prior.iterdir()}
    selected = load_cases(FIXTURE)["selected_cases"][3:]
    provider = ScriptedProvider([clear(item["question"]) for item in selected])
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "continued", settings=local_settings(),
                          provider=provider, reviewer=lambda *_: review(), resume_from=prior, review_addendum=addendum)
    assert summary["status"] == "completed" and summary["model_calls"] == 14
    assert [item["id"] for item in summary["cases"]] == list(ENTRANCE_ORDER[3:])
    assert len(provider.messages) == 14 and not (tmp_path / "continued/RW03.raw.json").exists()
    manifest = json.loads((tmp_path / "continued/manifest.json").read_text(encoding="utf-8"))
    assert manifest["config"]["batch_model_call_limit"] == 14
    assert [item["case_id"] for item in manifest["continuation"]["reused_first_outputs"]] == ["RW01", "RW02", "RW03"]
    assert manifest["continuation"]["reused_first_outputs"][2]["original_status"] == "failed"
    assert all(p.read_bytes() == before[p.name] for p in prior.iterdir())
    assert "Explicit synthetic authorization" not in json.dumps(provider.messages)


@pytest.mark.parametrize("change,reason", [("no_addendum", "prior_not_accepted"),
    ("altered_hash", "prior_not_accepted"), ("no_authorization", "addendum_mismatch"),
    ("already_attempted", "suffix_already_attempted"), ("config", "snapshot_mismatch"),
    ("model", "model_mismatch"), ("noncontiguous", "not_contiguous"), ("code", "code_mismatch"),
    ("legacy_code", "code_mismatch")])
def test_invalid_continuation_is_rejected_before_call_or_output_creation(tmp_path, change, reason):
    prior, addendum = stopped_run_and_addendum(tmp_path)
    settings, identity = local_settings(), None
    if change == "no_addendum":
        addendum = None
    elif change in {"altered_hash", "no_authorization"}:
        amendment = json.loads(addendum.read_text(encoding="utf-8"))
        if change == "altered_hash":
            amendment["reviews"][0]["raw_sha256"] = "wrong"
        else:
            amendment["human_authorization"] = ""
        addendum.write_text(json.dumps(amendment), encoding="utf-8")
    elif change == "already_attempted":
        (prior / "RW04.attempt.json").write_text("{}", encoding="utf-8")
    elif change == "config":
        settings = settings.model_copy(update={"llm_seed": 99})
    elif change == "model":
        identity = {"digest": "changed"}
    elif change == "noncontiguous":
        summary = json.loads((prior / "summary.json").read_text(encoding="utf-8"))
        summary["cases"][4]["status"] = "passed"
        (prior / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    elif change in {"code", "legacy_code"}:
        manifest = json.loads((prior / "manifest.json").read_text(encoding="utf-8"))
        if change == "code":
            manifest["code_sha256"]["app/core/query_analysis.py"] = "changed"
        else:
            manifest["code_sha256"] = {name: digest for name, digest in manifest["code_sha256"].items()
                                       if not name.startswith("app/core/")}
        (prior / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    provider = ScriptedProvider([])
    with pytest.raises(ValueError, match=reason):
        capture_run(cases_path=FIXTURE, output=tmp_path / "continued", settings=settings, provider=provider,
                    reviewer=lambda *_: review(), resume_from=prior, review_addendum=addendum, model_identity=identity)
    assert not provider.messages and not (tmp_path / "continued").exists()


def test_continuation_still_stops_on_first_new_semantic_failure(tmp_path):
    prior, addendum = stopped_run_and_addendum(tmp_path)
    provider = ScriptedProvider([clear("A wrong numeric condition")])
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "continued", settings=local_settings(),
                          provider=provider, reviewer=lambda *_: review("failed"), resume_from=prior, review_addendum=addendum)
    assert summary["stop_case"] == "RW04" and summary["stop_reason"] == "semantic_failure"
    assert summary["executed"] == 1 and summary["not_run"] == 13 and len(provider.messages) == 1


def test_continue_mode_records_mixed_errors_without_retry(tmp_path):
    selected = load_cases(FIXTURE)["selected_cases"]
    contents = [clear(item["question"]) for item in selected]
    contents[1], contents[2] = "not JSON", TimeoutError("private failure")
    provider = ScriptedProvider(contents)
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=local_settings(),
                          provider=provider, continue_on_failure=True,
                          reviewer=lambda _, case: review("failed" if case["id"] == "RW01" else
                                                          "uncertain" if case["id"] == "RW04" else "passed"))
    assert summary["status"] == "completed_with_failures" and summary["not_run"] == 0
    assert (summary["failed"], summary["uncertain"], summary["passed"]) == (3, 1, 13)
    assert summary["model_calls"] == len(provider.messages) == 17
    assert summary["stop_case"] is None and summary["tool_calls"] == summary["cloud_calls"] == 0
    assert [item["failure_reason"] for item in summary["cases"][:4]] == [
        "semantic_failure", "invalid_model_output", "timeout", "manual_review_uncertain"]
    assert len({item["model_call_id"] for item in summary["cases"]}) == 17
    assert "private failure" not in (tmp_path / "run/RW03.raw.json").read_text(encoding="utf-8")


def test_continue_mode_resumes_after_failed_review_and_preserves_it(tmp_path):
    prior, _ = stopped_run_and_addendum(tmp_path)
    before = {p.name: p.read_bytes() for p in prior.iterdir()}
    remaining = load_cases(FIXTURE)["selected_cases"][3:]
    provider = ScriptedProvider([clear(item["question"]) for item in remaining])
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "continued", settings=local_settings(),
                          provider=provider, reviewer=lambda *_: review(), resume_from=prior,
                          continue_on_failure=True)
    assert summary["executed"] == summary["model_calls"] == len(provider.messages) == 14
    manifest = json.loads((tmp_path / "continued/manifest.json").read_text(encoding="utf-8"))
    reused = manifest["continuation"]["reused_first_outputs"][-1]
    assert reused["original_status"] == reused["accepted_status"] == "failed"
    assert manifest["continuation"]["start_case"] == "RW04"
    assert all(p.read_bytes() == before[p.name] for p in prior.iterdir())
    assert not (tmp_path / "continued/RW03.raw.json").exists()


def test_explicit_reviewer_interruption_ends_continue_mode(tmp_path):
    def interrupted(*_):
        raise EOFError()
    provider = ScriptedProvider([clear("PN8733 的启动电压是多少？")])
    summary = capture_run(cases_path=FIXTURE, output=tmp_path / "run", settings=local_settings(),
                          provider=provider, reviewer=interrupted, continue_on_failure=True)
    assert summary["status"] == "stopped" and summary["stop_reason"] == "manual_review_interrupted"
    assert len(provider.messages) == 1 and summary["not_run"] == 16


def test_authorized_granite_capture_freezes_prompt_and_schema_identity(tmp_path):
    from app.core.legacy_prompts import REWRITE_PROMPT_VERSION
    from app.core.legacy_schemas import QueryAnalysis

    settings = local_settings().model_copy(update={"ollama_model": "granite4.1:8b"})
    provider = ScriptedProvider([clear("PN8733 的启动电压是多少？")])
    result = capture_run(cases_path=FIXTURE, output=tmp_path / "granite", settings=settings,
                         provider=provider, reviewer=lambda *_: review("failed"))
    assert result["executed"] == len(provider.messages) == 1
    manifest = json.loads((tmp_path / "granite/manifest.json").read_text(encoding="utf-8"))
    assert manifest["config"]["ollama_model"] == "granite4.1:8b"
    assert manifest["prompt_version"] == REWRITE_PROMPT_VERSION
    schema = json.dumps(QueryAnalysis.model_json_schema(), ensure_ascii=False, sort_keys=True)
    assert manifest["schema_sha256"] == hashlib.sha256(schema.encode("utf-8")).hexdigest()
    assert "app/core/legacy_prompts.py" in manifest["code_sha256"]
    assert "app/core/legacy_schemas.py" in manifest["code_sha256"]
    for name in ("query_analysis", "conversation", "model_call", "model_provider", "legacy_cache"):
        assert f"app/core/{name}.py" in manifest["code_sha256"]


def test_changed_prompt_fingerprint_blocks_continuation_before_calls(tmp_path):
    prior, addendum = stopped_run_and_addendum(tmp_path)
    path = prior / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["code_sha256"]["app/core/legacy_prompts.py"] = "different-prompt"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    provider = ScriptedProvider([])
    with pytest.raises(ValueError, match="continuation_code_mismatch"):
        capture_run(cases_path=FIXTURE, output=tmp_path / "new", settings=local_settings(),
                    provider=provider, reviewer=lambda *_: review(), resume_from=prior, review_addendum=addendum)
    assert not provider.messages and not (tmp_path / "new").exists()
