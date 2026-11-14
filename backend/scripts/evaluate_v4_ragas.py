"""独立离线评估；未审核题集先拒绝，Judge 只能使用已安装的本机模型。"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from scripts.validate_v4_gold_dataset import BACKEND_ROOT, DEFAULT_DATASET, GoldDataset, validate_dataset


METRIC_NAMES = ("answer_accuracy", "context_relevance", "response_groundedness", "context_precision", "context_recall")
PINNED_RAGAS = "0.4.3"
OUTPUT_ROOT = BACKEND_ROOT / "tmp/v4-evaluations"


def validate_local_base_url(url: str) -> str:
    parts = urlsplit(url)
    if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parts.username or parts.password or parts.query or parts.fragment or parts.path.rstrip("/") != "/v1"):
        raise ValueError("Judge 仅允许无凭据的本机 HTTP /v1 地址")
    port = parts.port or 11434
    host = "[::1]" if parts.hostname == "::1" else "127.0.0.1"
    return urlunsplit(("http", f"{host}:{port}", "/v1/", "", ""))


def file_hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest().upper()


def validate_index_documents(manifest_path: Path, manifest: dict, gold: GoldDataset) -> None:
    """只读复核索引的源文档聚合指纹，不初始化或迁移生产索引。"""
    data_dir = manifest_path.resolve().parent.parent
    documents_root = (data_dir / "documents").resolve()
    documents = json.loads((data_dir / "documents.json").read_text(encoding="utf-8"))
    snapshots = []
    gold_found = False
    for document in documents:
        if document.get("status") != "ready":
            continue
        source = Path(document.get("source_path") or "").resolve()
        if not source.is_relative_to(documents_root) or not source.is_file():
            raise ValueError("index_source_invalid")
        digest = file_hash(source).lower()
        document_id = document["document_id"]
        snapshots.append({"document_id": document_id, "source_sha256": digest})
        if document_id == str(gold.source_document.document_id):
            if digest != gold.source_document.sha256.lower():
                raise ValueError("index_document_mismatch")
            gold_found = True
    encoded = json.dumps(sorted(snapshots, key=lambda item: item["document_id"]),
                         sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if not gold_found or hashlib.sha256(encoded).hexdigest() != manifest.get("documents_sha256"):
        raise ValueError("index_documents_snapshot_mismatch")


def capture_graph_result(case: dict, result, *, index_version: str, answer_model: str) -> dict:
    """由实际 GraphRunResult 导出，不把标准答案或引文填成实际检索结果。"""
    candidates = [item.model_dump(mode="json") for item in result.retrieved_results]
    batches = copy.deepcopy(result.retrieval_batches)
    raw_contexts = [item["content"] for batch in batches for item in batch["results"]]
    generated_contexts = [str(item["content"]) for item in result.context_messages if str(item.get("content", "")).strip()]
    return {
        "case_id": case["case_id"], "question": case["question"],
        "history_fixture": copy.deepcopy(case.get("history_fixture", [])),
        "request_id": result.request_id, "thread_id": result.thread_id,
        "user_input": result.rewritten_query, "independent_questions": list(result.questions),
        "response": result.final_answer, "status": result.status,
        "run_error": None if result.status in {"completed", "fallback", "clarification", "cancelled"} else result.status,
        "raw_retrieval_candidates": candidates,
        "retrieval_batches": batches,
        "retrieved_contexts": raw_contexts,
        "retrieval_layer": "tool_results_in_query_and_rank_order",
        "generation_contexts": generated_contexts,
        "generator_context_text": "\n\n".join(generated_contexts),
        "generation_records": copy.deepcopy(result.context_messages),
        "sources": [item.model_dump(mode="json") for item in result.sources],
        "answer_model": answer_model, "index_version": index_version,
        "answer_cost": copy.deepcopy(result.usage), "model_trace": copy.deepcopy(result.model_trace),
        "human_review": {"status": "pending", "reviewer": None, "conclusion": None},
    }


def prepare_evaluation(dataset: dict, capture: dict, *, pdf_path=None, manifest_path=None, validator=validate_dataset) -> list[dict]:
    gate = validator(dataset, pdf_path, require_reviewed=True)
    if not gate.get("formal_ready") or not gate.get("valid"):
        codes = ",".join(item["code"] for item in gate.get("errors", []))
        raise ValueError(codes or "review_required")
    gold = GoldDataset.model_validate(dataset)
    if manifest_path is None:
        raise ValueError("index_snapshot_required")
    manifest_path = Path(manifest_path)
    actual_index_hash = file_hash(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_index_documents(manifest_path, manifest, gold)
    if (capture.get("schema_version") != 1 or capture.get("capture_kind") != "graph_run"
        or capture.get("dataset_version") != gold.dataset_version
        or str(capture.get("document_sha256", "")).upper() != gold.source_document.sha256.upper()
        or capture.get("index_manifest_sha256") != actual_index_hash
        or str(capture.get("index_version", "")).upper() != actual_index_hash
        or not capture.get("index_version") or capture.get("answer_provider") != "ollama"
        or not capture.get("answer_model")):
        raise ValueError("capture_snapshot_mismatch")
    captured = capture.get("cases", [])
    by_id = {item["case_id"]: item for item in captured}
    if len(by_id) != len(captured) or set(by_id) != {case.case_id for case in gold.cases}:
        raise ValueError("capture_case_set_mismatch")
    records = []
    for case in gold.cases:
        item = by_id[case.case_id]
        if (item.get("question") != case.question
            or item.get("history_fixture", []) != [message.model_dump() for message in case.history_fixture]
            or item.get("answer_model") != capture["answer_model"] or item.get("index_version") != capture["index_version"]
            or not item.get("request_id") or not item.get("thread_id")
            or not isinstance(item.get("answer_cost"), dict) or item["answer_cost"].get("cloud_calls") != 0):
            raise ValueError("capture_question_or_model_mismatch")
        for key in ("retrieved_contexts", "generation_contexts"):
            values = item.get(key)
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError("capture_context_invalid")
        if not isinstance(item.get("response"), str) or not isinstance(item.get("raw_retrieval_candidates"), list):
            raise ValueError("capture_response_invalid")
        batches = item.get("retrieval_batches")
        if not isinstance(batches, list) or item.get("retrieval_layer") != "tool_results_in_query_and_rank_order":
            raise ValueError("capture_retrieval_layer_invalid")
        try:
            actual_contexts = [entry["content"] for batch in batches for entry in batch["results"]]
            generation_contexts = [entry["content"] for entry in item["generation_records"]]
        except (KeyError, TypeError):
            raise ValueError("capture_context_invalid") from None
        if actual_contexts != item["retrieved_contexts"] or generation_contexts != item["generation_contexts"]:
            raise ValueError("capture_context_layer_mismatch")
        if case.case_type == "answerable" and not item.get("user_input"):
            raise ValueError("capture_query_missing")
        records.append({**copy.deepcopy(item), "case_type": case.case_type,
                        "reference": case.reference_answer, "required_facts": case.required_facts,
                        "ordered_facts": case.ordered_facts, "forbidden_claims": case.forbidden_claims})
    return records


def metric_inputs(row: dict) -> dict:
    query, response, reference = row["user_input"], row["response"], row.get("reference")
    retrieved, generated = row["retrieved_contexts"], row["generation_contexts"]
    return {
        "answer_accuracy": {"user_input": query, "response": response, "reference": reference},
        "context_relevance": {"user_input": query, "retrieved_contexts": retrieved},
        "response_groundedness": {"response": response, "retrieved_contexts": generated},
        "context_precision": {"user_input": query, "reference": reference, "retrieved_contexts": retrieved},
        "context_recall": {"user_input": query, "reference": reference, "retrieved_contexts": retrieved},
    }


async def evaluate_record(row: dict, scorers: dict, *, timeout: float = 60, meter=None, progress=None) -> dict:
    result = copy.deepcopy(row)
    result["metrics"] = {}
    inputs = metric_inputs(row)
    for name in METRIC_NAMES:
        started = time.perf_counter()
        before = meter.snapshot() if meter else None
        metric = {"status": "scored", "value": None, "not_applicable_reason": None, "evaluation_error": None}
        if row.get("run_error"):
            metric.update(status="evaluation_error", evaluation_error="answer_pipeline_failed")
        elif row["case_type"] != "answerable":
            metric.update(status="not_applicable", not_applicable_reason="交互或无答案场景单独复核，不混入事实问答均值")
        elif meter and meter.calls >= meter.max_calls:
            metric.update(status="evaluation_error", evaluation_error="judge_call_budget_exceeded")
        elif name == "answer_accuracy" and not row.get("reference"):
            metric.update(status="not_applicable", not_applicable_reason="缺少可复核标准答案")
        elif name != "answer_accuracy" and not inputs[name]["retrieved_contexts"]:
            metric.update(status="not_applicable", not_applicable_reason="没有该层级的实际上下文，不能用标准答案补齐")
        else:
            try:
                raw = await asyncio.wait_for(scorers[name].ascore(**inputs[name]), timeout=timeout)
                value = raw.value
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError("invalid_score")
                metric["value"] = float(value)
                metric["raw_result"] = {"value": value, "reason": getattr(raw, "reason", None),
                                        "traces": getattr(raw, "traces", None)}
            except Exception as exc:
                metric.update(status="evaluation_error", evaluation_error=type(exc).__name__)
        metric["duration_ms"] = round((time.perf_counter() - started) * 1000)
        metric["cost"] = meter.difference(before) if meter else {"usage_source": "not_recorded"}
        result["metrics"][name] = metric
        if progress:
            progress({"event": "metric_complete", "case_id": row["case_id"], "metric": name,
                      "status": metric["status"], "value": metric["value"], "error": metric["evaluation_error"],
                      "cost": metric["cost"], "duration_ms": metric["duration_ms"]})
    # 字面探针只提示可能遗漏，不能替代语义判断或人工审核。
    normal = "".join(row["response"].split())
    result["literal_probe"] = {"potential_missing_facts": [fact for fact in row.get("required_facts", [])
                                                         if "".join(fact.split()) not in normal],
                                "is_semantic_verdict": False}
    result["human_review"] = {"status": "pending", "reviewer": None, "conclusion": None}
    return result


class LocalMeter:
    def __init__(self, base_url: str, max_calls: int):
        self.base_url = validate_local_base_url(base_url)
        self.max_calls = max_calls
        self.calls = self.prompt_tokens = self.completion_tokens = self.usage_records = 0
        self.call_trace = []
        self.request_started = {}

    async def request(self, request):
        expected = urlsplit(self.base_url)
        if (request.url.scheme, request.url.host, request.url.port) != (expected.scheme, expected.hostname, expected.port):
            raise ValueError("non_local_request_blocked")
        if request.url.path not in {"/v1/chat/completions", "/api/tags"}:
            raise ValueError("unexpected_local_endpoint")
        if request.url.path == "/v1/chat/completions":
            if self.calls >= self.max_calls:
                raise RuntimeError("judge_call_budget_exceeded")
            self.calls += 1
            self.request_started[id(request)] = time.perf_counter()

    async def response(self, response):
        if response.request.url.path != "/v1/chat/completions":
            return
        await response.aread()
        trace = {"status_code": response.status_code,
                 "duration_ms": round((time.perf_counter() - self.request_started.pop(id(response.request), time.perf_counter())) * 1000)}
        try:
            usage = response.json().get("usage", {})
            prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if (isinstance(prompt, int) and not isinstance(prompt, bool) and prompt >= 0
                and isinstance(completion, int) and not isinstance(completion, bool) and completion >= 0):
                self.prompt_tokens += prompt
                self.completion_tokens += completion
                self.usage_records += 1
                trace.update(prompt_tokens=prompt, completion_tokens=completion)
        except (ValueError, AttributeError):
            pass
        self.call_trace.append(trace)

    def snapshot(self):
        return {"model_calls": self.calls, "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
                "usage_records": self.usage_records}

    def difference(self, before=None):
        before = before or dict.fromkeys(self.snapshot(), 0)
        delta = {key: value - before[key] for key, value in self.snapshot().items()}
        delta.update(total_tokens=delta["prompt_tokens"] + delta["completion_tokens"], cloud_calls=0,
                     unknown_usage_calls=delta["model_calls"] - delta["usage_records"],
                     usage_source="provider" if delta["model_calls"] == delta["usage_records"] else "partial_provider")
        return delta


class JudgeRunError(RuntimeError):
    def __init__(self, cause: Exception, audit: dict):
        super().__init__(type(cause).__name__)
        self.audit = audit


async def run_judge(records: list[dict], *, model: str, base_url: str, timeout=60, max_calls=16, smoke=False, progress=None) -> dict:
    # 禁止 RAGAS 遥测。仅此离线函数导入评估依赖，生产请求不依赖它们。
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"
    if importlib.metadata.version("ragas") != PINNED_RAGAS:
        raise ValueError("ragas_version_mismatch")
    import httpx
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import AnswerAccuracy, ContextRelevance, ResponseGroundedness, ContextPrecision, ContextRecall

    meter = LocalMeter(base_url, max_calls)
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=timeout,
                                 event_hooks={"request": [meter.request], "response": [meter.response]}) as http:
        tags = await http.get(meter.base_url.split("/v1/")[0] + "/api/tags")
        tags.raise_for_status()
        installed = {item["name"] for item in tags.json().get("models", [])}
        if model not in installed:
            raise ValueError("judge_model_not_installed")
        client = AsyncOpenAI(base_url=meter.base_url, api_key="ollama", http_client=http, max_retries=0)
        answer_cost = meter.difference()
        before_judge = meter.snapshot()
        results = []
        try:
            if smoke:
                row = copy.deepcopy(records[0])
                started = time.perf_counter()
                try:
                    generated = await client.chat.completions.create(
                        model=model, temperature=0, max_tokens=256,
                        messages=[{"role": "system", "content": "只根据给定上下文简短回答，不添加事实。"},
                                  {"role": "user", "content": row["user_input"] + "\n上下文：" + row["generation_contexts"][0]}],
                    )
                finally:
                    answer_cost = meter.difference()
                    before_judge = meter.snapshot()
                row["response"] = generated.choices[0].message.content or ""
                row["answer_cost"] = answer_cost
                row["answer_duration_ms"] = round((time.perf_counter() - started) * 1000)
                row["answer_model"] = model
                records = [row]
            # Instructor 的重试也受每项超时及总 HTTP 调用预算限制。
            llm = llm_factory(model, client=client, temperature=0, max_tokens=1024, max_retries=1)
            scorers = dict(zip(METRIC_NAMES, [
                AnswerAccuracy(llm=llm, max_retries=1), ContextRelevance(llm=llm, max_retries=1),
                ResponseGroundedness(llm=llm, max_retries=1), ContextPrecision(llm=llm), ContextRecall(llm=llm)]))
            for row in records:
                results.append(await evaluate_record(row, scorers, timeout=timeout, meter=meter, progress=progress))
        except Exception as exc:
            raise JudgeRunError(exc, {"case_results": results, "unscored_inputs": records,
                "judge_cost": meter.difference(before_judge), "smoke_answer_cost": answer_cost,
                "local_call_trace": meter.call_trace}) from None
        return {"case_results": results, "judge_cost": meter.difference(before_judge),
                "smoke_answer_cost": answer_cost, "local_call_trace": meter.call_trace,
                "installed_judge_model": model,
                "judge_model_digest": next(item["digest"] for item in tags.json()["models"] if item["name"] == model)}


def save_report(report: dict) -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_ROOT / f"{report['run_id']}.json"
    with path.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="本地离线五项 RAGAS 评估；不是在线评分器")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--inputs", type=Path, help="实际 Graph 输出快照 JSON，禁止拿标准答案冒充系统回答")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--index-manifest", type=Path)
    parser.add_argument("--judge-model", help="已安装的 Ollama 模型名；不自动下载")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1/")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--max-calls", type=int, default=16)
    parser.add_argument("--smoke", action="store_true", help="仅使用内置合成来源做一题兼容性冒烟，不是正式题集评分")
    parser.add_argument("--progress", action="store_true", help="逐项输出状态与用量，不输出提示词或文档正文")
    args = parser.parse_args(argv)
    report = {"run_id": f"eval-{uuid4()}", "started_at": datetime.now(timezone.utc).isoformat(),
              "mode": "synthetic_compatibility_smoke" if args.smoke else "formal_offline",
              "formal_acceptance": False, "status": "failed", "ragas_version": PINNED_RAGAS,
              "judge_model": args.judge_model, "independent_judge": False, "errors": [], "case_results": []}
    report["judge_configuration"] = {"temperature": 0, "max_tokens": 1024, "instructor_max_retries": 1,
                                     "rating_max_retries": 1, "per_metric_timeout_seconds": args.timeout,
                                     "max_http_model_calls": args.max_calls, "trust_env": False,
                                     "ragas_telemetry": False, "langsmith_tracing": False}
    report["dependency_versions"] = {}
    for name in ("ragas", "instructor", "openai", "langchain", "langchain-community", "langchain-core",
                 "langchain-openai", "langchain-text-splitters", "httpx", "pydantic", "PyMuPDF"):
        try:
            report["dependency_versions"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            report["dependency_versions"][name] = None
    started = time.perf_counter()
    try:
        if not 1 <= args.timeout <= 120 or not 1 <= args.max_calls <= 1000:
            raise ValueError("invalid_runtime_budget")
        base_url = validate_local_base_url(args.base_url)
        if args.smoke:
            if args.inputs or args.index_manifest or args.pdf or args.dataset != DEFAULT_DATASET:
                raise ValueError("smoke_must_not_read_formal_inputs")
            records = [{"case_id": "SMOKE-1", "case_type": "answerable", "user_input": "测试记录默认保留多久？",
                        "response": "", "reference": "测试记录默认保留三年。", "required_facts": ["三年"],
                        "retrieved_contexts": ["测试记录默认保留三年。"],
                        "generation_contexts": ["测试记录默认保留三年。"], "run_error": None}]
            report["dataset_version"] = "synthetic-smoke-not-gold"
            report["answer_model"] = args.judge_model
            report["limitations"] = ["合成来源的一题兼容性测试；回答与 Judge 使用同一模型，只能作为探索性结果。"]
        else:
            dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
            # 即使缺少 --inputs 或评估依赖也先执行题集关卡，草案不可绕过。
            gate = validate_dataset(dataset, args.pdf, require_reviewed=True)
            if not gate["formal_ready"]:
                raise ValueError(",".join(error["code"] for error in gate["errors"]) or "review_required")
            if not args.inputs:
                raise ValueError("actual_capture_required")
            capture = json.loads(args.inputs.read_text(encoding="utf-8"))
            records = prepare_evaluation(dataset, capture, pdf_path=args.pdf, manifest_path=args.index_manifest)
            report.update(dataset_version=dataset["dataset_version"], document_sha256=dataset["source_document"]["sha256"],
                          index_version=capture["index_version"], index_manifest_sha256=capture["index_manifest_sha256"],
                          answer_model=capture["answer_model"], independent_judge=args.judge_model != capture["answer_model"],
                          capture_sha256=file_hash(args.inputs), dataset_sha256=file_hash(args.dataset))
            report["limitations"] = ["指标不是设备操作安全结论，人工必答点审核仍需另行完成。"]
        if not args.judge_model:
            raise ValueError("explicit_local_judge_required")
        report.update(asyncio.run(run_judge(records, model=args.judge_model, base_url=base_url,
                                           timeout=args.timeout, max_calls=args.max_calls, smoke=args.smoke,
                                           progress=(lambda event: print(json.dumps(event, ensure_ascii=True), flush=True)) if args.progress else None)))
        failures = sum(item["status"] == "evaluation_error" for row in report["case_results"] for item in row["metrics"].values())
        report.update(status="completed_with_errors" if failures else "completed", metric_error_count=failures,
                      human_review_status="pending")
    except Exception as exc:
        if isinstance(exc, JudgeRunError):
            report.update(exc.audit)
        # 固定闸门代码可以公开；第三方异常只记录类型，避免泄露上下文/凭据。
        known = {"review_required", "actual_capture_required", "explicit_local_judge_required", "judge_model_not_installed",
                 "index_snapshot_required", "ragas_version_mismatch", "capture_snapshot_mismatch", "invalid_runtime_budget",
                 "smoke_must_not_read_formal_inputs"}
        detail = str(exc)
        report["errors"].append({"code": detail if detail in known or isinstance(exc, JudgeRunError) else type(exc).__name__})
    report["duration_ms"] = round((time.perf_counter() - started) * 1000)
    path = save_report(report)
    print(json.dumps({"status": report["status"], "mode": report["mode"], "report_path": str(path),
                      "errors": report["errors"], "formal_acceptance": False}, ensure_ascii=True))
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
