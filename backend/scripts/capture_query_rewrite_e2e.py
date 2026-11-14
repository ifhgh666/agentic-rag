"""Phase F: three fixed normal-API first requests, separate manual judgments.

No follow-up, retry, reference input, index write or cloud fallback. Password is
read with getpass (or an optional masked local dialog), never from arguments.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx

from app.config import Settings
from scripts.capture_query_rewrite_v1 import now, save_new


BACKEND = Path(__file__).resolve().parents[1]
QUESTIONS = (
    "设备输入电压为 245 V，持续 400 ms，会触发什么保护？之后如何恢复？",
    "PX-200 输入电压为195 V，持续300 ms，是否会触发欠压保护？请说明判断依据。",
    "PX-200 的过压保护触发电压和恢复电压分别是多少？哪个更高？",
)
CASE_IDS = ("Q16", "C-UV", "COMPARE")


def load_requests(path: Path) -> list[dict[str, str]]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    case = next(item for item in dataset["cases"] if item["id"] == "RW24")
    if dataset.get("version") != "query-rewrite-v1" or tuple(case.get("requests", [])) != QUESTIONS:
        raise ValueError("frozen_request_mismatch")
    return [{"id": case_id, "question": question} for case_id, question in zip(CASE_IDS, QUESTIONS)]


def fingerprint(settings: Settings) -> dict[str, str]:
    """Read source/parsed records, index manifest/vectors and Qdrant storage bytes.

    Runtime logs, model caches and Qdrant's process lock are outside this set.
    File additions/removals also change the snapshot; no database is opened.
    """
    paths = [(settings.data_dir / name, name) for name in ("documents.json", "parents.json", "children.json")]
    for folder in ("documents", "index"):
        paths.extend((path, path.relative_to(settings.data_dir).as_posix())
                     for path in (settings.data_dir / folder).rglob("*") if path.is_file())
    paths.extend((path, "qdrant/" + path.relative_to(settings.qdrant_path).as_posix())
                 for path in settings.qdrant_path.rglob("*") if path.is_file() and path.name != ".lock")
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for path, name in sorted(paths, key=lambda row: row[1])
            if path.is_file()}


def safe_profile(settings: Settings) -> dict[str, Any]:
    if (settings.llm_provider != "ollama" or settings.ollama_model != "qwen3:4b-instruct"
            or not 0 < settings.request_timeout_seconds <= 300 or not 0 < settings.llm_timeout_seconds <= 120
            or settings.max_query_analysis_calls != 1 or not 0 < settings.max_llm_calls_per_request <= 12
            or not 0 < settings.max_simple_llm_calls <= 8 or settings.max_tool_calls > 16):
        raise ValueError("unapproved_model_or_budget")
    names = ("llm_provider", "ollama_model", "llm_temperature", "llm_seed", "agent_loop_protocol",
             "request_timeout_seconds", "llm_timeout_seconds", "max_query_analysis_calls", "max_simple_llm_calls",
             "max_llm_calls_per_request", "max_tool_calls", "model_context_window", "max_context_tokens",
             "llm_max_output_tokens", "model_context_safety_tokens", "sparse_offline_fallback", "embedding_model")
    return {**{name: getattr(settings, name) for name in names},
            "embedding_backend": settings.effective_embedding_backend,
            "max_requests": 3, "max_batch_model_calls": 36, "automatic_retries": 0, "judge_calls": 0}


def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
        raise ValueError("local_http_api_only")


def login_hidden(client: httpx.Client, settings: Settings, reader: Callable[[str], str]) -> None:
    password = reader("Local platform password (hidden): ")
    if not password:
        raise EOFError("credential_input_cancelled")
    response = client.post("/api/auth/login", json={"username": settings.admin_username, "password": password}, timeout=10)
    password = ""
    response.raise_for_status()
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]


def parse_sse(text: str) -> list[dict[str, Any]]:
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        name = next((line[6:].strip() for line in lines if line.startswith("event:")), None)
        data = "\n".join(line[5:].lstrip() for line in lines if line.startswith("data:"))
        if not name or not data:
            raise ValueError("invalid_sse")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("invalid_sse")
        events.append({"event": name, "data": payload})
    return events


def capture_case(client: httpx.Client, settings: Settings, case: dict[str, str], output: Path) -> dict[str, Any]:
    thread_id = f"rw-f-{uuid4().hex}"
    payload = {"question": case["question"], "thread_id": thread_id, "action": "new_question"}
    started_at, started = now(), time.perf_counter()
    save_new(output / f"{case['id']}.attempt.json", {"case_id": case["id"], "payload": payload,
             "started_at": started_at, "timeout_seconds": settings.request_timeout_seconds})
    chunks, events = [], []
    request_id, status_code, reason = None, None, None
    try:
        # The server's shared deadline remains <=300s. Five seconds of transport
        # allowance lets its timeout event arrive; no additional model budget.
        with client.stream("POST", "/api/chat/stream", json=payload,
                           timeout=httpx.Timeout(settings.request_timeout_seconds + 5, connect=5)) as response:
            status_code = response.status_code
            identity = response.headers.get("x-request-id")
            if identity:
                request_id = str(UUID(identity))  # Never use untrusted paths from headers.
            for chunk in response.iter_text():
                chunks.append(chunk)
            if status_code != 200:
                reason = f"http_{status_code}"
    except Exception as exc:
        reason = type(exc).__name__  # Do not persist exception messages or headers.
    elapsed = int((time.perf_counter() - started) * 1000)
    text = "".join(chunks)
    with (output / f"{case['id']}.sse.txt").open("x", encoding="utf-8") as file:
        file.write(text)
    if not reason:
        try:
            events = parse_sse(text)
        except (ValueError, TypeError):
            reason = "invalid_sse"
    def event(name):
        return next((item["data"] for item in events if item["event"] == name), {})
    complete, usage, answer, analysis = (event(name) for name in ("complete", "usage", "answer", "analysis"))
    if not reason and not complete:
        reason = "missing_complete"
    if not reason and complete.get("status") != "completed":
        reason = complete.get("reason") or "complete_answer_not_verified"
    if not reason and not request_id:
        reason = "missing_request_id"
    if not reason and not usage:
        reason = "usage_unavailable"
    if usage and not reason:
        if (type(usage.get("cloud_calls")) is not int or usage["cloud_calls"] != 0
                or type(usage.get("model_calls")) is not int or not 1 <= usage["model_calls"] <= 12
                or type(usage.get("tool_calls")) is not int or not 0 <= usage["tool_calls"] <= 16):
            reason = "capture_budget_violation"
    local = settings.data_dir / "logs/loop_traces" / f"{request_id}.json" if request_id else None
    trace, trace_hash = {}, None
    if local and local.is_file():
        try:
            content = local.read_bytes()
            trace = json.loads(content.decode("utf-8"))
            trace_hash = hashlib.sha256(content).hexdigest()
            if trace.get("request_id") != request_id or trace.get("original_question") != case["question"]:
                trace = {}
                reason = "local_trace_identity_mismatch"
        except (ValueError, OSError):
            reason = reason or "local_trace_unavailable"
    keep = {"node", "model_call_id", "candidate_content", "provider", "model", "duration_ms", "failure_reason",
            "original_conditions", "input_tokens", "output_tokens", "input_tokens_estimate", "output_tokens_estimate"}
    models = [{key: value for key, value in item.items() if key in keep} for item in trace.get("model_trace", [])]
    record = {"case_id": case["id"], "question": case["question"], "payload": payload,
              "request_id": request_id, "thread_id": thread_id, "http_status": status_code,
              "started_at": started_at, "finished_at": now(), "end_to_end_ms": elapsed,
              "status": complete.get("status", "transport_failed"), "failure_reason": reason,
              "answer": answer.get("answer", ""), "sources": answer.get("sources", []),
              "analysis": analysis, "verification": event("verification"), "usage": usage or None,
              "usage_available": bool(usage), "events": events, "model_outputs": models,
              "tool_trace": [item for item in trace.get("execution_trace", []) if str(item.get("event", "")).startswith("tool_")],
              "local_trace": str(local) if local and local.is_file() else None, "local_trace_sha256": trace_hash,
              "raw_sse_file": f"{case['id']}.sse.txt", "raw_sse_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    save_new(output / f"{case['id']}.raw.json", record)
    return record


def capture_run(*, client: httpx.Client, settings: Settings, cases_path: Path, output: Path,
                reviewer: Callable, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    cases, config = load_requests(cases_path), safe_profile(settings)
    validate_url(str(client.base_url))
    output.mkdir(parents=True, exist_ok=False)
    before = fingerprint(settings)
    started = time.perf_counter()
    statuses = [{"id": item["id"], "status": "not_run", "request_id": None, "thread_id": None} for item in cases]
    sources = [*BACKEND.joinpath("app").rglob("*.py"), Path(__file__).resolve()]
    save_new(output / "manifest.json", {"created_at": now(), "phase": "F", "cases": cases,
             "fixture_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(), "profile": config,
             "api_url": str(client.base_url), "metadata": metadata or {}, "knowledge_before": before,
             "code_sha256": {path.relative_to(BACKEND).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
             "initial_statuses": statuses, "context_source": "none; new thread for each original question",
             "protocol": "first normal API request only; separate manual entrance/answer review before next; stop on failure"})
    summary = {"status": "completed", "cases": statuses, "stop_case": None, "stop_reason": None,
               "model_calls": 0, "tool_calls": 0, "cloud_calls": 0}
    for index, case in enumerate(cases):
        if fingerprint(settings) != before:
            summary.update(status="stopped", stop_case=case["id"], stop_reason="knowledge_changed")
            break
        record = capture_case(client, settings, case, output)
        entry = statuses[index]
        entry.update(status="review_pending", request_id=record["request_id"], thread_id=record["thread_id"],
                     raw_file=f"{case['id']}.raw.json", end_to_end_ms=record["end_to_end_ms"])
        reason = record["failure_reason"]
        for name in ("model_calls", "tool_calls", "cloud_calls"):
            value = (record["usage"] or {}).get(name)
            summary[name] = summary[name] + value if summary[name] is not None and type(value) is int and value >= 0 else None
        if summary["model_calls"] is not None and summary["model_calls"] > 36:
            reason = "capture_budget_violation"
        if record["events"]:
            try:
                decision = reviewer(record, case)
                allowed = {"passed", "failed", "not_verified", "uncertain"}
                valid = (isinstance(decision, dict)
                         and all(decision.get(name) in allowed for name in ("entrance_status", "answer_status"))
                         and all(isinstance(decision.get(name), str) and decision[name].strip() for name in ("reviewer", "rationale")))
                if not valid:
                    reason = reason or "manual_review_missing_or_invalid"
                else:
                    save_new(output / f"{case['id']}.review.json", {**decision, "case_id": case["id"], "reviewed_at": now()})
                    entry.update(entrance_status=decision["entrance_status"], answer_status=decision["answer_status"],
                                 review_file=f"{case['id']}.review.json")
                    if decision["entrance_status"] != "passed" or decision["answer_status"] != "passed":
                        reason = reason or ("semantic_failure" if "failed" in (decision["entrance_status"], decision["answer_status"])
                                            else "complete_answer_not_verified")
            except (EOFError, KeyboardInterrupt):
                reason = reason or "manual_review_interrupted"
            except Exception as exc:
                reason = reason or f"manual_review_error:{type(exc).__name__}"
        if fingerprint(settings) != before:
            reason = "knowledge_changed"
        if reason:
            entry["status"] = "failed"
            summary.update(status="stopped", stop_case=case["id"], stop_reason=reason)
            break
        entry["status"] = "passed"
    summary.update(finished_at=now(), elapsed_seconds=round(time.perf_counter() - started, 3),
                   executed=sum(item["status"] != "not_run" for item in statuses),
                   not_run=sum(item["status"] == "not_run" for item in statuses),
                   knowledge_after=fingerprint(settings), knowledge_unchanged=fingerprint(settings) == before)
    save_new(output / "summary.json", summary)
    return summary


def interactive_review(record: dict[str, Any], case: dict[str, str]) -> dict[str, Any]:
    print(json.dumps({key: record[key] for key in ("case_id", "question", "status", "failure_reason", "analysis",
          "answer", "sources", "verification", "usage", "end_to_end_ms", "model_outputs")}, ensure_ascii=False), flush=True)
    return json.loads(input("REVIEW_JSON (entrance_status, answer_status, reviewer, rationale, optional checks): "))


def dialog_password(prompt: str) -> str:
    import tkinter as tk
    from tkinter import simpledialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return simpledialog.askstring("阶段 F 本地平台登录", "请输入平台密码（隐藏输入；仅用于本次本机登录）：",
                                      show="*", parent=root) or ""
    finally:
        root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", type=Path, default=BACKEND / "tests/fixtures/query_rewrite_v1_cases.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-on-failure", action="store_true", required=True)
    parser.add_argument("--credential-dialog", action="store_true", help="Windows: masked local password dialog instead of getpass")
    args = parser.parse_args()
    try:
        validate_url(args.url)
        settings = Settings()
        safe_profile(settings)
        load_requests(args.cases)
        if args.output.exists():
            raise FileExistsError("output_already_exists")
        with httpx.Client(base_url=args.url, timeout=5, trust_env=False, follow_redirects=False) as client:
            health = client.get("/api/health").json()
            if not health.get("index_ready"):
                raise ValueError("formal_index_not_ready")
            validate_url(settings.ollama_base_url)
            installed = httpx.get(settings.ollama_base_url.rstrip("/") + "/api/tags", timeout=5, trust_env=False).json()
            model = next(item for item in installed["models"] if item["name"] == settings.ollama_model)
            print("Phase F prepared: local API, three fixed first requests, no retry. Waiting for hidden login.", flush=True)
            login_hidden(client, settings, dialog_password if args.credential_dialog else getpass.getpass)
            print("Local login completed; starting Q16 once.", flush=True)
            try:
                result = capture_run(client=client, settings=settings, cases_path=args.cases, output=args.output,
                                     reviewer=interactive_review, metadata={"health": health, "model_identity": model})
                print(json.dumps(result, ensure_ascii=False), flush=True)
                return 0 if result["status"] == "completed" else 1
            finally:
                try:
                    client.post("/api/auth/logout", timeout=5)
                except httpx.HTTPError:
                    print("Logout unavailable; no further requests submitted.", flush=True)
                client.headers.pop("Authorization", None)
    except Exception as exc:
        print(json.dumps({"status": "capture_error", "error_type": type(exc).__name__}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
