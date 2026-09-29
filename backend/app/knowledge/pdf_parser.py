import re
from collections import Counter
from io import BytesIO

from .models import ParsedPage, ParsedPdf


class PdfParseError(ValueError):
    pass


class PdfParser:
    def parse(self, content: bytes) -> ParsedPdf:
        if not content:
            raise PdfParseError("PDF 文件为空。")
        try:
            import fitz

            document = fitz.open(stream=BytesIO(content), filetype="pdf")
        except Exception as exc:
            raise PdfParseError("PDF 文件损坏或无法读取。") from exc
        try:
            # 仅处理可选中文本的 PDF；OCR 属于独立阶段。
            if not any(page.get_text("text").strip() for page in document):
                raise PdfParseError("PDF 中没有可提取的文本，暂不支持扫描件 OCR。")
            import pymupdf4llm

            markdown_pages = pymupdf4llm.to_markdown(document, page_chunks=True, use_ocr=False)
            first_lines = [
                next((line.strip() for line in str(item.get("text", "")).splitlines() if line.strip()), "")
                for item in markdown_pages
            ]
            repeated = {line for line, count in Counter(first_lines).items() if line and count >= 2}
            pages: list[ParsedPage] = []
            for index, item in enumerate(markdown_pages):
                page_number = int(item.get("metadata", {}).get("page", index + 1))
                lines = str(item.get("text", "")).splitlines()
                while lines and not lines[0].strip():
                    lines.pop(0)
                if lines and lines[0].strip() in repeated:
                    lines.pop(0)
                while lines and not lines[-1].strip():
                    lines.pop()
                if lines and re.fullmatch(rf"第\s*{page_number}\s*页", lines[-1].strip()):
                    lines.pop()
                text = "\n".join(lines).strip()
                if text:
                    pages.append(ParsedPage(page_number=page_number, text=text))
        except PdfParseError:
            raise
        except Exception as exc:
            raise PdfParseError("PDF 结构化 Markdown 解析失败。") from exc
        finally:
            document.close()
        if not pages:
            raise PdfParseError("PDF 中没有可提取的文本，暂不支持扫描件 OCR。")
        return ParsedPdf(pages=pages)
