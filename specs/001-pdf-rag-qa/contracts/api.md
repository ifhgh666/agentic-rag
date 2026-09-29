# API 契约：PDF RAG 知识库问答

基础路径：`/api`  
除非接口另有说明，否则请求和响应均使用 JSON。  
受保护接口要求请求头包含 `Authorization: Bearer <jwt>`。

## 通用错误

```json
{
  "error": {
    "code": "DOCUMENT_NOT_READY",
    "message": "当前没有可用的 ready 知识文档。",
    "request_id": "optional-uuid"
  }
}
```

API 不得返回模型提供商密钥、密码、本机绝对路径或原始堆栈信息。

## 健康检查

### `GET /api/health`

公开的服务就绪检查。

响应 `200`：

```json
{
  "status": "ok",
  "service": "pdf-rag-api",
  "index_ready": true
}
```

如果进程正常但派生索引需要修复，则返回 `200`、`index_ready: false` 和安全的状态
说明；不要暴露本机文件路径。

## 身份认证

### `POST /api/auth/login`

请求：

```json
{
  "username": "admin",
  "password": "configured-password"
}
```

响应 `200`：

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "username": "admin" }
}
```

凭据无效时返回 `401` 和 `INVALID_CREDENTIALS`。

### `POST /api/auth/logout`

受保护接口。客户端丢弃 Bearer 令牌，服务端返回 `204`。V1 使用短时效 JWT，
因此退出会结束当前客户端会话；令牌将在过期后失效，后续可以增加服务端令牌吊销
列表扩展点。

## 知识文档

### `GET /api/knowledge/documents`

受保护接口。返回 `200`：

```json
{
  "items": [
    {
      "document_id": "uuid",
      "filename": "guide.pdf",
      "status": "ready",
      "size_bytes": 12345,
      "uploaded_at": "2026-09-22T08:00:00Z",
      "processed_at": "2026-09-22T08:00:05Z",
      "parent_count": 4,
      "child_count": 12,
      "error_reason": null
    }
  ]
}
```

### `POST /api/knowledge/documents`

受保护的多部分上传接口，字段名为 `file`。文件必须是非空的文本型 PDF。文件被
接受处理后返回 `202`：

```json
{
  "document_id": "uuid",
  "status": "processing",
  "filename": "guide.pdf"
}
```

类型不正确、空文件、损坏文件、扫描件/无文本文件或超大文件返回 `400` 或 `422`，
并附带稳定错误码和可读信息。处理失败时保留状态为 `failed` 的文档记录，使管理员
能够看到失败原因。

### `DELETE /api/knowledge/documents/{document_id}`

受保护接口。删除原始 PDF、提取文本、父子元数据和派生索引中的对应内容。只有
剩余索引重建完成后才返回 `204`。未知 ID 返回 `404`。

## 检索诊断

### `POST /api/debug/retrieve`

受保护接口。不生成答案。

请求：

```json
{
  "query": "保存期限是多久？",
  "top_k": 5,
  "min_score": 0.35
}
```

响应 `200`：

```json
{
  "query": "保存期限是多久？",
  "results": [
    {
      "child_id": "uuid",
      "parent_id": "uuid",
      "document_id": "uuid",
      "filename": "guide.pdf",
      "section_title": "保存期限",
      "score": 0.82,
      "content_preview": "..."
    }
  ]
}
```

结果按分数降序排列，并且已经通过最低分数过滤。

## 流式问答

### `POST /api/chat/stream`

受保护接口。请求 JSON：

```json
{
  "question": "保存期限是多久？"
}
```

响应类型为 `text/event-stream`。每条事件都包含同一个 `request_id`。

事件格式：

```text
event: step
data: {"request_id":"uuid","stage":"child_retrieval","status":"completed","sequence":4,"duration_ms":21,"detail":{}}
```

必需事件类型：

- `step`：一个流水线阶段的开始、完成或失败。
- `retrieval`：按顺序排列的保留子级结果及来源元数据。
- `answer`：`{ "request_id", "answer", "sources" }`。
- `evaluation`：`{ "request_id", "relevance", "faithfulness", "completeness", "overall", "reason" }`。
- `error`：`{ "request_id", "code", "message" }`。
- `complete`：`{ "request_id", "status": "completed" }`。

服务器必须在慢速处理开始前发送 `query_receipt`/`received` 阶段。如果没有 ready
文档，或没有结果通过最低分数，答案事件必须包含明确的证据不足回复和空来源列表；
只要基础设施没有阻止流程完成，事件流仍应以 `complete` 结束。

## 日志

### `GET /api/logs`

受保护接口，支持以下查询参数：

`level`、`module`、`request_id`、`limit`（默认 100，最大 500）。

响应 `200`：

```json
{
  "items": [
    {
      "timestamp": "2026-09-22T08:00:05Z",
      "level": "INFO",
      "module": "rag.pipeline",
      "request_id": "uuid",
      "message": "答案已生成",
      "duration_ms": 120,
      "error": null
    }
  ],
  "count": 1
}
```

过滤条件无效时返回 `422`；未认证访问返回 `401`。

## 兼容性和版本

这是 V1 本地契约。路由使用稳定的资源名称和错误码，React 客户端可以在没有模型
提供商凭据的情况下完成测试。增加多用户角色、多轮记忆、OCR、联网搜索或多个知识
库时，必须创建新的规格说明，不能静默扩展本契约。
