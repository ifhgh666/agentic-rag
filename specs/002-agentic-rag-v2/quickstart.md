# V2 分阶段验证指南

本文件是设计阶段的可执行验收入口。实现阶段每完成一个阶段，都要把实际命令、
结果和未完成事项补充到阶段报告中，然后暂停等待继续指示。

## 前置条件

```powershell
cd C:\path\agentic-rag
python --version
cd backend
python -m pip install -r requirements.txt
cd ..\frontend
npm install
```

配置 `backend/.env` 中的管理员、JWT、LLM Base URL、API Key 和模型；密钥不得提交。
V2-1/V2-2 的 Qdrant 默认使用 `backend/data/qdrant` 本地目录，不要求单独启动 Qdrant
服务。
V2-2 默认使用 `Qdrant/bm25`；当前开发配置已成功缓存官方模型。
网络不可用时可以开启 `SPARSE_OFFLINE_FALLBACK=true`，使用本地 BM25 兼容编码。

## 启动

后端：

```powershell
cd C:\path\agentic-rag\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

前端：

```powershell
cd C:\path\agentic-rag\frontend
npm run dev
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## V2-1 验收

```powershell
cd backend
pytest -q tests/unit tests/integration tests/contract
```

预期：已有 V1 上传、检索、回答、删除测试通过；Qdrant collection 创建并可查询；
同一文档删除后对应 Child Points 不再返回。

本阶段实际验证：

```powershell
cd C:\path\agentic-rag\backend
pytest -q
```

结果：`32 passed`。手工启动后，`GET /api/health` 返回 `index_ready=true`，登录接口
返回 HTTP 200，`POST /api/debug/retrieve` 能从 `document_child_chunks` 返回 Child。

注意：本地 Qdrant 目录有单进程锁。正式服务运行时不要再启动第二个使用同一
`backend/data/qdrant` 的 Uvicorn 或测试进程；测试夹具默认使用 `pytest-qdrant` 隔离目录。

## V2-2 验收

```powershell
cd C:\path\agentic-rag\backend
python -m pytest tests/unit/test_sparse_embeddings.py tests/unit/test_vector_db_manager.py tests/unit/test_index_store.py tests/unit/test_retriever.py -q
python -m compileall -q app tests
```

预期：Dense 和 Sparse 命名向量同时存在，Qdrant Fusion 能返回结果；语义问题和型号/引脚
精确词都能返回结果，响应中出现 `retrieval_mode=hybrid`；Parent 不在 Qdrant collection。

V2-2 迁移说明：如果启动时发现 V2-1 的 Dense-only collection，`IndexStore` 会从旧的
`backend/data/index/children.json` 和 `vectors.npy` 重建双向量 collection；如果旧伴随文件
不存在，则从 Qdrant payload 读取 Child 文本后重新编码。问答检索阶段不会重新解析 PDF。

本阶段实际验证：

```powershell
cd C:\path\agentic-rag\backend
python -m pytest -q
```

结果：`35 passed`；真实服务重启后 `/api/health` 为 `index_ready=true`，登录成功，
`/api/debug/retrieve` 返回 `retrieval_mode=hybrid`。Qdrant collection 实测包含 `dense`
和 `sparse` 两个命名向量，共 35 个 Child Points。

## V2-3 验收

```powershell
cd C:\path\agentic-rag\backend
python -m pytest tests/unit/test_graph_state.py tests/unit/test_rag_tools.py tests/unit/test_graph.py tests/unit/test_pipeline_events.py -q
python -m compileall -q app tests
```

预期：第一次工具调用是 `search_child_chunks`；ToolNode 执行后回到
`orchestrator`；有 Parent 证据时进入 `collect_answer` 并执行答案评估；无证据时进入
`fallback_response`。本阶段不实现多轮新 Query、Parent 迭代、上下文压缩和持久化记忆。

本阶段实际验证：

```powershell
cd C:\path\agentic-rag\backend
python -m pytest -q
```

结果：`41 passed`；LangGraph Main Graph、Agent Subgraph、两个工具和现有问答 SSE
回归测试通过。后端真实启动、健康检查和无证据 fallback 见 `v2-3-report.md`。

## V2-4 验收

```powershell
cd C:\path\agentic-rag\backend
python -m pytest tests/unit/test_query_planner.py tests/unit/test_graph.py tests/unit/test_rag_tools.py -q
python -m compileall -q app tests
```

