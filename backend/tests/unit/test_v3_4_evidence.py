import json
from uuid import uuid4

from app.knowledge.stores import DocumentStore
from app.rag.evidence import EvidenceSelector, find_numeric_conflict
from app.rag.generator import AnswerGenerator, INSUFFICIENT_ANSWER
from app.rag.model_provider import ModelResult
from app.schemas.chat import RetrievalResult
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, ParentContextUnit


class StubProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete(self, messages, *, tools=None):
        self.calls.append(messages)
        return ModelResult(json.dumps(self.payload, ensure_ascii=False), "ollama", "stub", 40, 25)


def _record(citation_id, text, filename="guide.pdf"):
    return {
        "citation_id": citation_id,
        "record_id": str(uuid4()),
        "parent_id": str(uuid4()),
        "document_id": str(uuid4()),
        "source": filename,
        "section_title": "保护功能",
        "page_start": 3,
        "page_end": 3,
        "raw_text": text,
        "content": f"[{citation_id} | 来源：{filename} | 第3页 | 章节：保护功能]\n{text}",
        "tokens": 40,
    }


def test_selector_does_not_discard_other_parents_after_first_short_parent(settings):
    store = DocumentStore(settings.data_dir)
    results = []
    for text, score in [
        ("欠压保护输入电压低于 198 V，30 秒后恢复。", 0.9),
        ("PX-200 输出电流超过 16 A 持续 100 ms，立即触发过流保护。", 0.7),
    ]:
        document_id, parent_id = uuid4(), uuid4()
        store.save_document(KnowledgeDocument(
            document_id=document_id, filename="guide.pdf", status=DocumentStatus.ready,
            size_bytes=1, uploaded_at=utc_now(),
        ))
        store.replace_chunks(document_id, [ParentContextUnit(
            parent_id=parent_id, document_id=document_id, text=text,
            char_count=len(text), ordinal=0,
        )], [])
        results.append(RetrievalResult(
            child_id=uuid4(), parent_id=parent_id, document_id=document_id,
            filename="guide.pdf", score=score, content_preview=text[:12], text=text[:12],
            retrieval_mode="hybrid",
        ))
    records = EvidenceSelector(settings, store).select("PX-200 的过流保护阈值是多少？", results)
    assert len(records) == 2
    assert any("16 A" in item["raw_text"] and "100 ms" in item["raw_text"] for item in records)


def test_selector_rejects_low_score_unrelated_result(settings):
    store = DocumentStore(settings.data_dir)
    result = RetrievalResult(
        child_id=uuid4(), parent_id=uuid4(), document_id=uuid4(),
        filename="wrong.pdf", score=0.001, content_preview="无关内容", text="无关内容",
        retrieval_mode="hybrid",
    )
    assert EvidenceSelector(settings, store).select("PX-200 的过流阈值是多少？", [result]) == []


def test_grounded_answer_only_accepts_exact_quotes_and_adds_source(settings):
    quote = "PX-200 输出电流超过 16 A 持续 100 ms 触发过流保护。"
    record = _record("E1", quote)
    provider = StubProvider({
        "is_answerable": True,
        "answer": "PX-200 的过流保护阈值是输出电流超过 16 A 持续 100 ms。",
        "citations": [{"citation_id": "E1", "quote": quote}],
        "conflict": False,
    })
    generator = AnswerGenerator(settings, provider)
    answer, cited_ids, trace = generator.generate_grounded_with_result("PX-200 的过流保护阈值是多少？", [record])
    assert "16 A" in answer and "100 ms" in answer
    assert "来源：guide.pdf" in answer and "第3页" in answer
    assert quote in answer
    assert cited_ids == ["E1"]
    assert trace["node"] == "collect_answer" and trace["input_tokens"] == 40


