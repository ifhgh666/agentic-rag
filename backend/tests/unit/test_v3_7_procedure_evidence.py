"""通用流程证据覆盖；业务代码不识别测试设备和具体动作词。"""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import Settings
from app.core.legacy_rag import eligible_units, read_saved_markdown, recover_paragraphs
from app.core.answering import format_evidence_records, AnswerGenerator, INSUFFICIENT_ANSWER
from scripts.replay_v3_6_q3 import FixedResponseProvider
from app.core.query_analysis import QueryAnalyzer
from app.core.conversation import PreparedQuery
from app.core.model_call import BoundedCache
from tests.fakes.providers import ScriptedQueryProvider


MARKDOWN = "## Service\n\n|Item|Value|\n|---|---|\n|Summary|Perform reset.|\n\nFor recovery, close the valve and wait until pressure\n\nhas dissipated. Check the circuit, then clear the alert.\n\nFor another fault, leave power off."
RAW = " ".join(MARKDOWN.split())


def record():
    return format_evidence_records([{
        "record_id": "parent-1", "source": "manual.pdf", "page_start": 3,
        "section_title": "Service", "raw_text": RAW,
        "procedure_units": recover_paragraphs(RAW, MARKDOWN),
    }])[0]


def test_restore_full_paragraph_and_merge_pdf_line_wrap_not_table():
    units = recover_paragraphs(RAW, MARKDOWN)
    assert len(units) == 2
    assert "pressure has dissipated" in units[0]["text"]
    assert "clear the alert" in units[0]["text"]
    assert all("Perform reset" not in unit["text"] for unit in units)


def test_stale_markdown_cannot_supply_missing_steps():
    assert recover_paragraphs(RAW.replace("close the valve", "open the valve"), MARKDOWN) == []
    assert recover_paragraphs(RAW[:90], MARKDOWN) == []


def test_procedure_model_expression_is_preserved_and_original_is_only_citation():
    item = record()
    provider = FixedResponseProvider({"is_answerable": True, "answer": "Clear the alert.",
        "citations": [{"citation_id": "E1", "quote": item["procedure_units"][0]["text"]}],
        "procedure_unit_ids": ["E1.P1"], "conflict": False})
    answer, ids, trace = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
        "Walk me through recovery", [item], procedure_required=True)
    assert answer.split("\n\n依据：")[0] == "Clear the alert."
    assert "has dissipated" in answer and "clear the alert" in answer
    assert ids == ["E1"] and trace["validation_status"] == "accepted"
    assert len(provider.calls) == 1


def test_legacy_unit_ids_without_actual_citations_fail_after_bounded_model_repair():
    item = record()
    item["raw_text"] = "Clear the alert."
    provider = FixedResponseProvider({"is_answerable": True, "answer": "Clear the alert.",
        "citations": [], "procedure_unit_ids": ["E1.P1"]})
    answer, ids, trace = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
        "Recovery?", [item], procedure_required=True)
    assert not ids and trace["stop_reason"] == "verification_failed"
    assert len(provider.calls) == 2 and "校验" in answer


def test_legacy_unit_ids_do_not_override_a_valid_model_quote_or_claim_semantic_completeness():
    for unit_ids in ([], ["E1.P999"]):
        provider = FixedResponseProvider({"is_answerable": True, "answer": "Clear the alert.",
            "citations": [{"citation_id": "E1", "quote": "clear the alert."}],
            "procedure_unit_ids": unit_ids})
        answer, ids, _ = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
            "Recovery?", [record()], procedure_required=True)
        assert answer.startswith("Clear the alert.") and ids == ["E1"]
        assert "close the valve" not in answer  # Program does not expand the answer.


def test_fact_answer_contract_and_numeric_checks_are_unchanged():
    item = format_evidence_records([{"record_id": "fact", "source": "manual.pdf", "page_start": 2,
        "raw_text": "Threshold is 12 A for 80 ms."}])[0]
    provider = FixedResponseProvider({"is_answerable": True, "answer": "12 A for 80 ms",
        "citations": [{"citation_id": "E1", "quote": item["raw_text"]}]})
    answer, ids, trace = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result("Threshold?", [item])
    assert "12 A" in answer and "80 ms" in answer and ids == ["E1"]
    assert trace["validation_status"] == "accepted"