预期：覆盖一次搜索直接回答、Child 碎片后读取 Parent、第一次无结果后生成第二个 Query、
达到工具预算后 fallback 四条路径；重复 Query/Parent 不会无限循环。

本阶段实际验证：

```powershell
cd C:\path\agentic-rag\backend
python -m pytest -q
```

结果：多轮检索定向测试 `9 passed`，编译检查通过；全量回归 `47 passed`。
真实服务健康检查、登录、Hybrid 检索和测试 PDF 上传索引均通过，详见
`v2-4-report.md`。

## V2-5 验收

```powershell
cd backend
python -m pytest tests/unit/test_context_compression.py tests/unit/test_graph.py tests/unit/test_graph_state.py tests/unit/test_pipeline_events.py -q
```

预期：上下文超过动态预算时生成 `context_summary` 和 `context_compression` 事件；原始
`retrieved_contexts` 保留，工具轨迹不重复。实际定向测试 `12 passed`，全量回归 `51 passed`，
编译检查通过。V2-5 真实 FastAPI 长上下文验证见 `v2-5-report.md`。

## V2-6 验收

```powershell
cd C:\path\agentic-rag\backend
python -m pytest tests/unit/test_conversation_memory.py tests/unit/test_graph_state.py tests/unit/test_graph.py tests/contract/test_chat_stream_api.py -q
python -m pytest tests -q
python -m compileall -q app tests
cd ..\frontend
npm run test -- --run
npm run build
```

预期：同一 `thread_id` 的第二个问题可以使用上一轮背景改写；新的 `thread_id` 不共享历史；
没有明确对象的“它的保护功能呢？”会返回 `clarification`，且不会启动 Child 检索。
前端连续提问会复用当前线程，“新会话”会清空线程标识并创建新的会话。

本阶段实际验证：后端定向测试 `15 passed`，后端全量回归 `57 passed`，编译检查通过；
前端测试 `7 passed`，生产构建通过；真实服务 `/api/health` 返回 `status=ok`、
`index_ready=true`。详细结果见 `v2-6-report.md`。

限制：记忆使用进程内 `InMemorySaver`，后端重启后会丢失；跨进程持久化记忆不在 V2-6 范围内。

## V2-7 端到端验收

```powershell
cd C:\path\agentic-rag\backend
python -m pytest tests/integration/test_v2_final_acceptance.py tests/unit/test_execution_observability.py tests/unit/test_logger.py -q
python -m pytest tests -q
python -m compileall -q app tests
cd ..\frontend
npm run test -- --run
npm run build
```

预期：SSE 至少包含 `query_rewritten`、`agent_decision`、`tool_call`、`hybrid_search`、
`parent_retrieval`、`context_compression`（发生压缩时）、`evaluation` 和 `complete`；
每个执行事件带 `request_id`、`thread_id`、`node`、`event`、工具/查询/Parent/迭代字段，
日志可以用 `request_id` 查询，且不出现 API Key、Authorization、完整 Prompt 或 reasoning。

1. 浏览器打开 `http://localhost:5173` 并登录。
2. 上传一个文本型 PDF，确认前端依次展示 PDF、Markdown、Parent、Child、Dense、
   Sparse、Qdrant Hybrid 状态。
3. 连续发送“PN8733 上电以后整个工作过程是什么？”和“那它的保护功能呢？”。
4. 确认 Process 面板展示 Query Rewrite、Agent Decision、Hybrid Search、Parent、
   Evaluation 和 Complete，但没有私有思维链。
5. 使用相同 `request_id`/`thread_id` 关联后端 JSONL 日志和 SSE 事件。

本阶段实际验证：后端全量测试 `64 passed`，编译检查通过；前端测试 `10 passed`，生产构建
通过；真实服务健康检查返回 `index_ready=true`，真实澄清 SSE 返回 `step`、`node`、
`query_rewritten`、`agent_decision`、`answer`、`complete`，敏感字段检查通过。由于当前
本地配置已启用大模型，未用正式服务发送会消耗模型额度的完整回答请求；完整工具链由
确定性集成测试覆盖。工具事件来自 Graph 内真实执行 trace，但当前是在 Graph 完成后回放，
不是节点执行期间的实时推送。

## 阶段报告格式

```text
阶段：V2-x
已交付：文件/接口/测试
验证命令：...
结果：通过/失败
未完成事项：...
下一阶段：等待用户确认
```
