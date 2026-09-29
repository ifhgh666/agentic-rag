from pathlib import Path
from uuid import uuid4

from app.knowledge.chunker import chunk_document
from app.knowledge.models import ParsedPage, ParsedPdf
from app.knowledge.pdf_parser import PdfParser


SAMPLE_PDF = Path(__file__).resolve().parents[3] / "output" / "pdf" / "rag-test-knowledge-document.pdf"


def test_chinese_pdf_preserves_pages_headings_and_tables():
    parsed = PdfParser().parse(SAMPLE_PDF.read_bytes())

    assert [page.page_number for page in parsed.pages] == [1, 2, 3, 4]
    assert "## 2. 上电与启动流程" in parsed.pages[1].text
    assert "## 3. 保护功能与故障处理" in parsed.pages[2].text
    assert "|过流保护|" in parsed.pages[2].text
    assert "|运行记录保留期|3 年|" in parsed.pages[3].text
    assert "第 2 页" not in parsed.pages[1].text
    assert "�" not in parsed.text


def test_chinese_pdf_sections_do_not_turn_numbers_into_headings(settings):
    parsed = PdfParser().parse(SAMPLE_PDF.read_bytes())
    parents, children = chunk_document(uuid4(), parsed, settings)

    titles = [parent.section_title for parent in parents]
    assert any("2. 上电与启动流程" in title for title in titles)
    assert any("3. 保护功能与故障处理" in title for title in titles)
    assert any("4. 运行记录与维护" in title for title in titles)
    assert not any(title in {"300 ms", "30 秒自动恢复", "16 A", "3 年"} for title in titles)
    assert min(parent.char_count for parent in parents) >= 100
    assert next(parent for parent in parents if "2. 上电与启动流程" in parent.section_title).page_start == 2
    assert next(parent for parent in parents if "4. 运行记录与维护" in parent.section_title).page_end == 3
    assert any("接地线" in child.text and "负载连接" in child.text for child in children)
    assert any("16 A" in child.text and "100 ms" in child.text for child in children)
    assert all(child.parent_id in {parent.parent_id for parent in parents} for child in children)


def test_parent_rebalance_and_child_boundaries(settings):
    settings = settings.model_copy(update={"parent_chunk_size": 260, "child_chunk_size": 110, "child_chunk_overlap": 20})
    parsed = ParsedPdf(
        [ParsedPage(1, "## 1. 说明\n\n" + "短段。\n\n" + "## 1.1 细节\n\n" + ("中文内容保持连续。" * 95))]
    )
    parents, children = chunk_document(uuid4(), parsed, settings)

    assert len(parents) > 1
    assert max(parent.char_count for parent in parents) <= settings.parent_chunk_size
    assert max(child.char_count for child in children) <= settings.child_chunk_size
    assert all(child.text.strip() for child in children)
    assert all(parent.page_start == 1 and parent.page_end == 1 for parent in parents)
    assert not any(parent.char_count < 30 for parent in parents)
