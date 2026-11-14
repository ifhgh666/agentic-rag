"""One stage-C API smoke question; never a formal 30-question scoring run.

Password is read interactively, never from arguments, source files or reports.
No retry, follow-up clarification, knowledge write, index rebuild or cloud fallback.
"""
from pathlib import Path
import argparse
import getpass
import hashlib
import json
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings
from scripts.loop005_snapshot import knowledge_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--case", choices=("Q16", "C-UV"), default="Q16")
    parser.add_argument("--output", type=Path, default=ROOT / "output/loop005-phase-c-platform-20261009.json")
    args = parser.parse_args()
    if urlsplit(args.url).hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("Local platform smoke only")
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new path to preserve earlier results")
    settings = Settings()
    if settings.llm_provider != "ollama":
        raise SystemExit("Local Ollama only")
    baseline = json.loads((ROOT / "output/loop005-baseline/snapshot.json").read_text(encoding="utf-8"))
    before = knowledge_hashes()
    if before != baseline["knowledge"]:
        raise SystemExit("Knowledge fingerprints changed; smoke not started")
    capture = json.loads((ROOT / "output/rag30-20261008/capture.json").read_text(encoding="utf-8"))
    case = next(c for c in capture["cases"] if str(c["question_id"]) in {"16", "Q16"})
    question = case["question"]  # Only question goes to the API, never the reference answer.
    if args.case == "C-UV":
        # Independent stage-C scenario with an explicit device; not a replacement
        # for a failed formal case or a reference answer embedded in the request.
        question = "PX-200 输入电压为195 V，持续300 ms，是否会触发欠压保护？请说明判断依据。"
    password = getpass.getpass("Platform password: ")
    with httpx.Client(base_url=args.url, timeout=settings.request_timeout_seconds + 30) as client:
        health = client.get("/api/health").json()
        login = client.post("/api/auth/login", json={"username": settings.admin_username, "password": password})
        password = ""
        login.raise_for_status()
        token = login.json()["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        thread = "phase-c-smoke-" + uuid4().hex
        started = time.perf_counter()
        print("stage_c_single_question_started", flush=True)
        response = client.post("/api/chat/stream", json={"question": question, "thread_id": thread})
        elapsed = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        events = []
        for block in response.text.split("\n\n"):
            if not block.strip():
                continue
            lines = block.splitlines()
            event = next(line[7:] for line in lines if line.startswith("event: "))
            data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
            events.append({"event": event, "data": data})
        request_id = response.headers["x-request-id"]
        local = settings.data_dir / "logs/loop_traces" / (request_id + ".json")
        trace = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
        complete = next(e["data"] for e in events if e["event"] == "complete")
        # The API's outer deadline can finish before graph diagnostics/usage.
        # Preserve that real timeout without treating unknown usage as zero.
        usage = next((e["data"] for e in events if e["event"] == "usage"), {})
        answer = next((e["data"] for e in events if e["event"] == "answer"), {})
        calls = {c["model_call_id"] for c in trace.get("model_trace", []) if c.get("model_call_id")}
        decisions = [e["data"] for e in events if e["event"] == "agent_decision" and e["data"].get("decision_source") == "model"]
        tools = [e["data"] for e in events if e["event"] == "tool_call"]
        after = knowledge_hashes()
        passed = bool(decisions and tools and all(d.get("model_call_id") in calls for d in decisions)
            and complete["status"] in {"completed", "partial", "insufficient"}
            and usage.get("cloud_calls") == 0 and before == after)
        result = {"purpose": "stage_c_single_question_smoke_not_formal_score", "passed": passed,
            "transport": "normal_frontend_proxy_api", "url": args.url,
            "question_id": args.case, "question": question, "request_id": request_id, "thread_id": thread,
            "status": complete["status"], "stop_reason": complete.get("reason"), "stop_origin": complete.get("stop_origin"),
            "answer": answer.get("answer", ""), "sources": answer.get("sources", []),
            "end_to_end_ms": elapsed, "usage": usage, "usage_available": bool(usage), "events": events,
            "local_trace": str(local), "local_trace_sha256": hashlib.sha256(local.read_bytes()).hexdigest() if local.exists() else None,
            "model_decision_count": len(decisions), "tool_call_count": len(tools),
            "model_call_ids_linked": bool(decisions) and all(d.get("model_call_id") in calls for d in decisions),
            "knowledge_hashes_before": before, "knowledge_hashes_after": after,
            "knowledge_unchanged": before == after,
            "profile": {name: getattr(settings, name) for name in ("llm_provider", "ollama_model", "agent_loop_protocol",
                "model_context_window", "llm_max_output_tokens", "max_context_tokens", "max_simple_llm_calls",
                "max_llm_calls_per_request", "max_tool_calls", "request_timeout_seconds", "llm_timeout_seconds")}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        client.post("/api/auth/logout")
        print(json.dumps({"passed": passed, "status": result["status"], "model_calls": usage.get("model_calls"),
                          "end_to_end_ms": elapsed, "output": str(args.output)}), flush=True)
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
