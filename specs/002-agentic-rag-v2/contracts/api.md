# V2 API 与事件契约

## 兼容原则

认证、文档列表、文档删除和健康检查保持 V1 路径兼容。V2 只扩展问答请求、入库
状态和调试响应，不把内部 Qdrant 路径或模型思维链暴露给前端。

## `POST /api/chat/stream`

请求 JSON：

```json
{
  "question": "PN8733 上电以后整个工作过程是什么？",
  "thread_id": "chat-uuid",
  "conversation_id": "chat-uuid"
}
```

规则：

- `question` 必填，最长 `MAX_QUESTION_CHARS`。
- `thread_id` 可选；省略时服务端生成并在首个事件返回，后续同一聊天必须复用。
- 不接受客户端传入检索结果、Parent 内容或模型决策。

## SSE 事件

每个事件都包含 `request_id` 和 `thread_id`，`data` 为 JSON。

```text
event: query_receipt
data: {"request_id":"...","thread_id":"...","question":"..."}

event: query_rewritten
data: {"query":"...","is_clear":true}

event: agent_decision
data: {"action":"search_child_chunks","iteration":1}

event: hybrid_search
data: {"query":"...","count":7,"retrieval_mode":"hybrid","duration_ms":12}

event: parent_retrieval
data: {"parent_id":"...","duration_ms":4}

event: context_compression
data: {"summary_chars":800,"removed_messages":6}

event: answer
data: {"content":"...","sources":[{"source":"...","parent_id":"..."}]}

event: evaluation
data: {"relevance":90,"faithfulness":92,"completeness":88,"overall":90}

event: complete
data: {"request_id":"...","thread_id":"...","status":"completed"}
```

允许的 `agent_decision.action`：`search_child_chunks`、`retrieve_parent_chunks`、
`answer`、`fallback`、`clarification`。不允许发送完整 prompt、隐藏思维链或 API Key。

## 错误事件

```text
event: error
data: {
  "code":"AGENT_BUDGET_EXCEEDED",
  "message":"已达到本次检索预算，以下为当前证据范围内的回答。",
  "request_id":"..."
}
```

统一错误码至少包括：`INVALID_QUESTION`、`THREAD_NOT_FOUND`、`INDEX_NOT_READY`、
`AGENT_BUDGET_EXCEEDED`、`LLM_TOOL_CALL_UNSUPPORTED`、`INTERNAL_ERROR`。

## `POST /api/knowledge/{document_id}/rebuild`

用于显式从已保存 Markdown 重建 Parent、Child 和 Qdrant Points，不重新读取 PDF，
除非 Markdown 缺失且请求明确允许重新解析。

响应：

```json
{
  "document_id": "...",
  "status": "ready",
  "markdown_path": "data/markdown/...md",
  "parent_count": 38,
  "child_count": 142,
  "retrieval_mode": "hybrid"
}
```

## `GET /api/knowledge/{document_id}/ingestion`

返回入库阶段状态，用于前端展示：

```json
{
  "document_id": "...",
  "steps": [
    {"name":"pdf_uploaded","status":"completed"},
    {"name":"pdf_to_markdown","status":"completed"},
    {"name":"parent_chunking","status":"completed","count":38},
    {"name":"child_chunking","status":"completed","count":142},
    {"name":"dense_embedding","status":"completed"},
    {"name":"sparse_indexing","status":"completed"},
    {"name":"qdrant_hybrid_ready","status":"completed"}
  ]
}
```

## 工具内部契约

```python
search_child_chunks(query: str, limit: int = DEFAULT_RETRIEVAL_K) -> list[Evidence]
retrieve_parent_chunks(parent_id: str) -> ParentEvidence
```

工具必须验证长度、去重键、文档状态和索引就绪状态；不得自行解析 PDF。
