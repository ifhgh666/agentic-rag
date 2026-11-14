"""Q3 取证工具；默认离线模拟反例，显式模式仅运行一次本地模型链路。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from uuid import uuid4
from app.config import Settings
from app.core.answering import AnswerEvaluator, format_evidence_records, AnswerGenerator
from app.core.model_provider import ModelResult, OllamaProvider


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE = BACKEND_ROOT / "tests/fixtures/v3_6_q3_case.json"
OUTPUT_ROOT = BACKEND_ROOT / "tmp/v3-6"
_LITERAL_MODEL_ID = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,12}[-_]?\d{2,}[A-Za-z0-9-]*(?![A-Za-z0-9])")


def validate_sparse_query_scope(query: str) -> None:
    """允许中文及字面型号；不把空英文停用词表的结果推广到任意英文。"""
    without_ids = _LITERAL_MODEL_ID.sub("", query)
    if any(character.isascii() and character.isalpha() for character in without_ids):
        raise ValueError("离线等价核对仅支持中文及字面型号，不支持一般英文查询")


def inspect_q3_steps(answer: str, case: dict) -> dict:
    """固定样例的字面定位，不是生产规则或通用语义评分。"""
    body = answer.split("\n\n依据：", 1)[0]
    normalized = "".join(body.split())
    matches = []
    for step in case["expected_sequence"]:
        positions = [normalized.find(term) for term in step["probe_terms"] if term in normalized]
        matches.append({"step": step["id"], "position": min(positions) if positions else None})
    present = [item["position"] for item in matches if item["position"] is not None]
    missing = [item["step"] for item in matches if item["position"] is None]
    return {"kind": "fixture_literal_probe_not_semantic_evaluation", "answer_body": body,
            "missing_steps": missing, "ordered": not missing and present == sorted(present),
            "matches": matches, "human_semantic_review_required": True}


class FixedResponseProvider:
    """只模拟模型输出；经过真实 AnswerGenerator 校验，不建立网络连接。"""

    def __init__(self, response: dict):
        self.response = copy.deepcopy(response)
        self.calls: list[dict] = []

    def complete(self, messages, *, tools=None):
        self.calls.append({"messages": copy.deepcopy(messages), "response": copy.deepcopy(self.response)})
        return ModelResult(json.dumps(self.response, ensure_ascii=False), "fixture", "fixed-q3-counterexample")


def replay_counterexample(case: dict) -> dict:
    records = format_evidence_records(copy.deepcopy(case["records"]))
    provider = FixedResponseProvider(case["counterexample"]["model_response"])
    generator = AnswerGenerator(Settings(_env_file=None), provider)
    answer, ids, trace = generator.generate_grounded_with_result(case["question"], records, procedure_required=True)
    context = "\n\n".join(item["content"] for item in records)
    verification = AnswerEvaluator().evaluate(case["question"], answer, context, records=records)
    probe = inspect_q3_steps(answer, case)
    pages = [item["page_start"] for item in records if item["citation_id"] in ids]
    return {"schema_version": 1, "capture_kind": "deterministic_generator_counterexample",
            "case_id": case["case_id"], "question": case["question"], "answer": answer,
            "generation_records": records, "model_calls": provider.calls,
            "validation_status": trace["validation_status"], "model_trace": trace,
            "cited_ids": ids, "cited_pages": pages, "verification": verification.model_dump(mode="json"),
            "step_probe": probe, "live_model_calls": 0, "cloud_calls": 0,
            "counterexample_reproduced": trace["validation_status"] == "accepted"
                and probe["missing_steps"] == ["disconnect_load", "wait_discharge"]}


def validate_local_capture_settings(settings: Settings) -> None:
    endpoint = urlsplit(settings.ollama_base_url)
    if (settings.llm_provider != "ollama" or endpoint.scheme != "http"
        or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}
        or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
        or endpoint.path.rstrip("/") or not settings.ollama_model.strip()):
        raise ValueError("真机诊断只允许已配置的本机 Ollama，不自动下载或回退云模型")
    if settings.effective_embedding_backend != "fastembed" or settings.sparse_model != "Qdrant/bm25":
        raise ValueError("必须保持正式索引的 Dense 模型和 BM25 类型，不使用确定性向量代替")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verified_bm25_cache(settings: Settings) -> Path:
    """诊断使用真实默认词表；绕开 FastEmbed 对不存在的 mock.file 的离线检查。"""
    from fastembed.common.utils import define_cache_dir
    from huggingface_hub import snapshot_download

    if settings.sparse_model != "Qdrant/bm25" or settings.sparse_offline_fallback:
        raise ValueError("该诊断要求当前默认 BM25 编码器，不切换离线空词表")
    cache_root = define_cache_dir(None)
    model_root = cache_root / "models--Qdrant--bm25"
    directory = Path(snapshot_download(repo_id=settings.sparse_model, cache_dir=str(cache_root),
                                     local_files_only=True, allow_patterns=["english.txt"]))
    metadata = json.loads((model_root / "files_metadata.json").read_text(encoding="utf-8"))
    word_file = directory / "english.txt"
    relative = str(word_file.relative_to(model_root))
    expected = metadata[relative]
    data = word_file.read_bytes()
    blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if len(data) != expected["size"] or blob != expected["blob_id"]:
        raise ValueError("默认停用词文件不匹配下载元数据，不运行模型问答")
    return directory


def protected_files(settings: Settings) -> dict[str, Path]:
    root = settings.data_dir.resolve()
    result = {f"data/{name}": root / name for name in (
        "documents.json", "parents.json", "children.json", "index/children.json", "index/manifest.json",
    )}
    result["backend/.env"] = BACKEND_ROOT / ".env"
    result["gold-cases-v1.json"] = BACKEND_ROOT.parent / "specs/004-query-clarification-ragas/gold-cases-v1.json"
    for path in (BACKEND_ROOT / "app").rglob("*.py"):
        result[f"backend/{path.relative_to(BACKEND_ROOT).as_posix()}"] = path
    for document in json.loads(result["data/documents.json"].read_text(encoding="utf-8")):
        if document["status"] == "ready":
            source = Path(document["source_path"]).resolve()
            if not source.is_relative_to(root / "documents") or not source.is_file():
                raise ValueError("正式源文件不在预期文档目录内")
            result[f"source/{document['document_id']}"] = source
            markdown = Path(document["markdown_path"]) if document.get("markdown_path") else None
            if markdown and markdown.is_file():
                result[f"markdown/{document['document_id']}"] = markdown
    for path in settings.qdrant_path.resolve().rglob("*"):
        if path.is_file() and path.name != ".lock":
            result[f"qdrant/{path.relative_to(settings.qdrant_path.resolve()).as_posix()}"] = path
    return result


def clone_index_readonly(settings: Settings, target: Path) -> None:
    """SQLite 使用 mode=ro 的一致性备份，绝不打开生产 Qdrant 客户端。"""
    target = target.resolve()
    if not target.is_relative_to(OUTPUT_ROOT.resolve()) or target == OUTPUT_ROOT.resolve():
        raise ValueError("快照必须位于本工具的临时子目录")
    for name in ("documents.json", "parents.json", "children.json", "index/children.json", "index/manifest.json"):
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(settings.data_dir / name, destination)
    qdrant_root = settings.qdrant_path.resolve()
    shutil.copytree(qdrant_root, target / "qdrant", ignore=shutil.ignore_patterns(
        ".lock", "*.sqlite", "*.sqlite-wal", "*.sqlite-shm", "*.sqlite-journal"), dirs_exist_ok=True)
    databases = list(qdrant_root.rglob("*.sqlite"))
    if not databases:
        raise ValueError("正式 Qdrant 数据库不存在；诊断不迁移、不重建")
    for database in databases:
        destination = target / "qdrant" / database.relative_to(qdrant_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        output = sqlite3.connect(destination)
        try:
            source.backup(output)
        finally:
            output.close()
            source.close()


class BoundedCaptureProvider:
    def __init__(self, delegate: OllamaProvider):
        self.delegate = delegate
        self.calls: list[dict] = []

    def complete(self, messages, *, tools=None):
        if len(self.calls) >= 2:
            raise RuntimeError("本次单题诊断已达到两次本地模型调用上限，停止取证")
        entry = {"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)}
        self.calls.append(entry)
        response = self.delegate.complete(messages, tools=tools)
        entry["response"] = asdict(response)
        return response


def capture_local_once(case: dict, settings: Settings, *, use_configured_sparse: bool = False) -> dict:
    validate_local_capture_settings(settings)
    # 导入前关闭可选的外部追踪与下载；没有 Judge，也不读取云模型密钥。
    os.environ.update({"HF_HUB_OFFLINE": "1", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"})
    from app.knowledge.stores import DocumentStore
    from app.knowledge.retrieval import ContextBuilder
    from app.knowledge.embeddings import EmbeddingService
    from app.rag.graph import AgentGraphService
    from app.knowledge.index import IndexStore
    from app.knowledge.retrieval import Retriever
    from app.knowledge.embeddings import SparseEmbeddingService
    from fastembed import SparseTextEmbedding
    from scripts.evaluate_v4_ragas import capture_graph_result

    class SnapshotIndex(IndexStore):
        def _load_and_migrate_legacy_index(self):
            if not self.vector_db.ready:
                raise RuntimeError("正式索引快照无 Point；禁止迁移或重建")

        def rebuild(self, children):
            raise RuntimeError("取证过程禁止重建任何索引")

    paths = protected_files(settings)
    before = {name: digest(path) for name, path in paths.items()}
    # 在任何问答模型调用前验证实际词表，启动失败也不会消耗分析调用。
    sparse_cache = verified_bm25_cache(settings) if use_configured_sparse else None
    manifest = json.loads((settings.data_dir / "index/manifest.json").read_text(encoding="utf-8"))
    source_key = f"source/{case['source']['document_id']}"
    if before.get(source_key) != case["source"]["pdf_sha256"]:
        raise ValueError("正式 PDF 已变化，不沿用固定样例")
    provider = OllamaProvider(settings)
    if settings.ollama_model not in provider.check_connection():
        raise RuntimeError("配置的 Ollama 模型未安装；本工具不自动下载")
    capture = BoundedCaptureProvider(provider)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="index-snapshot-", dir=OUTPUT_ROOT) as directory:
        snapshot = Path(directory)
        clone_index_readonly(settings, snapshot)
        overrides = {"data_dir": snapshot, "qdrant_db_path": snapshot / "qdrant",
                     "embedding_cache_dir": settings.embedding_cache_path.resolve()}
        if not use_configured_sparse:
            overrides.update({"sparse_offline_fallback": True, "sparse_model_path": snapshot / "bm25"})
        local = settings.model_copy(update=overrides)
        store = DocumentStore(snapshot)
        index = SnapshotIndex(snapshot, EmbeddingService(local), store)
        try:
            if sparse_cache:
                index.vector_db.sparse_embedder = SparseEmbeddingService(local, model_factory=lambda model_name:
                    SparseTextEmbedding(model_name=model_name, specific_model_path=str(sparse_cache),
                                        local_files_only=True, disable_stemmer=settings.sparse_offline_fallback))
            if not index.ready or index.vector_db.count != manifest["point_count"]:
                raise RuntimeError(f"快照索引未就绪：{index.rebuild_reason}")
            service = AgentGraphService(local, Retriever(local, index, store), ContextBuilder(local, store),
                AnswerGenerator(local, capture), AnswerEvaluator(), store)
            result = service.run(case["question"], thread_id=f"v3-6-diagnostic-{uuid4()}")
            exported = capture_graph_result(case, result, index_version=index.version, answer_model=settings.ollama_model)
            # 快照离线 BM25 与默认的 stemmer 查询向量必须对本次每个查询等价。
            # 若不等价则不把此结果标为可比的正式索引快照诊断。
            reference_options = {"local_files_only": True, "disable_stemmer": settings.sparse_offline_fallback}
            if not use_configured_sparse:
                reference_options["specific_model_path"] = str(local.sparse_model_path)
            elif sparse_cache:
                reference_options["specific_model_path"] = str(sparse_cache)
            baseline_encoder = SparseTextEmbedding(model_name=settings.sparse_model, **reference_options)
            equivalent = []
            for batch in result.retrieval_batches:
                query = batch["query"]
                validate_sparse_query_scope(query)
                actual = index.vector_db.sparse_embedder.embed_one(query)
                reference = index.vector_db.sparse_embedder._to_sparse_vector(next(baseline_encoder.embed([query])))
                equal = actual.model_dump() == reference.model_dump()
                equivalent.append({"query": query, "equivalent": equal})
                if not equal:
                    raise ValueError("离线 Sparse 查询与配置的默认 tokenizer 不等价")
            exported.update({"schema_version": 1, "capture_kind": "formal_index_snapshot_graph_run",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "workbench_ui_run": False, "model_calls": capture.calls,
                "verification": result.evaluation.model_dump(mode="json") if result.evaluation else None,
                "step_probe": inspect_q3_steps(result.final_answer, case),
                "context_threshold": result.context_token_threshold,
                "snapshot_note": "复用正式索引的 SQLite 一致性副本及现有 Parent；没有重解析或重建。离线 BM25 对本次中文及字面型号查询逐一核对向量等价，不证明任意英文查询等价。",
                "configured_sparse_encoder": use_configured_sparse,
                "sparse_query_equivalence": equivalent, "formal_manifest": manifest,
                "protected_hashes_before": before})
        finally:
            index.vector_db.client.close()
    after = {name: digest(path) for name, path in paths.items()}
    exported["protected_hashes_after"] = after
    exported["protected_files_unchanged"] = before == after
    if before != after:
        raise RuntimeError("保护文件发生变化；不得报告为只读取证，请检查并发操作")
    return exported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-local", action="store_true", help="显式运行一次当前本地模型链路，最多两次调用")
    parser.add_argument("--strict", action="store_true", help="仅重放：生成器仍接受固定漏步骤反例时返回退出码 1")
    args = parser.parse_args()
    if args.capture_local and args.strict:
        parser.error("真机诊断不与固定反例的严格失败模式混用")
    case = json.loads(DEFAULT_CASE.read_text(encoding="utf-8"))
    output = capture_local_once(case, Settings()) if args.capture_local else replay_counterexample(case)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_ROOT / ("local-capture.json" if args.capture_local else "counterexample.json")
    # 使用独立名字保留已有诊断，避免重复命令覆盖用户已查看的结果。
    if path.exists():
        path = path.with_name(f"{path.stem}-{uuid4().hex[:8]}.json")
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"capture_kind": output["capture_kind"], "artifact": str(path.resolve()),
        "missing_steps_literal_probe": output["step_probe"]["missing_steps"],
        "human_semantic_review_required": True,
        "usage": output.get("answer_cost", {"live_model_calls": 0, "cloud_calls": 0}),
        "protected_files_unchanged": output.get("protected_files_unchanged"),
        "verification": output["verification"]}, ensure_ascii=False))
    if args.strict and output.get("counterexample_reproduced"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
