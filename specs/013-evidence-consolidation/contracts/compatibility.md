# Compatibility Contract

唯一批准的兼容变化：删除 app.rag.procedure_evidence，不保留转发；仓库外导入改为 app.rag.evidence。

normalized(text)、_matching_section(parent_text, markdown)、recover_paragraphs(parent_text, markdown)、read_saved_markdown(document)、eligible_units(records) 及四个常量保留，签名/返回/算法/异常处理原样搬移。

EvidenceSelector.select 与旧 evidence 能力不变；主图不恢复 procedure 分类或 select；ModelCallRunner、ContextAdmission、SSE、配置和前端协议无变化。保留同文档派生 Markdown 路径/大小/解码/失败检查，不扩大权限或解析 PDF。
