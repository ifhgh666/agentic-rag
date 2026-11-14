from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Settings
from app.knowledge.chunker import chunk_document
from app.knowledge.pdf_parser import PdfParser
from app.knowledge.stores import DocumentStore
from app.knowledge.embeddings import EmbeddingService
from app.knowledge.index import IndexStore
from app.knowledge.retrieval import Retriever
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument


SAMPLE_PDF = Path(__file__).resolve().parents[3] / "output" / "pdf" / "rag-test-knowledge-document.pdf"
MODEL_CACHE = Path(__file__).resolve().parents[2] / "data" / "models"


def test_four_baseline_questions_have_facts_in_top5_child_or_parent(tmp_path):
    if not SAMPLE_PDF.is_file():
        pytest.skip("缺少本地基线 PDF 归档")
    if not any(MODEL_CACHE.glob("models--qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/*")):
        pytest.skip("本机未缓存 FastEmbed 多语言模型；先按 README 下载后运行")
    settings = Settings(
        data_dir=tmp_path,
        qdrant_db_path=tmp_path / "qdrant",
        embedding_backend="fastembed",
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        embedding_cache_dir=MODEL_CACHE,
        sparse_offline_fallback=True,
        sparse_model_path=tmp_path / "bm25",
        llm_base_url="",
        llm_api_key="",
        llm_model="",
        retrieval_min_score=0.0,
    )
    pdf = SAMPLE_PDF.read_bytes()
    document_id = uuid4()
    source = tmp_path / "source.pdf"
    source.write_bytes(pdf)
    parsed = PdfParser().parse(pdf)
    parents, children = chunk_document(document_id, parsed, settings)
    store = DocumentStore(tmp_path)
    store.save_document(KnowledgeDocument(
        document_id=document_id, filename="rag-test-knowledge-document.pdf", status=DocumentStatus.ready,
        size_bytes=len(pdf), uploaded_at=utc_now(), source_path=str(source),
        parent_count=len(parents), child_count=len(children),
    ))
    store.replace_chunks(document_id, parents, children)
    index = IndexStore(tmp_path, EmbeddingService(settings), document_store=store)
    try:
        index.rebuild(children)
        assert index.ready and not index.needs_rebuild
        retriever = Retriever(settings, index, store)
        checks = [
            ("设备上电前需要检查什么？", ("接地线", "负载连接")),
            ("PX-200 的过流保护阈值是多少？", ("16 A", "100 ms")),
            ("运行记录默认保留多久？", ("三年", "先进先出")),
            ("设备多久进行一次维护？", ("六个月",)),
        ]
        for question, facts in checks:
            hits = retriever.search(question, top_k=5, min_score=0.0)
            assert hits, question
            evidence = "\n".join(hit.text + "\n" + store.get_parent(hit.parent_id).text for hit in hits)
            assert all(fact in evidence for fact in facts), (question, facts, [hit.section_title for hit in hits])
    finally:
        index.vector_db.client.close()
