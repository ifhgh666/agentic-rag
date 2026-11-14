"""已审核题集的真实 Graph 批量采集；只运行本机模型和正式索引的隔离快照。"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.config import Settings
from app.core.conversation import ConversationTurn
from scripts.evaluate_v4_ragas import capture_graph_result, file_hash, prepare_evaluation, validate_index_documents
from scripts.replay_v3_6_q3 import (
    BACKEND_ROOT, OUTPUT_ROOT as SNAPSHOT_ROOT, clone_index_readonly, digest,
    protected_files, validate_local_capture_settings, verified_bm25_cache,
)
from scripts.validate_v4_gold_dataset import DEFAULT_DATASET, GoldDataset, validate_dataset


OUTPUT_ROOT = BACKEND_ROOT / "tmp/v4-captures"


class BatchCaptureProvider:
    """额外的整批硬上限；Graph 原有每请求/节点上限仍然有效。"""

    def __init__(self, delegate, *, max_calls):
        self.delegate, self.max_calls = delegate, max_calls
        self.calls = []

    def complete(self, messages, *, tools=None):
        if len(self.calls) >= self.max_calls:
            raise RuntimeError("capture_batch_budget_exceeded")
        started = time.perf_counter()
        entry = {"usage_recorded": False}
        self.calls.append(entry)
        try:
            result = self.delegate.complete(messages, tools=tools)
            entry.update(provider=result.provider, model=result.model,
                         prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens,
                         usage_recorded=result.prompt_tokens is not None and result.completion_tokens is not None)
            return result
        except Exception as exc:
            entry["error_type"] = type(exc).__name__
            raise
        finally:
            entry["duration_ms"] = round((time.perf_counter() - started) * 1000)


def aggregate_cost(turns):
    usages = [turn["answer_cost"] for turn in turns]
    keys = ("model_calls", "cloud_calls", "prompt_tokens", "completion_tokens", "total_tokens", "duration_ms")
    result = {key: sum(usage.get(key, 0) for usage in usages) for key in keys}
    result["budget_exceeded"] = any(usage.get("budget_exceeded", False) for usage in usages)
    result["usage_source"] = "provider" if all(usage.get("usage_source") == "provider" for usage in usages) else "see_turns"
    return result


def capture_case(service, case, *, index_version, answer_model, progress=None):
    thread = f"v4-formal-{case['case_id']}-{uuid4()}"
    history = case.get("history_fixture", [])
    if history:
        state = service.memory.thread_state(thread)
        service.memory.update(thread, expected_version=state.state_version,
                              recent_messages=[ConversationTurn(**item) for item in history])
    steps = case.get("flow_steps") or [{"question": case["question"], "action": "auto"}]
    turns, checks = [], []
    for number, step in enumerate(steps, 1):
        result = service.run(step["question"], thread_id=thread, action=step["action"])
        turn = capture_graph_result({**case, "question": step["question"]}, result,
                                    index_version=index_version, answer_model=answer_model)
        turn.update(action=step["action"], turn_number=number, actual_pending_query=service.memory.pending(thread),
                    analysis_relation=result.analysis_relation, tool_trace=result.tool_trace,
                    verification=result.evaluation.model_dump(mode="json") if result.evaluation else None)
        turns.append(turn)
        if case["case_type"] == "clarification_flow":
            checks.append({"turn_number": number, "is_semantic_verdict": False,
                "status_matches": result.status == step["expected_status"],
                "pending_matches": turn["actual_pending_query"] == step.get("expected_pending_query", ""),
                "retrieval_matches": bool(result.retrieval_batches) == step["retrieval_expected"],
                "relation_matches": step.get("expected_relation") is None or result.analysis_relation == step["expected_relation"],
                "questions_match_literally": result.questions == step.get("expected_questions", [])})
        if progress:
            progress({"event": "answer_turn_complete", "case_id": case["case_id"], "turn": number,
                      "status": result.status, "model_calls": result.usage.get("model_calls"),
                      "total_tokens": result.usage.get("total_tokens")})
    row = capture_graph_result(case, result, index_version=index_version, answer_model=answer_model)
    row.update(flow_turns=turns, flow_checks=checks, answer_cost=aggregate_cost(turns),
               analysis_relation=result.analysis_relation, tool_trace=result.tool_trace,
               verification=turns[-1]["verification"])
    if case["case_type"] == "answerable" and result.status == "clarification":
        row["run_error"] = "unexpected_clarification"
    return row


def checkpoint(path, report):
    # 只覆盖本次 UUID 命名的输出，不修改输入题集或知识库文件。
    temporary = path.with_suffix(".partial")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def close_snapshot(index):
    # VectorDbManager 不是客户端；先关闭实际 QdrantClient 再清理 Windows 临时目录。
    index.vector_db.client.close()


def capture_batch(dataset, settings, *, progress=None):
    validate_local_capture_settings(settings)
    gate = validate_dataset(dataset, require_reviewed=True)
    if not gate["formal_ready"]:
        raise ValueError("review_required")
    gold = GoldDataset.model_validate(dataset)
    os.environ.update(HF_HUB_OFFLINE="1", LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false", RAGAS_DO_NOT_TRACK="true")
    from app.knowledge.stores import DocumentStore
    from app.knowledge.retrieval import ContextBuilder
    from app.knowledge.embeddings import EmbeddingService
    from app.core.answering import AnswerEvaluator
    from app.core.answering import AnswerGenerator
    from app.rag.graph import AgentGraphService
    from app.knowledge.index import IndexStore
    from app.core.model_provider import OllamaProvider
    from app.knowledge.retrieval import Retriever
    from app.knowledge.embeddings import SparseEmbeddingService
    from fastembed import SparseTextEmbedding

    class SnapshotIndex(IndexStore):
        def _load_and_migrate_legacy_index(self):
            if not self.vector_db.ready:
                raise RuntimeError("snapshot_not_ready_rebuild_forbidden")

        def rebuild(self, children):
            raise RuntimeError("capture_rebuild_forbidden")

    paths = protected_files(settings)
    before = {name: digest(path) for name, path in paths.items()}
    manifest_path = settings.data_dir / "index/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_index_documents(manifest_path, manifest, gold)
    index_version = file_hash(manifest_path)
    sparse_cache = verified_bm25_cache(settings)
    delegate = OllamaProvider(settings)
    if settings.ollama_model not in delegate.check_connection():
        raise ValueError("answer_model_not_installed")
    requests = sum(len(case.get("flow_steps") or [None]) for case in dataset["cases"])
    provider = BatchCaptureProvider(delegate, max_calls=requests * settings.max_llm_calls_per_request)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    artifact = OUTPUT_ROOT / f"graph-{uuid4()}.json"
    report = {"schema_version": 1, "capture_kind": "graph_run", "capture_transport": "isolated_formal_index_graph",
              "dataset_version": dataset["dataset_version"], "document_sha256": gold.source_document.sha256,
              "index_version": index_version, "index_manifest_sha256": index_version,
              "answer_provider": "ollama", "answer_model": settings.ollama_model,
              "started_at": datetime.now(timezone.utc).isoformat(), "status": "capturing", "cases": [],
              "workbench_ui_run": False, "formal_acceptance": False, "protected_hashes": before,
              "capture_call_limit": provider.max_calls, "source_sparse_wordlist_sha256": digest(sparse_cache / "english.txt")}
    checkpoint(artifact, report)
    try:
        with TemporaryDirectory(prefix="v4-formal-", dir=SNAPSHOT_ROOT) as directory:
            snapshot = Path(directory)
            clone_index_readonly(settings, snapshot)
            local = settings.model_copy(update={"data_dir": snapshot, "qdrant_db_path": snapshot / "qdrant",
                                               "embedding_cache_dir": settings.embedding_cache_path.resolve()})
            store = DocumentStore(snapshot)
            embedding = EmbeddingService(local)
            index = SnapshotIndex(snapshot, embedding, store)
            try:
                index.vector_db.sparse_embedder = SparseEmbeddingService(local, model_factory=lambda model_name:
                    SparseTextEmbedding(model_name=model_name, specific_model_path=str(sparse_cache), local_files_only=True,
                                        disable_stemmer=settings.sparse_offline_fallback))
                if not index.ready or index.vector_db.count != manifest["point_count"] or index.version.upper() != index_version:
                    raise ValueError("snapshot_index_mismatch")
                # 所有资源先加载检查，再开始问答；不切换词表、stemmer 或 Dense 模型。
                embedding.embed_one("PX-200")
                index.vector_db.sparse_embedder.embed_one("PX-200")
                service = AgentGraphService(local, Retriever(local, index, store), ContextBuilder(local, store),
                                            AnswerGenerator(local, provider), AnswerEvaluator(), store)
                for case in dataset["cases"]:
                    if before != {name: digest(path) for name, path in paths.items()}:
                        raise ValueError("protected_files_changed")
                    row = capture_case(service, case, index_version=index_version, answer_model=settings.ollama_model,
                                       progress=progress)
                    report["cases"].append(row)
                    report["provider_call_trace"] = provider.calls
                    checkpoint(artifact, report)
                prepare_evaluation(dataset, report, manifest_path=manifest_path)
                report["status"] = "captured"
            finally:
                close_snapshot(index)
    except Exception as exc:
        report.update(status="capture_failed", error_type=type(exc).__name__)
        if isinstance(exc, (ValueError, RuntimeError)) and str(exc) in {
            "protected_files_changed", "snapshot_index_mismatch", "capture_batch_budget_exceeded"}:
            report["error_code"] = str(exc)
        raise
    finally:
        after = {name: digest(path) for name, path in paths.items()}
        report.update(protected_files_unchanged=before == after, provider_call_trace=provider.calls,
                      completed_at=datetime.now(timezone.utc).isoformat(),
                      unknown_usage_calls=sum(not call["usage_recorded"] for call in provider.calls))
        checkpoint(artifact, report)
        if progress:
            progress({"event": "capture_finished", "status": report["status"], "artifact": str(artifact),
                      "case_count": len(report["cases"]), "model_calls": len(provider.calls),
                      "protected_files_unchanged": before == after})
    if not report["protected_files_unchanged"]:
        raise ValueError("protected_files_changed")
    return artifact


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-local", action="store_true")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args(argv)
    if not args.capture_local:
        parser.error("需显式指定 --capture-local，不默认启动模型")
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    capture_batch(dataset, Settings(), progress=lambda event: print(json.dumps(event, ensure_ascii=True), flush=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