def test_markdown_list_is_kept_as_one_ordered_unit_with_intro():
    md = "## Setup\n\nFollow these steps:\n\n1. Isolate input.\n\n2. Wait for discharge.\n\n3. Check the circuit.\n\nNever bypass interlocks."
    units = recover_paragraphs(" ".join(md.split()), md)
    assert "1. Isolate input" in units[0]["text"]
    assert "3. Check the circuit" in units[0]["text"]
    assert units[0]["text"].index("1.") < units[0]["text"].index("3.")


def test_generator_sends_actual_raw_evidence_and_requires_citations():
    item = record()
    item["content"] = "[E1]\nClear the alert."
    provider = FixedResponseProvider({"is_answerable": True, "answer": "x", "procedure_unit_ids": ["E1.P1"]})
    answer, _, _ = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
        "Recovery?", [item], procedure_required=True)
    assert len(provider.calls) == 2 and "校验" in answer
    assert "close the valve" in provider.calls[0]["messages"][-1]["content"]


def test_entrance_cache_does_not_add_legacy_procedure_classification():
    provider = ScriptedQueryProvider({"is_clear": True,
        "questions": ["Walk me through re-enabling the channel"], "clarification_needed": ""})
    analyzer = QueryAnalyzer(Settings(_env_file=None), provider, cache=BoundedCache(10, 60), index_version=lambda: "index")
    prepared = PreparedQuery("", [], "unused", True)
    first = analyzer.analyze("Walk me through re-enabling the channel", prepared, thread_id="t")
    second = analyzer.analyze("Walk me through re-enabling the channel", prepared, thread_id="t")
    assert first.is_clear and not first.requires_procedure and not second.requires_procedure and second.source == "cache"
    assert len(provider.calls) == 1


def test_short_condition_prefix_is_not_dropped_as_a_heading():
    md = "## Recovery\n\nIf alert code is\n\nABC, isolate the input. Wait until the circuit is discharged."
    units = recover_paragraphs(" ".join(md.split()), md)
    assert units[0]["text"].startswith("If alert code is ABC")


def test_procedure_only_context_does_not_repeat_parent_and_units():
    item = record()
    item["procedure_only"] = True
    item["source_text"] = item["raw_text"]
    item["raw_text"] = "\n\n".join(unit["text"] for unit in item["procedure_units"])
    formatted = format_evidence_records([item])[0]
    assert "Perform reset" not in formatted["content"]
    assert formatted["content"].count("close the valve") == 1
    assert "Perform reset" in formatted["source_text"]


def test_fact_citation_flags_do_not_override_model_selected_sources():
    procedure = record()
    fact = format_evidence_records([{"source": "manual.pdf", "record_id": "fact", "page_start": 4,
        "raw_text": "Records are retained for three years."}])[0]
    fact["citation_id"] = "E2"
    payload = {"is_answerable": True, "answer": "Short answer", "procedure_unit_ids": ["E1.P1"],
               "citations": [{"citation_id": "E2", "quote": fact["raw_text"]}]}
    for include in (False, True):
        provider = FixedResponseProvider(payload)
        answer, ids, _ = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
            "Recovery and retention", [procedure, fact], procedure_required=True, include_fact_citations=include)
        assert answer.startswith("Short answer")
        assert "close the valve" not in answer
        assert "three years" in answer and ids == ["E2"]


def test_model_may_describe_multiple_sources_with_explicit_citations():
    first, second = record(), record()
    first["document_id"] = "manual-a"
    second.update({"citation_id": "E2", "document_id": "manual-b"})
    provider = FixedResponseProvider({"is_answerable": True, "answer": "Two manuals describe the recovery.",
        "citations": [{"citation_id": "E1", "quote": "close the valve"},
                      {"citation_id": "E2", "quote": "clear the alert."}],
        "procedure_unit_ids": ["E1.P1", "E2.P1"]})
    answer, ids, trace = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
        "Recovery?", [first, second], procedure_required=True)
    assert answer.startswith("Two manuals") and ids == ["E1", "E2"]
    assert trace["validation_status"] == "accepted"


