from uuid import uuid4

from app.knowledge.chunker import chunk_document
from app.knowledge.models import ParsedPage, ParsedPdf


def test_chunker_keeps_parent_child_relationship(settings):
    parsed = ParsedPdf([ParsedPage(1, "# 规则\n数据保存期限是三年。\n" + "补充说明。" * 100)])
    parents, children = chunk_document(uuid4(), parsed, settings)
    parent_ids = {item.parent_id for item in parents}
    assert parents and children
    assert all(item.parent_id in parent_ids for item in children)
    assert all(item.char_count == len(item.text) for item in children)

