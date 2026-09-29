import fitz
import pytest

from app.knowledge.pdf_parser import PdfParseError, PdfParser


def test_parser_extracts_page_text(pdf_bytes):
    parsed = PdfParser().parse(pdf_bytes)
    assert parsed.pages[0].page_number == 1
    assert "data retention period" in parsed.text


@pytest.mark.parametrize("content", [b"", b"not a pdf"])
def test_parser_rejects_invalid_content(content):
    with pytest.raises(PdfParseError):
        PdfParser().parse(content)


def test_parser_rejects_pdf_without_text():
    document = fitz.open()
    document.new_page()
    content = document.tobytes()
    document.close()
    with pytest.raises(PdfParseError, match="没有可提取"):
        PdfParser().parse(content)