def test_source_ordinals_do_not_reorder_model_expression_or_selected_citations():
    first, second = record(), record()
    first.update({"document_id": "manual-a", "page_start": 3, "source_ordinal": 2, "record_id": "z"})
    second.update({"citation_id": "E2", "document_id": "manual-a", "page_start": 3,
                   "source_ordinal": 1, "record_id": "a"})
    provider = FixedResponseProvider({"is_answerable": True, "answer": "First close the valve; for another fault leave power off.",
        "citations": [{"citation_id": "E1", "quote": "close the valve"},
                      {"citation_id": "E2", "quote": "For another fault, leave power off."}],
        "procedure_unit_ids": ["E1.P1", "E2.P2"]})
    answer, ids, trace = AnswerGenerator(Settings(_env_file=None), provider).generate_grounded_with_result(
        "Recovery?", [first, second], procedure_required=True)
    assert ids == ["E1", "E2"] and trace["validation_status"] == "accepted"
    assert answer.startswith("First close the valve; for another fault")


def test_three_field_entrance_does_not_infer_a_procedure_flag():
    provider = ScriptedQueryProvider({"is_clear": True,
                                      "questions": ["Unseen wording"], "clarification_needed": ""})
    outcome = QueryAnalyzer(Settings(_env_file=None), provider).analyze(
        "Unseen wording", PreparedQuery("", [], "unused", True))
    assert outcome.is_clear and not outcome.requires_procedure


@pytest.mark.parametrize("case", [
    "valid", "missing", "other_directory", "wrong_document_id", "too_large",
    "invalid_utf8", "read_error", "missing_markdown_path", "missing_source_path",
])
def test_saved_markdown_keeps_document_boundary_and_read_failures(tmp_path, monkeypatch, case):
    document_id = uuid4()
    directory = tmp_path / str(document_id)
    directory.mkdir()
    markdown = directory / "document.md"
    markdown.write_text(MARKDOWN, encoding="utf-8")
    document = SimpleNamespace(document_id=document_id, markdown_path=str(markdown),
                               source_path=str(directory / "document.pdf"))
    if case == "missing":
        markdown.unlink()
    elif case == "other_directory":
        document.source_path = str(tmp_path / "other" / "document.pdf")
    elif case == "wrong_document_id":
        document.document_id = uuid4()
    elif case == "too_large":
        with markdown.open("wb") as stream:
            stream.truncate(10 * 1024 * 1024 + 1)
    elif case == "invalid_utf8":
        markdown.write_bytes(b"\xff\xfe")
    elif case == "read_error":
        def fail_read(*args, **kwargs):
            raise OSError("synthetic read failure")
        monkeypatch.setattr(type(markdown), "read_text", fail_read)
    elif case == "missing_markdown_path":
        document.markdown_path = ""
    elif case == "missing_source_path":
        document.source_path = ""
    assert read_saved_markdown(document) == (MARKDOWN if case == "valid" else "")


@pytest.mark.parametrize("complete,raw_text,content,accepted", [
    (True, "Close\nvalve.", "[E1] Close<br /> valve.", True),
    (False, "Close valve.", "Close valve.", False),
    (1, "Close valve.", "Close valve.", False),
    (True, "Other text.", "Close valve.", False),
    (True, "Close valve.", "Other text.", False),
])
def test_eligible_units_require_complete_text_in_both_retained_views(complete, raw_text, content, accepted):
    item = {"citation_id": "E1", "raw_text": raw_text, "content": content,
            "procedure_units": [{"text": "Close valve.", "complete": complete}]}
    allowed = eligible_units([item])
    if accepted:
        assert allowed == {"E1.P1": (item, "Close valve.", 1)}
        assert allowed["E1.P1"][0] is item
    else:
        assert allowed == {}
