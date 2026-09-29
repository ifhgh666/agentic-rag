# Implementation Plan: PDF-RAG V2 Agentic RAG

**Branch**: `002-agentic-rag-v2` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: 用户提供的 V2 改造规范和配置指南，已整理为 [spec.md](spec.md)。

## Summary

将 V1 的“一次检索、一次回答、一次评估”升级为单 Agent、多轮检索的 Agentic RAG。入库阶段将
PDF 一次性转换为 Markdown，按标题层级生成 Parent/Child；Child 使用 Qdrant 存储
Dense 和 Sparse 向量，Parent 保留在 JSON Store。问答阶段使用 LangGraph 的 Main
Graph 和 Agent Subgraph，让模型通过工具调用决定继续 Hybrid Search、读取 Parent 或
结束并回答。现有 FastAPI、React、SSE、JWT、答案评估和日志能力保持兼容。

本计划采用阶段闸门：完成一个阶段的代码、测试、验收记录和运行命令后立即暂停并
向用户汇报，不自动进入下一个阶段。`tasks.md` 不在本轮生成，等用户确认开始实现
后，再按当前阶段生成和执行任务。

## Technical Context

**Language/Version**: Python 3.12.4；前端 TypeScript 5.7、React 18、Vite 6

**Primary Dependencies**: FastAPI、LangGraph、LangChain Core/OpenAI adapter、
Qdrant Python client、FastEmbed sparse model、PyMuPDF、React、SSE、JWT

**Storage**: 本地文件（PDF、Markdown、Parent JSON、JSONL 日志）和本地持久化
Qdrant collection；V2 对话检查点使用进程内 `InMemorySaver`

**Testing**: pytest 后端单元/契约/集成测试；Vitest 前端测试；手工 SSE 和浏览器验收

**Target Platform**: Windows 本地开发机，FastAPI `127.0.0.1:8000`，Vite `5173`

**Project Type**: React + FastAPI 本地 Web 应用

**Performance Goals**: 单管理员、单机、小规模 PDF；上传处理和检索可观测，阶段验收不
以高并发为目标；Agent 循环受 8 次工具调用、10 次迭代限制

**Constraints**: 保留 V1 API 行为；不在问答时重新解析 PDF；Parent 不进入 Qdrant；
不得泄露 API Key 或模型思维链；Qdrant 初版采用本地路径，不要求单独启动服务

**Scale/Scope**: 一个知识库、一个 Agent、一个管理员、单个 `thread_id` 会话链；不做
多 Agent、多知识库、联网搜索、OCR、图片理解、复杂权限和持久化生产级记忆

## Constitution Check

*GATE: 通过后才能进入实现阶段；设计产物完成后再次检查。*

- **阶段边界交付：通过。** V2-1 至 V2-7 独立验收，每阶段有产物、测试、命令和
  未完成事项；本轮不生成实现任务，也不实现代码。
- **RAG 模块单一职责：通过。** 解析、Markdown、分块、向量数据库、工具、Graph、
  生成、评估、日志和 API 通过独立模块协作。
- **基于证据回答：通过。** 首次 Agent 强制搜索；没有足够证据时明确说明；最终
  评估不反向触发未声明的检索。
- **安全且一致的数据处理：通过。** 密钥继续来自 `.env`；删除按文档 ID 删除
  Markdown、Parent 和 Qdrant Points；迁移阶段先建立回归和一致性检查。
- **可观察且可验证：通过。** Graph 节点、工具调用、检索、压缩、SSE 和日志共享
  `request_id`/`thread_id`；每阶段增加针对性测试。
- **V1 边界：通过。** V2 作为新的 `002-agentic-rag-v2` 功能目录，不覆盖
  `001-pdf-rag-qa`，并通过回归测试保持既有功能。

## Project Structure

### Documentation (this feature)

```text
specs/002-agentic-rag-v2/
├── spec.md               # V2 需求、边界和验收标准
├── plan.md               # 本文件：阶段计划和技术设计
├── research.md           # 技术选型与风险研究
├── data-model.md         # 入库、检索和 Agent 状态模型
├── quickstart.md         # 分阶段验证指南
├── contracts/
│   └── api.md            # V2 API、SSE 和错误契约
└── tasks.md              # 用户确认后按当前阶段生成
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   ├── auth/
│   ├── knowledge/
│   │   ├── pdf_parser.py
│   │   ├── chunker.py
│   │   └── stores.py
│   ├── rag/
│   │   ├── vector_db_manager.py
│   │   ├── tools.py
│   │   ├── graph_state.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   ├── nodes.py
│   │   ├── edges.py
│   │   ├── graph.py
│   │   ├── evaluator.py
│   │   └── service.py
│   └── observability/
├── data/
│   ├── markdown/
│   ├── parents/
│   ├── qdrant/
│   └── logs/
├── tests/
│   ├── contract/
│   ├── integration/
│   ├── security/
│   └── unit/
└── requirements.txt

frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   └── styles/
└── tests/
```

**Structure Decision**: 采用当前单仓库 `backend/` + `frontend/` 结构。V2 在既有模块
上增量替换索引和问答编排；`knowledge` 负责入库，`rag` 负责检索和 Agent，`api`
负责 HTTP/SSE 传输，前端只消费公开事件，不承载 Agent 推理。

## Design Decisions

