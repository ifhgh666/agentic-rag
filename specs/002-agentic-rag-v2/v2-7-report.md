# V2-7 阶段验收报告：Observability and Frontend Delivery

**日期**：2026-09-24

## 已交付

- 新增统一执行事件模型和脱敏工具，统一字段包括：
  `request_id`、`thread_id`、`node`、`event`、`tool`、`query`、`parent_id`、
  `duration_ms`、`score`、`iteration`、`tool_call_count` 和 `details`。
- Pipeline 增加可审计事件：`node`、`query_rewritten`、`agent_decision`、`tool_call`、
  `hybrid_search`、`parent_retrieval`、`budget`、`context_compression`、`evaluation`、
  `error` 和 `complete`；原有 `step`、`retrieval`、`answer` 事件保持兼容。
- Structured JSONL 日志增加线程、节点、工具、查询、Parent、分数、迭代和预算字段，支持按
  `request_id` 或 `thread_id` 过滤；日志开关和最大字段长度由配置控制。
- 日志/SSE 脱敏 API Key、Authorization、密码、完整 Prompt、reasoning 和过长字段。
- Process 面板增加 Agent 轨迹区，展示节点、工具、Hybrid 模式、Parent、迭代和压缩摘要，
  不渲染内部 Prompt 或模型私有推理。
- 工具执行时记录真实的 Query、Parent、结果数、最高分、检索模式和耗时，避免从最终状态
  反推第二次检索或 Parent 调用。
- 增加 V2 最终集成验收，覆盖认证、健康检查、文档上传、Hybrid 检索、SSE、答案评估和
  日志关联；前端测试覆盖真实 Process 面板渲染和 SSE 解析。

## 验证结果

```powershell
cd C:\path\agentic-rag\backend
python -m pytest tests -q
python -m compileall -q app tests
cd ..\frontend
npm run test -- --run
npm run build
```

- 后端全量测试：`64 passed`
- 后端编译检查：通过
- 前端测试：`10 passed`
- 前端生产构建：通过
- 确定性完整 SSE 验收：通过，工具链事件、真实工具元数据和日志关联字段完整
- 真实服务健康：`status=ok`、`index_ready=true`
- 真实服务澄清 SSE：通过，未发现敏感字段；本轮重启后健康检查仍为 `status=ok`、
  `index_ready=true`

## V2 最终边界

V2 已完成 Qdrant Hybrid、LangGraph 检索循环、上下文压缩、进程内会话记忆、SSE/日志可观察性
和前端执行面板。查询改写目前仍是 V2-6 的规则版；按用户要求，后续 V3 再替换为参考项目
中的大模型结构化查询改写。执行事件在当前 Graph 完成后按真实工具 trace 回放到 SSE，工具
耗时和结果元数据真实记录；尚未改为节点执行期间的实时逐事件推送。会话记忆仍是进程内
`InMemorySaver`，重启后丢失。
