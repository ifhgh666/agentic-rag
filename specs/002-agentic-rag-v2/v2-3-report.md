# V2-3 阶段验收报告：LangGraph + Tool Calling 骨架

**日期**：2026-09-24

## 已交付

- 增加 `langgraph` 和 `langchain-openai` 依赖，新增 `MAX_TOOL_CALLS`、
  `MAX_ITERATIONS`、`GRAPH_RECURSION_LIMIT` 配置。
- 新增 `MainState`、`AgentState`、`Evidence` 和 `GraphRunResult`。
- 新增 `search_child_chunks` 和 `retrieve_parent_chunks` 两个受控 LangChain 工具：
  校验参数、索引状态、文档状态和 Parent ID，不读取或解析 PDF。
- 新增 LangGraph Agent Subgraph：`orchestrator` → `ToolNode` → `orchestrator`，
  有证据时进入 `collect_answer`，无证据时进入 `fallback_response`。
- 新增 Main Graph：Agent Subgraph 完成后统一进入现有答案评估节点。
- 现有 `RagPipeline` 已接入 Graph，同时保留原有 SSE stage、answer、evaluation、complete
  事件格式，不发送模型私有思维链。
- 本阶段明确不实现 V2-4 的多轮新 Query、Parent 迭代、重复检索去重循环、上下文压缩，
  也不实现 V2-6 的持久化会话记忆。

## 验证命令与结果

```powershell
cd C:\Users\ifhgz\Desktop\agentic-rag
python -m pytest backend/tests/unit/test_graph_state.py backend/tests/unit/test_rag_tools.py backend/tests/unit/test_graph.py -q
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/tests
```

结果：Graph 定向测试 `6 passed`；后端完整测试 `41 passed`；编译检查通过。

Graph 单元验证覆盖：

- 首次进入 Agent 必须调用 `search_child_chunks`。
- `ToolNode` 执行后再次进入 `orchestrator`。
- 有证据时进入 `collect_answer` 并执行原有答案评估。
- 无证据或索引未就绪时进入 `fallback_response`。
- Parent 工具只读取 Parent Store，不重新解析 PDF。

真实服务验收：

- 后端重启后 `/api/health` 返回 `index_ready=true`。
- Graph 单元/集成测试已使用无证据请求验证 fallback，返回“当前知识库中没有足够信息回答
  这个问题”，未触发模型生成调用。
- 真实服务登录成功，`POST /api/debug/retrieve` 返回 `retrieval_mode=hybrid`，确认重启后
  Graph 依赖和 V2-2 检索链路正常加载；未通过真实 LLM 问答消耗外部模型额度。
- 已保留本地 Qdrant 单进程访问限制；测试使用 `pytest-qdrant` 隔离目录。

## 阶段边界与下一步

本阶段完成后暂停。V2-4 才会增加模型驱动的多轮新 Query、Parent Retrieval 路由、预算
循环和重复检索去重；需要用户明确继续后再执行。
