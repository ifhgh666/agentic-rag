"""Phase E only: first visible entrance outputs, sequential manual review, no retry.

Run from backend. Output contains local diagnostic prompts from the synthetic
fixture, never credentials/private reasoning. It is not a public debug endpoint.
Every record is created exclusively. Authorized continuation uses a new directory
and references a completed prior summary; it never overwrites or retries a case.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from app.config import Settings
from app.core.conversation import PreparedQuery
from app.core.model_call import ModelCallBudget, summarize_usage
from app.core.model_provider import ChatProvider, OllamaProvider
from app.core.query_analysis import QUERY_REWRITE_POLICY_VERSION, QueryAnalyzer
from app.core.legacy_prompts import REWRITE_PROMPT_VERSION
from app.core.legacy_schemas import QueryAnalysis


ENTRANCE_ORDER = tuple(f"RW{number:02}" for number in range(1, 17)) + ("RW18",)
BACKEND = Path(__file__).resolve().parents[1]
Reviewer = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_cases(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    dataset = json.loads(content.decode("utf-8"))
    if dataset.get("version") != QUERY_REWRITE_POLICY_VERSION:
        raise ValueError("fixture_version_mismatch")
    if tuple(dataset.get("real_entrance_order", [])) != ENTRANCE_ORDER:
        raise ValueError("frozen_order_mismatch")
    items = dataset["cases"]
    by_id = {item["id"]: item for item in items}
    if len(by_id) != len(items):
        raise ValueError("duplicate_case_id")
    selected = [by_id[case_id] for case_id in ENTRANCE_ORDER]
    if {item["id"] for item in items if item.get("stage") == "E"} != set(ENTRANCE_ORDER):
        raise ValueError("frozen_case_set_mismatch")
    for item in selected:
        if item.get("validation") != "real_entrance" or not isinstance(item["question"], str):
            raise ValueError("invalid_entrance_fixture")
        inputs = item["input"]
        if set(inputs) != {"conversation_summary", "history_messages", "pending_query", "pending_clarifications", "action"}:
            raise ValueError("invalid_fixture_input_keys")
    return {"version": dataset["version"], "frozen_on": dataset["frozen_on"],
            "sha256": hashlib.sha256(content).hexdigest(), "selected_cases": selected}


def settings_snapshot(settings: Settings) -> dict[str, Any]:
    endpoint = urlparse(settings.ollama_base_url)
    if (settings.llm_provider != "ollama" or settings.ollama_model not in {"qwen3:4b-instruct", "granite4.1:8b"}
            or endpoint.scheme != "http" or endpoint.hostname not in {"localhost", "127.0.0.1", "::1"}
            or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
            or not 0 < settings.llm_timeout_seconds <= 120
            or not 0 < settings.request_timeout_seconds <= 300
            or settings.max_query_analysis_calls < 1):
        raise ValueError("unapproved_provider_model_or_budget")
    fields = ("llm_provider", "ollama_model", "ollama_base_url", "llm_temperature", "llm_seed",
              "llm_timeout_seconds", "request_timeout_seconds", "model_context_window",
              "max_context_tokens", "llm_max_output_tokens", "model_context_safety_tokens",
              "main_history_input_token_limit", "max_question_chars")
    return {**{field: getattr(settings, field) for field in fields},
            "entrance_calls_per_case": 1, "batch_model_call_limit": len(ENTRANCE_ORDER),
            "cache_enabled": False, "automatic_retries": 0, "judge_calls": 0,
            "index_access": False, "context_source": "frozen_fixture"}


def continuation_cases(dataset: dict[str, Any], config: dict[str, Any], prior: Path,
                       addendum: Path | None, model_identity: dict[str, Any] | None,
                       allow_failed: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Audit prior records and select only their untouched contiguous suffix.

    This is capture bookkeeping, not an entrance semantic validator. Any changed
    manual decision must be supplied separately, with explicit human approval.
    """
    prior = prior.resolve()
    manifest = json.loads((prior / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((prior / "summary.json").read_text(encoding="utf-8"))
    if (manifest.get("phase") != "E" or manifest.get("fixture") != dataset
            or manifest.get("config") != config or summary.get("status") != "stopped"
            or manifest.get("continuation")):
        raise ValueError("continuation_snapshot_mismatch")
    for name in ("app/core/query_analysis.py", "app/core/conversation.py", "app/core/model_call.py",
                 "app/core/model_provider.py", "app/core/legacy_schemas.py", "app/core/legacy_prompts.py",
                 "app/core/legacy_cache.py"):
        if hashlib.sha256((BACKEND / name).read_bytes()).hexdigest() != manifest["code_sha256"].get(name):
            raise ValueError("continuation_code_mismatch")
    if manifest.get("model_identity") != (model_identity or {"source": "not_recorded"}):
        raise ValueError("continuation_model_mismatch")
    previous = summary["cases"]
    if tuple(item["id"] for item in previous) != ENTRANCE_ORDER:
        raise ValueError("continuation_order_mismatch")
    remaining_at = next((i for i, item in enumerate(previous) if item["status"] == "not_run"), len(previous))
    if not 0 < remaining_at < len(previous) or any(item["status"] != "not_run" for item in previous[remaining_at:]):
        raise ValueError("continuation_not_contiguous")
    amendment = json.loads(addendum.read_text(encoding="utf-8")) if addendum else {}
    if amendment and (Path(amendment["source_run"]).resolve() != prior
                      or amendment.get("source_summary_sha256") != hashlib.sha256((prior / "summary.json").read_bytes()).hexdigest()
                      or not isinstance(amendment.get("human_authorization"), str)
                      or not amendment["human_authorization"].strip()):
        raise ValueError("continuation_addendum_mismatch")
    corrections = {item["case_id"]: item for item in amendment.get("reviews", [])}
    if len(corrections) != len(amendment.get("reviews", [])) or not set(corrections).issubset({item["id"] for item in previous[:remaining_at]}):
        raise ValueError("continuation_addendum_case_mismatch")
    references = []
    for entry, case in zip(previous[:remaining_at], dataset["selected_cases"]):
        raw_path, review_path = prior / f"{entry['id']}.raw.json", prior / f"{entry['id']}.review.json"
        raw, reviewed = json.loads(raw_path.read_text(encoding="utf-8")), json.loads(review_path.read_text(encoding="utf-8"))
        raw_hash, review_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest(), hashlib.sha256(review_path.read_bytes()).hexdigest()
        if (raw["case_id"] != entry["id"] or raw["question"] != case["question"]
                or raw.get("failure_reason") or raw["outcome"]["source"] != "model"
                or raw["usage"]["model_calls"] != 1 or raw["usage"]["tool_calls"] or raw["usage"]["cloud_calls"]
                or raw["usage"]["budget_exceeded"] or not raw["model_call_id"]
                or reviewed["case_id"] != entry["id"] or reviewed["status"] != entry["status"]):
            raise ValueError("continuation_prior_record_invalid")
        decision = corrections.get(entry["id"], reviewed)
        allowed_statuses = {"passed", "failed", "uncertain"} if allow_failed else {"passed"}
        if (decision.get("status") not in allowed_statuses
                or not all(isinstance(decision.get(key), str) and decision[key].strip() for key in ("reviewer", "rationale"))
                or entry["id"] in corrections and (decision.get("raw_sha256") != raw_hash or decision.get("review_sha256") != review_hash)):
            raise ValueError("continuation_prior_not_accepted")
        references.append({"case_id": entry["id"], "original_status": entry["status"], "accepted_status": decision["status"],
                           "request_id": raw["request_id"], "model_call_id": raw["model_call_id"],
                           "raw_sha256": raw_hash, "review_sha256": review_hash,
                           "review_source": "addendum" if entry["id"] in corrections else "original"})
    # Even a stale summary cannot cause an attempted case to be called again.
    if any(list(prior.glob(f"{item['id']}.*")) or item.get("request_id") or item.get("thread_id") for item in previous[remaining_at:]):
        raise ValueError("continuation_suffix_already_attempted")
    return dataset["selected_cases"][remaining_at:], {
        "source_run": str(prior), "source_manifest_sha256": hashlib.sha256((prior / "manifest.json").read_bytes()).hexdigest(),
        "source_summary_sha256": hashlib.sha256((prior / "summary.json").read_bytes()).hexdigest(),
        "review_addendum": amendment, "review_addendum_sha256": hashlib.sha256(addendum.read_bytes()).hexdigest() if addendum else None,
        "reused_first_outputs": references, "start_case": previous[remaining_at]["id"], "no_repeated_cases": True}


def capture_run(*, cases_path: Path, output: Path, settings: Settings,
                provider: ChatProvider, reviewer: Reviewer, model_identity: dict[str, Any] | None = None,
                resume_from: Path | None = None, review_addendum: Path | None = None,
                continue_on_failure: bool = False) -> dict[str, Any]:
    dataset = load_cases(cases_path)
    config = settings_snapshot(settings)
    selected, continuation = dataset["selected_cases"], None
    if review_addendum and not resume_from:
        raise ValueError("review_addendum_requires_prior_run")
    if resume_from:
        selected, continuation = continuation_cases(dataset, config, resume_from, review_addendum, model_identity,
                                                     allow_failed=continue_on_failure)
    config["batch_model_call_limit"] = len(selected)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)  # Even an empty existing directory is refused.
    started = time.perf_counter()
    cases = [{"id": case_id, "status": "not_run", "request_id": None, "thread_id": None}
             for case_id in (item["id"] for item in selected)]
    code_files = ("app/core/query_analysis.py", "app/core/conversation.py", "app/core/model_call.py",
                  "app/core/model_provider.py", "app/core/legacy_schemas.py", "app/core/legacy_prompts.py",
                  "app/core/legacy_cache.py",
                  "scripts/capture_query_rewrite_v1.py")
    save_new(output / "manifest.json", {
        "created_at": now(), "phase": "E", "policy_version": QUERY_REWRITE_POLICY_VERSION,
        "prompt_version": REWRITE_PROMPT_VERSION,
        "schema_sha256": hashlib.sha256(json.dumps(QueryAnalysis.model_json_schema(), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "cases_path": str(cases_path.resolve()), "fixture": dataset, "config": config,
        "model_identity": model_identity or {"source": "not_recorded"},
        "code_sha256": {name: hashlib.sha256((BACKEND / name).read_bytes()).hexdigest() for name in code_files},
        "initial_cases": cases, "protocol": ("first_output_only; manual_review_before_next; continue_on_failure"
                                              if continue_on_failure else
                                              "first_output_only; manual_review_before_next; stop_on_failure"),
        "continuation": continuation,
        "scope": "entrance only; no graph, retrieval, index, memory writes or model Judge",
        "raw_output_scope": "first visible ModelResult.content from existing provider (private reasoning removed)",
    })
    summary: dict[str, Any] = {"status": "completed", "cases": cases, "model_calls": 0,
                               "tool_calls": 0, "cloud_calls": 0, "stop_case": None, "stop_reason": None}
    for position, case in enumerate(selected):
        request_id, thread_id = f"rw-e-{uuid4().hex}", f"rw-e-thread-{uuid4().hex}"
        entry = cases[position]
        entry.update(request_id=request_id, thread_id=thread_id, status="review_pending")
        inputs = case["input"]
        prepared = PreparedQuery(rewritten_query=case["question"], question_is_clear=bool(case["question"]), **inputs)
        context_source = {"kind": "frozen_fixture", "case_id": case["id"], "fixture_sha256": dataset["sha256"],
                          "history_count": len(prepared.history_messages), "has_summary": bool(prepared.conversation_summary),
                          "pending_supplied": bool(prepared.pending_query),
                          "pending_used": bool(prepared.pending_query) and prepared.action == "continue_clarification"}
        began = now()
        save_new(output / f"{case['id']}.attempt.json", {
            "case_id": case["id"], "question": case["question"], "input": inputs,
            "context_source": context_source, "request_id": request_id, "thread_id": thread_id,
            "started_at": began, "max_model_calls": 1, "request_timeout_seconds": settings.request_timeout_seconds,
            "model_wait_seconds": settings.llm_timeout_seconds,
        })
        budget = ModelCallBudget(1, 1, {"query_analysis": 1}, timeout_seconds=settings.request_timeout_seconds, tool_limit=0)
        call_started = time.perf_counter()
        budget.start(request_id, deadline=time.monotonic() + settings.request_timeout_seconds)
        outcome = QueryAnalyzer(settings, provider=provider, budget=budget).analyze(
            case["question"], prepared, request_id=request_id, thread_id=thread_id)
        duration = int((time.perf_counter() - call_started) * 1000)
        usage = summarize_usage([outcome.model_trace] if outcome.model_trace else [], budget.finish(request_id), {}, duration)
        trace = outcome.model_trace or {}
        record = {"case_id": case["id"], "question": case["question"], "resolved_original": prepared.resolved_original(case["question"]),
                  "request_id": request_id, "thread_id": thread_id, "context_source": context_source,
                  "started_at": began, "finished_at": now(), "duration_ms": duration,
                  "model_call_id": trace.get("model_call_id"), "raw_output": trace.get("candidate_content"),
                  "input_messages": trace.get("input_messages", []), "model_trace": outcome.model_trace,
                  "outcome": {key: value for key, value in asdict(outcome).items() if key != "model_trace"},
                  "failure_reason": outcome.failure_reason, "usage": usage}
        save_new(output / f"{case['id']}.raw.json", record)  # Save before requesting any review.
        entry.update(raw_file=f"{case['id']}.raw.json", model_call_id=record["model_call_id"], duration_ms=duration)
        for key in ("model_calls", "tool_calls", "cloud_calls"):
            summary[key] += usage[key]
        reason = outcome.failure_reason
        if not reason and (usage["model_calls"] != 1 or not record["model_call_id"] or outcome.source != "model"):
            reason = "not_one_real_entrance_call"
        if not reason and (usage["cloud_calls"] or usage["tool_calls"] or usage["budget_exceeded"]):
            reason = "capture_budget_violation"
        if not reason:
            try:
                decision = reviewer(record, case)
                valid = (isinstance(decision, dict) and decision.get("status") in {"passed", "failed", "uncertain"}
                         and all(isinstance(decision.get(field), str) and decision[field].strip()
                                 for field in ("reviewer", "rationale")))
                if not valid:
                    reason = "manual_review_missing_or_invalid"
                else:
                    save_new(output / f"{case['id']}.review.json", {**decision, "case_id": case["id"], "reviewed_at": now()})
                    entry["status"] = decision["status"]
                    entry["review_file"] = f"{case['id']}.review.json"
                    if decision["status"] != "passed":
                        reason = "semantic_failure" if decision["status"] == "failed" else "manual_review_uncertain"
            except (EOFError, KeyboardInterrupt):
                reason = "manual_review_interrupted"
            except Exception as exc:
                reason = f"manual_review_error:{type(exc).__name__}"
        if reason:
            if outcome.failure_reason or reason in {"not_one_real_entrance_call", "capture_budget_violation"}:
                entry["status"] = "failed"
            entry["failure_reason"] = reason
            if continue_on_failure and reason not in {"capture_budget_violation", "manual_review_interrupted"}:
                if entry["status"] == "review_pending":
                    entry["status"] = "uncertain"
                continue
            summary.update(status="stopped", stop_case=case["id"], stop_reason=reason)
            break
    if summary["status"] == "completed" and any(entry["status"] in {"failed", "uncertain"} for entry in cases):
        summary["status"] = "completed_with_failures"
    summary.update(finished_at=now(), elapsed_seconds=round(time.perf_counter() - started, 3),
                   executed=sum(item["status"] != "not_run" for item in cases),
                   passed=sum(item["status"] == "passed" for item in cases),
                   failed=sum(item["status"] == "failed" for item in cases),
                   uncertain=sum(item["status"] == "uncertain" for item in cases),
                   not_run=sum(item["status"] == "not_run" for item in cases))
    save_new(output / "summary.json", summary)
    return summary


def interactive_review(record: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    # The rubric is shown only after inference and never sent back to the model.
    print(json.dumps({"case_id": case["id"], "question": case["question"], "input_fixture": case["input"],
                      "raw_output": record["raw_output"], "outcome": record["outcome"],
                      "usage": record["usage"], "duration_ms": record["duration_ms"],
                      "manual_rubric": case["expected"]}, ensure_ascii=False), flush=True)
    return json.loads(input('REVIEW_JSON (status passed/failed/uncertain, reviewer, rationale): '))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stop-on-failure", action="store_true")
    mode.add_argument("--continue-on-failure", action="store_true", help="Record per-case errors and continue; no retries or changes to quality decisions")
    parser.add_argument("--resume-from", type=Path, help="Read a prior stopped run; write only remaining first outputs to a new directory")
    parser.add_argument("--review-addendum", type=Path, help="Separate human-authorized manual review; prior evidence stays unchanged")
    args = parser.parse_args()
    try:
        settings = Settings()
        settings_snapshot(settings)
        load_cases(args.cases)
        if args.output.exists():
            raise FileExistsError("output_already_exists")
        provider = OllamaProvider(settings)
        # Freeze the installed model digest with a read-only lookup. No warmup or pull.
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
        installed = next((item for item in response.json().get("models", [])
                          if item.get("name") == settings.ollama_model), None)
        if not installed:
            raise ValueError("approved_model_not_installed")
        model_identity = {key: installed.get(key) for key in ("name", "digest", "modified_at", "size", "details")}
        model_identity["source"] = "local_ollama_api_tags"
        print("Frozen phase E: at most 17 entrance calls; manual review required; no retry.", flush=True)
        summary = capture_run(cases_path=args.cases, output=args.output, settings=settings,
                              provider=provider, reviewer=interactive_review, model_identity=model_identity,
                              resume_from=args.resume_from, review_addendum=args.review_addendum,
                              continue_on_failure=args.continue_on_failure)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 0 if summary["status"] == "completed" else 1
    except Exception as exc:
        print(json.dumps({"status": "capture_error", "error_type": type(exc).__name__}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
