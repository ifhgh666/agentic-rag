# V2-4 阶段验收报告：Multiple Retrieval Loop

**日期**：2026-09-24

## 已交付

- 新增可注入的 `QueryGenerator` 和默认规则生成器，能生成不重复的补充 Query。
- 扩展 AgentState，记录 `query_history`、`retrieval_keys`、Parent 上下文、最后工具、
  工具错误和预算状态。
- 实现四条受控路径：
  - 搜索有足够长证据 → 直接 `collect_answer`。
  - Child 证据较短 → 调用 `retrieve_parent_chunks` → `collect_answer`。
  - 首次搜索为空 → 生成第二个 Query → 再次搜索。
  - 达到工具/迭代预算或没有新的检索方向 → fallback 或基于已有证据回答。
- 使用 `search::{normalized_query}` 和 `parent::{parent_id}` 去重，避免重复工具调用。
- Parent 仍只从 Parent Store 读取，不重新解析 PDF；现有 SSE、答案生成和评估接口保持兼容。
- 使用配置的 `MAX_TOOL_CALLS`、`MAX_ITERATIONS`、`GRAPH_RECURSION_LIMIT` 和
  `AGENT_PARENT_THRESHOLD_CHARS` 控制循环。
- 增加 `SPARSE_OFFLINE_FALLBACK`：开启后使用 FastEmbed 的本地 BM25 兼容编码，
  不需要从 Hugging Face 下载停用词文件。

## 验证命令与结果

```powershell
cd C:\path\agentic-rag
python -m pytest backend/tests/unit/test_query_planner.py backend/tests/unit/test_graph.py backend/tests/unit/test_rag_tools.py -q
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/tests
```

结果：V2-4 定向测试 `9 passed`；后端全量测试 `47 passed`；编译检查通过。

覆盖路径：

- 一次 Hybrid Search 直接回答。
- Child 碎片触发 Parent Retrieval。
- 首次空结果生成不同 Query 并再次搜索。
- 工具预算为 1 时停止循环并 fallback。
- Query 和 Parent 去重键生效。

真实服务验收：

- 后端已重启，`GET /api/health` 返回 `index_ready=true`。
- 登录成功，`POST /api/debug/retrieve` 返回 1 条 `retrieval_mode=hybrid` 结果。
- 使用测试 PDF 完成真实上传和索引，文档状态为 `ready`，随后删除测试文档。
- 未主动调用真实大模型接口，避免消耗外部 API 额度；多轮路径使用确定性测试提供器验证。

切换代理后，HTTP `127.0.0.1:7897` 和 SOCKS5 `127.0.0.1:20808` 均能访问 Hugging Face。
官方 `Qdrant/bm25` 已成功缓存，当前 `backend/.env` 使用
`SPARSE_OFFLINE_FALLBACK=false`；离线回退代码仍保留，网络不可用时可改为 `true`。

## 阶段边界与下一步

本阶段完成后暂停。V2-5 才会实现上下文压缩、动态 Token 阈值、`context_summary` 和
压缩事件；本阶段不包含这些能力，也不实现 V2-6 会话记忆。
