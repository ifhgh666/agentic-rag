# Agent职责目录与提示唯一来源阶段报告（2026-10-18）

## 阶段目标与授权范围

用户明确要求继续整理当前难以理解的 Agent 代码，并给出目标目录：`app/rag_agent/` 下包含 `__init__.py`、`edges.py`、`graph.py`、`graph_state.py`、`nodes.py`、`prompts.py`、`schemas.py`、`tools.py`。用户同时要求 prompt 集中，入口使用 `rewrite-prompt-v6-zh`。

本轮作为007的补充A2阶段执行；`.specify/feature.json` 仍指向009，本轮没有改写功能指针或推进009。范围只包括职责迁移、兼容入口、提示唯一来源、采集指纹、工程测试和当前文档，不修改模型、检索算法、API/SSE协议、`.env`、正式知识库、索引或历史评测结论。

## 实际架构

```text
backend/app/rag_agent/
  __init__.py       # 无副作用包入口
  edges.py          # 条件路由
  graph.py          # LangGraph装配与AgentGraphService
  graph_state.py    # Agent/Main/Thread状态与结果
  nodes.py          # 所有真实节点行为
  prompts.py        # 所有生产提示与模型消息模板
  schemas.py        # 模型结构化输出
  tools.py          # 只读RAG工具与请求缓存
```

- `app.main` 与 `rag.pipeline` 直接导入 `rag_agent.graph.AgentGraphService`。
- 原 `app/rag/graph.py`、`graph_state.py`、`nodes.py`、`prompt.py`、`model_schema.py`、`tools.py` 只显式 re-export canonical 对象，不保留第二套函数、类或提示正文。
- 通用服务仍位于 `app/rag`，包括 provider、generator、query analysis、agent loop、conversation memory、retriever、evaluator 和 cost control；这些消费者直接导入 `rag_agent` 的职责模块。
- `rag_agent/__init__.py` 不 eager import graph，避免 consumer 迁移后的循环初始化。

## Prompt集中结果

- `backend/app/rag_agent/prompts.py` 是生产提示和模型消息模板的唯一实现。
- `REWRITE_PROMPT_VERSION` 保持为 `rewrite-prompt-v6-zh`；改写提示正文保持本轮开始时的中文v6内容。
- 除9个固定提示函数外，入口动态输入、分支问题、调用预算、基础答案、证据、分支汇总、检索改写和JSON Schema回退消息均由参数化纯函数生成。
- schema字段说明继续由 `schemas.py` 负责，工具description继续由 `tools.py` 负责；它们属于各自协议，不复制到prompt模块。
- `capture_query_rewrite_v1.py` 现在冻结真实的 `app/rag_agent/prompts.py` 与 `app/rag_agent/schemas.py`，不再对旧兼容壳取指纹。

## 主要文件

- 新canonical实现：`backend/app/rag_agent/` 八个文件。
- 生产接入：`backend/app/main.py`、`backend/app/rag/pipeline.py`、`agent_loop.py`、`query_analysis.py`、`generator.py`、`conversation_summary.py`、`query_planner.py`、`model_provider.py`、`conversation_memory.py`、`evidence.py`。
- 兼容入口：`backend/app/rag/{graph,graph_state,nodes,prompt,model_schema,tools}.py`。
- 采集与测试：`backend/scripts/capture_query_rewrite_v1.py`、`backend/tests/unit/test_rag_agent_architecture.py`、`test_request_deadline.py`、`test_query_rewrite_capture.py`。
- 当前文档：README、仓库导航、CURRENT_STATUS及007的spec/plan/tasks/research/prompt-review/contract/quickstart。

## 实际验证

工作目录均为 `C:\Users\ifhgz\Desktop\agentic-rag\backend`，pytest使用仓库内独立可写basetemp并禁用cacheprovider。

1. `python -m compileall -q app tests/unit/test_request_deadline.py tests/unit/test_query_rewrite_capture.py scripts/capture_query_rewrite_v1.py`
   - 退出码：0。
2. canonical/兼容对象身份与模块导入检查（`app.rag_agent.graph`、旧graph、canonical/旧prompt、agent_loop、model_provider）
   - 退出码：0；graph、prompt、预算提示和schema回退函数均指向canonical对象，版本输出为`rewrite-prompt-v6-zh`。
3. 定点pytest：架构守护、提示消费者、graph、graph_state、request deadline、structured query analysis、capture、provider、tools
   - 退出码：0；`96 passed in 77.20s`。
4. 完整后端工程回归：`python -m pytest -q tests/unit tests/contract tests/integration tests/security --basetemp=../output/prompt007/rag-agent-architecture-20261018/backend-regression/pytest -p no:cacheprovider`
   - 退出码：1；`590 passed, 2 failed in 163.29s`。
   - `test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity` 仍断言旧v4共享条件/比较/容量措辞。
   - `test_context_prompt_limits_history_and_preserves_unconfirmed_conditions` 仍断言旧短语“只使用必要历史”。
   - 两项均是当前中文v6启用后已在009阶段A和阈值保留报告中记录的既有措辞断言，不由本次目录迁移引入。本轮没有改回prompt、删除失败或把失败写成通过。

另有一次直接 `import app.main` 的检查触发模块级应用创建，因当前正式 `backend/data/qdrant` 已被另一实例占用而以 `AlreadyLocked` 失败。本轮未停止现有服务、未打开第二个正式Qdrant实例。完整pytest使用隔离临时数据并已覆盖应用相关工程路径；该失败不能说明正式运行实例已重新加载新代码。

## 测试性质与限制

以上均为工程测试，使用fake/scripted provider、假传输、临时数据和隔离索引。没有调用Ollama或云端模型，没有提交真实问题，没有运行检索质量或正式题集，也没有启动/重启后端。因此可确认目录职责、导入身份、提示来源和既有工程行为，不能证明真实问答质量、模型遵循度或运行中旧进程已经采用新代码。

历史真实结果保持：`rewrite-prompt-v6-zh` 的三题复测仍为0通过/3失败；唯一对象代码兜底的单题复测记录仍独立有效。架构迁移不改判这些结果。

## 阶段结论与停止点

T049–T053的架构交付已完成。真实Agent实现现在位于用户指定的八文件目录，节点与路由不再内嵌于graph，生产prompt只有一份，入口版本为`rewrite-prompt-v6-zh`，旧路径只承担兼容。两项既有prompt措辞测试仍失败并已如实保留。

下一阶段如需删除旧兼容模块、调整v6业务规则或重新运行真实模型验收，需要用户分别明确授权。

报告后暂停，等待用户验收。
