# Data Model

无新实体/持久化/状态迁移；原形状保持。

- recover_paragraphs 返回 list[dict]，text、complete=True、ordinal；章节须完全匹配，单元须位于 parent 原文。
- eligible_units 返回 citation_id.P{index} → (原 record 对象, 文本, 从 1 开始索引)。complete is True，文本同时位于 raw_text/content。
- read_saved_markdown 读取 document.markdown_path/source_path/document_id：resolve 后同目录且目录名为 document_id，文件≤10 MiB；缺失、拒绝和读取错误返回空字符串，不重新解析 PDF。
- EvidenceSelector、SourceRef、聊天事件和状态形状保持。
