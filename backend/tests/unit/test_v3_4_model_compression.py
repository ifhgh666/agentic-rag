import json

from app.rag.model_compression import ModelContextCompressor
from app.rag.model_provider import ModelResult
from app.rag.evidence import format_evidence_records


class StubProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete(self, messages, *, tools=None):
        self.calls.append(messages)
        return ModelResult(json.dumps(self.payload, ensure_ascii=False), "ollama", "stub", 80, 20)


def _records():
    return format_evidence_records([
        {
            "citation_id": "E1", "record_id": "one", "parent_id": "one",
            "document_id": "doc-one", "source": "protection.pdf", "section_title": "保护功能",
            "page_start": 3, "page_end": 3, "score": 0.9,
            "raw_text": "PX-200 的过流阈值为 16 A，持续 100 ms 触发保护。" + "其他说明。" * 50,
        },
        {
            "citation_id": "E2", "record_id": "two", "parent_id": "two",
            "document_id": "doc-two", "source": "records.pdf", "section_title": "运行记录",
            "page_start": 4, "page_end": 4, "score": 0.8,
            "raw_text": "运行记录默认保留三年，超过期限按先进先出删除。" + "其他说明。" * 50,
        },
    ])


def test_model_compression_only_runs_above_threshold_and_preserves_exact_facts():
    provider = StubProvider({
        "excerpts": [
            {"citation_id": "E1", "quote": "PX-200 的过流阈值为 16 A，持续 100 ms 触发保护。"},
            {"citation_id": "E2", "quote": "运行记录默认保留三年，超过期限按先进先出删除。"},
        ],
        "gaps": [],
    })
    compressor = ModelContextCompressor(provider)
    records = _records()
    unchanged, no_trace = compressor.compress("两个问题", records, threshold=10000)
    assert unchanged.compressed is False and no_trace is None and not provider.calls

    compressed, trace = compressor.compress("两个问题", records, threshold=110)
    assert compressed.compressed is True
    assert "16 A" in compressed.context and "100 ms" in compressed.context
    assert "三年" in compressed.context and "先进先出" in compressed.context
    assert "protection.pdf" in compressed.context and "records.pdf" in compressed.context
    assert compressed.tokens_after <= compressed.threshold
    assert trace["node"] == "context_compression" and len(provider.calls) == 1


def test_model_compression_rejects_invented_quote_and_uses_extractive_fallback():
    provider = StubProvider({"excerpts": [{"citation_id": "E1", "quote": "PX-200 阈值为 30 A。"}], "gaps": []})
    compressed, trace = ModelContextCompressor(provider).compress("PX-200 阈值", _records(), threshold=100)
    assert trace is not None
    assert "30 A" not in compressed.context
    assert compressed.tokens_after <= compressed.threshold
