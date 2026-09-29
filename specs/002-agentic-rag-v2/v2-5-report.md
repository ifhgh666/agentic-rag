# V2-5 阶段验收报告：Context Compression

**日期**：2026-09-24

## 已交付

- 增加 `BASE_TOKEN_THRESHOLD=2000` 和 `TOKEN_GROWTH_FACTOR=0.9` 配置。
- 增加确定性的 Token 估算、动态阈值、`should_compress_context` 和
  `compress_context`。
- 每条父文档检索证据生成一个独立的 `retrieval_result` 记录，单独保存
  `record_id`、`parent_id`、`document_id`、来源、章节、相关度、内容和 Token 估算；
  上下文预算按这些记录的 Token 总和判断，不再只把整段拼接文本当成一条记录。
- 压缩后仍保留逐条 `retrieval_result` 记录，并标记 `compressed=true`，因此可以知道每条
  证据压缩前后的内容和 Token 变化。
- 上下文超过阈值时生成 `context_summary`，答案生成只接收压缩摘要和必要证据。
- `retrieved_contexts` 原始证据仍保留在 Agent 状态中，用于审计和后续评估。
- `conversation_summary` 仍独立为空，本阶段没有实现 V2-6 会话记忆。
- 新增 `context_compression` SSE 事件，携带摘要长度、压缩前后 Token 数、阈值和移除项数量。
- 压缩发生在已有检索循环结束后，不会重新调用搜索或 Parent 工具。

## 验证结果

```powershell
cd C:\path\agentic-rag
python -m pytest backend/tests/unit/test_context_compression.py backend/tests/unit/test_graph.py backend/tests/unit/test_graph_state.py backend/tests/unit/test_pipeline_events.py -q
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/tests
```

- V2-5 定向测试：`12 passed`
- 后端全量测试：`51 passed`
- 编译检查：通过
- 真实服务：`GET /api/health` 返回 `status=ok`、`index_ready=true`；默认阈值下问答返回
  `answer` 和 `complete`。
- 使用正式 Qdrant 数据的临时副本和 30 Token 测试阈值调用真实 FastAPI 接口，确认同时收到
  `context_compression`、`answer` 和 `complete` 事件；正式数据未被修改。

## 阶段边界

本阶段只处理当前问题的检索上下文压缩。V2-6 的 `thread_id` 持久状态、历史摘要、查询改写、
澄清分支和 `InMemorySaver` 尚未实现。
