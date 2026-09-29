# V2-6 阶段验收报告：Conversation Memory

**日期**：2026-09-24

## 已交付

- 增加 `MAIN_HISTORY_MESSAGES_TO_KEEP=4` 配置，默认保留最近四条对话消息。
- 新增 `ConversationMemory`，按 `thread_id` 隔离短期消息窗口和滚动
  `conversation_summary`，并使用 LangGraph `InMemorySaver` 作为进程内线程检查点。
- Main Graph 增加 `prepare_query`、`clarification` 和 `persist_memory` 路径：
  - 清晰问题直接进入原有 Agent 检索循环；
  - 带“它/其/这个/那个”等指代的追问会结合当前线程历史改写；
  - 没有历史背景的模糊追问返回澄清，不执行 Child 搜索；
  - 答案或澄清结果完成后写回当前线程。
- `/api/chat/stream` 支持可选 `thread_id` 和 `conversation_id`，SSE 事件返回线程标识，
  并新增 `query_rewritten`、`agent_decision=clarification` 事件。
- 前端保存当前 `thread_id`，连续问题复用同一会话，并提供“新会话”入口清空线程。
- 保留 V2-5 的 `context_summary` 与 `conversation_summary` 分离；本轮对话摘要不混入检索证据。

## 验证结果

```powershell
cd C:\Users\ifhgz\Desktop\agentic-rag\backend
python -m pytest tests/unit/test_conversation_memory.py tests/unit/test_graph_state.py tests/unit/test_graph.py tests/contract/test_chat_stream_api.py -q
python -m pytest tests -q
python -m compileall -q app tests
cd ..\frontend
npm run test -- --run
npm run build
```

- V2-6 定向测试：`15 passed`
- 后端全量测试：`57 passed`
- 编译检查：通过
- 前端测试：`7 passed`
- 前端生产构建：通过
- 真实服务：`GET /api/health` 返回 `status=ok`、`index_ready=true`

## 阶段边界

记忆只存在当前 Python 进程内，后端重启后丢失；没有实现跨进程持久化、复杂多会话列表或
V2-7 的完整可观察性与最终端到端交付。