def test_short_model_answer_expands_to_its_verified_condition_sentence(settings):
    quote = "输出电流超过 16 A 持续 100 ms 会触发过流保护。"
    record = _record("E1", quote)
    provider = StubProvider({
        "is_answerable": True, "answer": "16 A",
        "citations": [{"citation_id": "E1", "quote": quote}], "conflict": False,
    })
    answer, _, _ = AnswerGenerator(settings, provider).generate_grounded_with_result("过流阈值？", [record])
    assert "16 A" in answer.split("\n\n依据：", 1)[0]
    assert "100 ms" in answer.split("\n\n依据：", 1)[0]


def test_grounded_answer_recovers_from_wrong_number_only_using_verified_quote(settings):
    record = _record("E1", "PX-200 的过流阈值是 16 A。")
    provider = StubProvider({
        "is_answerable": True, "answer": "PX-200 的过流阈值是 30 A。",
        "citations": [{"citation_id": "E1", "quote": "PX-200 的过流阈值是 16 A。"}], "conflict": False,
    })
    generated, cited_ids, trace = AnswerGenerator(settings, provider).generate_grounded_with_result("阈值？", [record])
    assert "16 A" in generated and "30 A" not in generated
    assert cited_ids == ["E1"] and trace["validation_status"] == "extractive_recovery"

    fake_quote = StubProvider({
        "is_answerable": True, "answer": "PX-200 的过流阈值是 16 A。",
        "citations": [{"citation_id": "E1", "quote": "PX-200 的过流阈值是 30 A。"}], "conflict": False,
    })
    rejected, cited_ids, _ = AnswerGenerator(settings, fake_quote).generate_grounded_with_result("阈值？", [record])
    assert rejected == INSUFFICIENT_ANSWER and cited_ids == []


def test_grounded_answer_remaps_real_quote_to_its_actual_source(settings):
    wrong = _record("E1", "PX-200 记录默认保留三年。", "records.pdf")
    actual = _record("E2", "例行维护周期为六个月。", "maintenance.pdf")
    provider = StubProvider({
        "is_answerable": True,
        "answer": "设备每六个月维护一次。",
        "citations": [{"citation_id": "E1", "quote": "例行维护周期为六个月。"}],
        "conflict": False,
    })
    answer, cited_ids, trace = AnswerGenerator(settings, provider).generate_grounded_with_result("维护周期？", [wrong, actual])
    assert cited_ids == ["E2"]
    assert "maintenance.pdf" in answer and "records.pdf" not in answer
    assert trace["remapped_citations"] == 1


def test_conflicting_evidence_cites_both_sources_without_picking_one(settings):
    first = _record("E1", "PX-200 阈值为 16 A。", "first.pdf")
    second = _record("E2", "PX-200 阈值为 18 A。", "second.pdf")
    provider = StubProvider({
        "is_answerable": True,
        "answer": "两份资料不一致：一份写 16 A，另一份写 18 A，无法确定唯一阈值。",
        "citations": [
            {"citation_id": "E1", "quote": "PX-200 阈值为 16 A。"},
            {"citation_id": "E2", "quote": "PX-200 阈值为 18 A。"},
        ],
        "conflict": True,
    })
    answer, cited_ids, _ = AnswerGenerator(settings, provider).generate_grounded_with_result("PX-200 阈值是多少？", [first, second])
    assert "不一致" in answer and "first.pdf" in answer and "second.pdf" in answer
    assert cited_ids == ["E1", "E2"]


def test_numeric_conflict_gate_only_flags_competing_values_for_same_fact():
    first = _record("E1", "PX-200 的过流保护阈值是 16 A。", "first.pdf")
    second = _record("E2", "PX-200 的过流保护阈值是 18 A。", "second.pdf")
    conflict = find_numeric_conflict("PX-200 的过流保护阈值是多少？", [first, second])
    assert conflict is not None
    assert conflict[0][0]["source"] == "first.pdf"
    assert conflict[1][0]["source"] == "second.pdf"
    same = _record("E2", "PX-200 的过流保护阈值是 16 A。", "second.pdf")
    assert find_numeric_conflict("PX-200 的过流保护阈值是多少？", [first, same]) is None
    unrelated = _record("E2", "PX-200 的保留期为 18 年。", "second.pdf")
    assert find_numeric_conflict("PX-200 的过流保护阈值是多少？", [first, unrelated]) is None