1. **Qdrant 部署**：V2 首版使用 `QdrantClient(path=QDRANT_DB_PATH)` 本地持久化，
   适配当前 Windows 单机项目，不引入额外服务依赖；后续可在不改变
   `VectorDbManager` 契约的情况下切换 URL 模式。
2. **向量边界**：只有 Child Point 进入 Qdrant，Parent 保持文件存储；Payload 保存
   `document_id`、`parent_id`、来源、页码、标题层级和文本。
3. **Agent 模型**：使用 LangGraph 管理状态和循环，使用 OpenAI-compatible Chat
   Model adapter 绑定工具；保留现有生成器作为兼容/降级路径。
4. **记忆范围**：V2 按规格使用 `InMemorySaver` 和 `thread_id`；它只保证当前进程
   内的会话连续性，重启后不承诺恢复，生产持久化 checkpointer 不在 V2 范围。
5. **思维链边界**：SSE 只传递工具、查询、证据摘要、节点和预算信息，不传递模型
   私有 reasoning 内容。

## 分阶段实施与交付物

每个阶段都必须遵循：实现 → 自动化测试 → 手工验收 → 更新阶段文档 → 汇报并暂停。
未完成事项不能被隐藏，也不能提前实现后续阶段能力。

### V2-0：规划与设计（本轮已完成）

交付物：`spec.md`、`plan.md`、`research.md`、`data-model.md`、`contracts/api.md`、
`quickstart.md`。本阶段不改造 V2 业务代码，不生成 `tasks.md`。

通过条件：需求边界、技术决策、数据模型、API/SSE 契约、阶段闸门和验证命令均可
追溯；V1 目录未被覆盖。

### V2-1：Qdrant Dense Migration

交付物：`VectorDbManager` 最小实现、Dense collection 创建/加载/写入/删除/查询、
FAISS 到 Qdrant 的索引适配或重建命令、数据一致性检查、回归测试和迁移说明。

通过条件：现有单轮 Simple RAG 的上传、索引、检索、回答和删除行为不变；Qdrant
中的数据只包含 Child；无需修改前端问答交互。

### V2-2：Sparse + Hybrid Retrieval

交付物：Sparse BM25 编码适配、命名 `sparse` 向量、Hybrid 查询和分数/模式元数据；
`search_child_chunks` 契约返回 `retrieval_mode=hybrid`；型号、引脚、寄存器等精确
术语测试；重建和删除测试。

通过条件：Dense 语义词和精确技术词都能召回；分数阈值、Top-K、模型和集合名来自
配置；Parent 仍不进入 Qdrant。

### V2-3：LangGraph + Tool Calling 骨架

交付物：`MainState`、`AgentState`、Main Graph、Agent Subgraph、两个工具、
`orchestrator`、`collect_answer`、`fallback_response` 和 Graph 单元测试。

通过条件：首次进入 Agent 强制调用搜索工具；工具结果能回到 Orchestrator；证据足够
时结束并沿用答案评估；暂不实现多轮自纠错和对话记忆。

### V2-4：Multiple Retrieval Loop

交付物：新 Query 生成、Parent Retrieval、工具/迭代预算、重复 Query/Parent 去重、
fallback 以及搜索→判断→搜索/Parent→回答的集成测试。

通过条件：至少覆盖三条路径：一次搜索直接回答、Child 碎片后读取 Parent、第一次
方向不足后生成第二个 Query；达到预算时可控结束且不死循环。

### V2-5：Context Compression

交付物：`retrieved_contexts`、`retrieval_keys`、`context_summary`、动态 Token 阈值、
`should_compress_context` 和 `compress_context`；长上下文测试及 SSE 事件。

通过条件：上下文超过预算时只保留压缩摘要和必要证据；不混淆
`conversation_summary`；压缩过程中不重复执行已完成工具。

### V2-6：Conversation Memory

交付物：`thread_id`、`InMemorySaver`、`conversation_summary`、历史摘要、查询改写、
澄清分支及 API/前端新会话支持。

通过条件：同一会话能理解“那它的保护功能呢？”；不同 `thread_id` 不串上下文；
模糊问题能请求澄清；重启丢失记忆属于已声明范围。

### V2-7：Observability 与前端交付

交付物：Agent 节点和工具 SSE 事件、Process 面板、日志字段升级、调试信息脱敏、
端到端测试、V2 配置/启动文档和最终验收清单。

通过条件：前端能看到可审计步骤而非思维链；一次请求可用 request/thread ID 串起
日志和 SSE；V1 回归测试与 V2 核心验收标准全部通过。

## 阶段闸门与暂停规则

进入下一个阶段必须同时满足：

1. 当前阶段的交付文件已落盘；
2. 针对性测试通过，失败项已解释；
3. 手工验收命令和预期输出已记录；
4. 未完成事项和风险已列出；
5. 已向用户汇报并获得继续指示。

本计划不会授权一次性执行 V2-1 至 V2-7；实现时每次只处理一个阶段。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| 增加 LangGraph Main Graph + Agent Subgraph | V2 需要受控 Agent Loop、工具路由和会话状态 | 单一固定 Pipeline 无法表达“工具结果返回后再次判断”，也无法保持阶段边界 |
| 引入 Qdrant 本地持久化 | V2 要求 Dense + Sparse Hybrid 和按文档删除 Child Points | FAISS 只能满足 V1 Dense 索引，无法承载命名 Sparse 向量和 Hybrid 查询 |
