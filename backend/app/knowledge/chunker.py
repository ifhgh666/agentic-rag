"""按 Markdown 标题构建 Parent，再在 Parent 内切分 Child。"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from ..config import Settings
from ..schemas.documents import ParentContextUnit, SearchableChildUnit
from .models import ParsedPdf


_MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*\.)\s+([^\d\s].+)$")
_CHAPTER_HEADING = re.compile(r"^(第[一二三四五六七八九十百]+[章节])\s*(.+)$")
_HTML_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


@dataclass
class _Section:
    title: str
    text: str
    page_start: int
    page_end: int


def _heading(line: str) -> tuple[int, str] | None:
    value = line.strip()
    if not value or len(value) > 120 or value.startswith("|"):
        return None
    if match := _MARKDOWN_HEADING.match(value):
        title = match.group(2).strip()
        number = re.match(r"^(\d+(?:\.\d+)*)\.?\s+", title)
        depth = number.group(1).count(".") if number else 0
        return len(match.group(1)) + depth, title
    if match := _NUMBERED_HEADING.match(value):
        return match.group(1).count(".") + 1, value
    if _CHAPTER_HEADING.match(value):
        return 1, value
    return None


def _is_heading(line: str) -> bool:
    return _heading(line) is not None


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", _HTML_BREAK.sub(" ", line)).strip()


def _split_balanced(text: str, max_size: int) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    if len(clean) <= max_size:
        return [clean]
    count = math.ceil(len(clean) / max_size)
    width = math.ceil(len(clean) / count)
    pieces = [clean[index : index + width].strip() for index in range(0, len(clean), width)]
    return [piece for piece in pieces if piece]


def _split_with_overlap(text: str, size: int, overlap: int) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    if len(clean) <= size:
        return [clean]
    overlap = min(max(0, overlap), max(0, size // 3))
    result: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        if end < len(clean):
            # 优先在空格/标点处分块；若无边界则按字符平衡切分。
            candidates = [clean.rfind(mark, start + size // 2, end) for mark in (" ", "。", "；", "，", "|", "！", "？")]
            boundary = max(candidates)
            if boundary > start:
                end = boundary + (0 if clean[boundary] == " " else 1)
        piece = clean[start:end].strip()
        if piece:
            result.append(piece)
        if end >= len(clean):
            break
        next_start = max(start + 1, end - overlap)
        if len(clean) - next_start <= overlap:
            next_start = end
        start = next_start
    return result


def _sections(parsed: ParsedPdf) -> list[_Section]:
    sections: list[_Section] = []
    stack: list[tuple[int, str]] = []
    lines: list[str] = []
    start: int | None = None
    end: int | None = None

    def flush() -> None:
        nonlocal lines, start, end
        clean = [_clean_line(line) for line in lines]
        text = "\n".join(line for line in clean if line).strip()
        if text and start is not None and end is not None:
            sections.append(_Section(" / ".join(title for _, title in stack), text, start, end))
        lines, start, end = [], None, None

    for page in parsed.pages:
        for line in page.text.splitlines():
            if heading := _heading(line):
                flush()
                level, title = heading
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
            if not line.strip():
                continue
            lines.append(line)
            start = page.page_number if start is None else start
            end = page.page_number
    flush()
    return sections


def _parent_pieces(sections: list[_Section], max_size: int, min_size: int) -> list[_Section]:
    pieces = [
        _Section(section.title, text, section.page_start, section.page_end)
        for section in sections
        for text in _split_balanced(section.text, max_size)
    ]
    merged: list[_Section] = []
    for piece in pieces:
        previous = merged[-1] if merged else None
        if (
            previous
            and (len(previous.text) < min_size or len(piece.text) < min_size)
            and previous.page_end == piece.page_start
            and len(previous.text) + len(piece.text) + 1 <= max_size
            and (piece.title.startswith(previous.title) or previous.title.startswith(piece.title))
        ):
            merged[-1] = _Section(
                piece.title if len(piece.title) >= len(previous.title) else previous.title,
                previous.text + "\n" + piece.text,
                previous.page_start,
                piece.page_end,
            )
        else:
            merged.append(piece)
    return merged


def chunk_document(
    document_id: UUID, parsed: ParsedPdf, settings: Settings
) -> tuple[list[ParentContextUnit], list[SearchableChildUnit]]:
    parent_size = max(1, settings.parent_chunk_size)
    child_size = max(1, settings.child_chunk_size)
    parent_pieces = _parent_pieces(_sections(parsed), parent_size, min(120, parent_size // 2))
    parents: list[ParentContextUnit] = []
    children: list[SearchableChildUnit] = []
    for piece in parent_pieces:
        parent = ParentContextUnit(
            parent_id=uuid4(), document_id=document_id, section_title=piece.title,
            page_start=piece.page_start, page_end=piece.page_end,
            text=piece.text, char_count=len(piece.text), ordinal=len(parents),
        )
        parents.append(parent)
        for ordinal, child_text in enumerate(_split_with_overlap(parent.text, child_size, settings.child_chunk_overlap)):
            children.append(SearchableChildUnit(
                child_id=uuid4(), parent_id=parent.parent_id, document_id=document_id,
                section_title=parent.section_title, text=child_text,
                char_count=len(child_text), ordinal=ordinal,
            ))
    if not parents or not children:
        raise ValueError("文档没有生成可用的父级或子级内容。")
    return parents, children
