"""V3-4: rebuild the real sample PDF in an isolated index and ask four baseline questions with local Ollama."""

import json
import re
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from app.config import Settings
from app.knowledge.chunker import chunk_document
from app.knowledge.pdf_parser import PdfParser
from app.knowledge.stores import DocumentStore
from app.knowledge.retrieval import ContextBuilder, Retriever
from app.knowledge.embeddings import EmbeddingService
from app.core.answering import AnswerEvaluator, AnswerGenerator
from app.rag.graph import AgentGraphService
from app.knowledge.index import IndexStore
from app.core.model_provider import create_provider
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument


SAMPLE_PDF = Path(__file__).resolve().parents[2] / "output" / "pdf" / "rag-test-knowledge-document.pdf"
MODEL_CACHE = Path(__file__).resolve().parents[1] / "data" / "models"
CASES = [
    ("Q1", "设备上电前需要检查什么？", [r"接地", r"负载", r"198", r"242", r"急停"]),
    ("Q2", "PX-200 的过流保护阈值是多少？", [r"16\s*A", r"100\s*ms"]),
    ("Q4", "运行记录默认保留多久？", [r"三年|3\s*年", r"先进先出"]),
    ("Q5", "设备多久进行一次维护？", [r"六个月|6\s*个月"]),
]


class CaptureProvider:
    def __init__(self, delegate):
        self.delegate = delegate
        self.last_content = ""

    def complete(self, messages, *, tools=None):
        result = self.delegate.complete(messages, tools=tools)
        self.last_content = result.content
        return result


def main(only: str | None = None, threshold: int | None = None) -> dict:
    configured = Settings()
    if configured.llm_provider != "ollama":
        raise RuntimeError("V3-4 真机验收只能使用本地 Ollama")
    if not SAMPLE_PDF.is_file():
        raise FileNotFoundError(SAMPLE_PDF)
    with TemporaryDirectory(prefix="v3-4-baseline-") as temp_dir:
        root = Path(temp_dir)
        settings = configured.model_copy(update={
            "data_dir": root,
            "qdrant_db_path": root / "qdrant",
            "embedding_backend": "fastembed",
            "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "embedding_cache_dir": MODEL_CACHE,
            "sparse_offline_fallback": True,
            "sparse_model_path": root / "bm25",
            **({"base_token_threshold": threshold, "token_growth_factor": 0.0} if threshold is not None else {}),
        })
        settings.ensure_data_dirs()
        pdf = SAMPLE_PDF.read_bytes()
        document_id = uuid4()
        parsed = PdfParser().parse(pdf)
        parents, children = chunk_document(document_id, parsed, settings)
        store = DocumentStore(root)
        store.save_document(KnowledgeDocument(
            document_id=document_id, filename=SAMPLE_PDF.name,
            status=DocumentStatus.ready, size_bytes=len(pdf), uploaded_at=utc_now(),
            parent_count=len(parents), child_count=len(children),
        ))
        store.replace_chunks(document_id, parents, children)
        index = IndexStore(root, EmbeddingService(settings), document_store=store)
        try:
            index.rebuild(children)
            retriever = Retriever(settings, index, store)
            capture = CaptureProvider(create_provider(settings))
            service = AgentGraphService(
                settings=settings, retriever=retriever, context_builder=ContextBuilder(settings, store),
                generator=AnswerGenerator(settings, capture), evaluator=AnswerEvaluator(), document_store=store,
            )
            outcomes = []
            for key, question, patterns in CASES:
                if only and key != only:
                    continue
                result = service.run(question, thread_id=f"v3-4-{key}")
                answer_main = result.final_answer.split("\n\n依据：", 1)[0]
                missing = [pattern for pattern in patterns if not re.search(pattern, answer_main, re.IGNORECASE)]
                outcomes.append({
                    "question": key,
                    "answer": result.final_answer,
                    "passed": result.status == "completed" and not missing and bool(result.sources),
                    "missing_patterns": missing,
                    "sources": [item.filename for item in result.sources],
                    "model_calls": [{"node": item.get("node"), "validation_status": item.get("validation_status")} for item in result.model_trace],
                    "retrieved_count": len(result.retrieved_results),
                    "context_facts": {pattern: bool(re.search(pattern, result.context, re.IGNORECASE)) for pattern in patterns},
                    "usage": result.usage,
                    "raw_model_response_if_failed": capture.last_content[:3000] if missing or result.status != "completed" else "",
                })
            report = {"index_parents": len(parents), "index_children": len(children), "cases": outcomes}
            print(json.dumps(report, ensure_ascii=True))
            if not all(item["passed"] for item in outcomes):
                raise AssertionError("四道基线题尚未全部通过；见上方逐题输出")
            if any(item["usage"]["model_calls"] > 2 or item["usage"]["cloud_calls"] for item in outcomes):
                raise AssertionError("简单基线题超过 2 次模型调用，或出现云端模型调用")
            return report
        finally:
            index.vector_db.client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=[item[0] for item in CASES])
    parser.add_argument("--threshold", type=int)
    arguments = parser.parse_args()
    main(arguments.only, arguments.threshold)
