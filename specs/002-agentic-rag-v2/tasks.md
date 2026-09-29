---
description: "V2-1 Qdrant Dense Migration 阶段任务"
---

# Tasks: PDF-RAG V2-1 Qdrant Dense Migration

**Input**: `plan.md`、`spec.md`、`research.md`、`data-model.md`、`contracts/api.md`

**范围**: 只执行 V2-1 Dense Migration；不实现 Sparse、Hybrid、LangGraph、Agent Loop、
上下文压缩、会话记忆或新的前端流程。

## Phase 1: Setup

- [x] T001 确认 `backend/requirements.txt`、`.gitignore` 和本地 `backend/data/qdrant` 配置路径，补充 V2-1 所需 Qdrant 依赖和运行目录规则

## Phase 2: Foundational Tests

- [x] T002 [P] 为 `backend/app/rag/vector_db_manager.py` 编写 Qdrant 本地 collection 创建、加载、Dense upsert、查询和按 `document_id` 删除的单元测试
- [x] T003 [P] 为 `backend/app/rag/index_store.py` 编写从旧 FAISS 文件迁移/重建到 Qdrant 的一致性和空索引测试

## Phase 3: User Story 1 - 保持 Simple RAG 的 Dense 检索行为（Priority: P1）

**Goal**: 使用本地持久化 Qdrant 替换 FAISS Dense 索引，同时保持现有上传、检索、回答和删除行为。

**Independent Test**: 使用测试 PDF 完成上传和处理，确认 Qdrant 中存在 Child Points，查询结果与原 Dense 检索契约一致；删除文档后对应 Points 消失，V1 后端回归测试通过。

- [x] T004 [US1] 在 `backend/app/rag/vector_db_manager.py` 实现 Qdrant 本地客户端、Dense collection schema、collection load/create、Child Point upsert、Dense query 和按 `document_id` 删除
- [x] T005 [US1] 在 `backend/app/rag/index_store.py` 将 `rebuild` 和 `search` 接到 `VectorDbManager`，保留 `IndexStore` 对 `Retriever` 的现有接口，并移除运行时对 FAISS 查询的依赖
- [x] T006 [US1] 在 `backend/app/config.py` 增加 Qdrant 路径、collection 名称和 Dense 检索配置，并在 `backend/.env.example` 写入安全默认值
- [x] T007 [US1] 在 `backend/app/main.py` 和 `backend/app/knowledge/manager.py` 接入 Qdrant 索引生命周期，确保上传重建、文档删除和服务启动加载保持一致
- [x] T008 [US1] 更新 `backend/tests/unit/test_index_store.py`、`backend/tests/unit/test_retriever.py` 和相关集成测试，验证 Child-only、ready 文档过滤、重建、查询和按文档删除

## Phase 4: Polish & V2-1 Validation

- [x] T009 [P] 更新 `specs/002-agentic-rag-v2/quickstart.md` 和 V2-1 迁移说明，记录安装、重建、启动、验证命令及未完成的 V2-2 事项
- [x] T010 运行后端完整测试、V2-1 定向测试、编译检查和手工健康检查，记录结果并在本任务清单中标记完成

## Dependencies & Execution Order

- T001 → T002/T003 → T004/T005/T006/T007 → T008 → T009/T010
- T002 与 T003 可并行；T009 只在实现和测试完成后执行。
- 本文件只覆盖 V2-1；V2-2 及后续阶段将在用户确认后生成新的阶段任务。

## V2-1 交付物

- `VectorDbManager` Dense 本地 Qdrant 实现
- `IndexStore` 到 Qdrant 的兼容适配
- 配置和依赖更新
- Qdrant 一致性、检索、删除和回归测试
- 阶段验证记录与未完成事项

---

# Tasks: PDF-RAG V2-2 Sparse + Hybrid Retrieval

**范围**：在 V2-1 本地 Qdrant Dense 检索基础上，增加 FastEmbed BM25 稀疏向量、同一点的 Dense+Sparse 命名向量和 Qdrant Fusion 混合检索；不实现 LangGraph、Tool Calling、Agent Loop、上下文压缩或会话记忆。

## Phase 1: Setup

- [x] T011 更新 `backend/requirements.txt`、`backend/app/config.py`、`backend/.env.example` 和本地 `.env`，加入 FastEmbed BM25、稀疏向量名称、混合检索 top-k/阈值配置

## Phase 2: Foundational Tests

- [x] T012 [P] 为 `backend/app/rag/sparse_embeddings.py` 编写延迟加载、批量编码和 `SparseVector` 转换测试，使用可注入的假模型隔离外部模型
- [x] T013 [P] 扩展 `backend/tests/unit/test_vector_db_manager.py`，验证 Dense+Sparse collection schema、双向量 upsert、Fusion 查询和按文档删除
- [x] T014 [P] 扩展检索契约测试，验证技术词查询走混合模式、阈值过滤生效、结果暴露 `retrieval_mode=hybrid`

## Phase 3: User Story 2 - Hybrid Retrieval（Priority: P1）

**Goal**：同时利用语义相似度和 BM25 词项匹配，提升型号、缩写、错误码和技术术语的召回稳定性。

**Independent Test**：使用包含技术术语和自然语言描述的 Child 集合，分别验证稀疏向量生成、Qdrant Fusion 查询、混合得分阈值和 debug/retrieve API 的模式标识。

- [x] T015 [US2] 新增 `backend/app/rag/sparse_embeddings.py`，封装 `Qdrant/bm25` 的懒加载和稀疏向量编码
- [x] T016 [US2] 升级 `backend/app/rag/vector_db_manager.py` 为 Dense+Sparse schema，重建时写入双命名向量，查询时使用 Dense/Sparse Prefetch 与 Qdrant Fusion
- [x] T017 [US2] 更新 `backend/app/rag/index_store.py`，兼容 Dense-only 旧 collection，启动时从旧 metadata 重建混合索引，查询阶段同时生成两类向量且不解析 PDF
- [x] T018 [US2] 更新 `backend/app/schemas/chat.py`、`backend/app/rag/retriever.py` 和 debug/retrieve 输出，显式标识 `retrieval_mode=hybrid`

## Phase 4: Polish & V2-2 Validation

- [x] T019 [P] 更新 `specs/002-agentic-rag-v2/quickstart.md` 和 `v2-2-report.md`，记录安装、迁移、启动、验证命令与已知限制
- [x] T020 运行 V2-2 定向测试、后端完整测试、编译检查和真实 Qdrant 服务验证，确认后端稳定后标记本阶段完成并停止

## V2-2 Dependencies & Execution Order

- T011 → T012/T013/T014 → T015/T016/T017/T018 → T019 → T020
- T012、T013、T014 可并行；T020 完成后只汇报 V2-2，不自动进入 V2-3。

---

# Tasks: PDF-RAG V2-3 LangGraph + Tool Calling Skeleton

**范围**：增加 LangGraph Main Graph、Agent Subgraph、强制首次 Child 搜索、两个受控工具、答案收集和 fallback；保留现有 FastAPI/SSE/评估接口，不实现 V2-4 的多轮新 Query、Parent 迭代循环、上下文压缩或 V2-6 会话记忆。

## Phase 1: Setup

- [x] T021 更新 `backend/requirements.txt` 和 `backend/app/config.py`，加入 LangGraph 依赖及 `MAX_TOOL_CALLS`、`MAX_ITERATIONS`、`GRAPH_RECURSION_LIMIT` 配置

## Phase 2: Foundational Tests

- [x] T022 [P] 为 `backend/app/rag/graph_state.py` 编写 MainState、AgentState 和 Evidence 的默认值、证据字段与预算约束测试
- [x] T023 [P] 为 `backend/app/rag/tools.py` 编写 Child 搜索和 Parent 读取工具测试，验证参数长度、索引未就绪、文档状态和不解析 PDF
- [x] T024 [P] 为 `backend/app/rag/graph.py` 编写 Graph 单元测试，验证首次进入 Agent 必须调用 `search_child_chunks`、工具结果回到 `orchestrator`、证据充分后进入 `collect_answer`、无证据进入 `fallback_response`

## Phase 3: User Story 3 - Controlled Agent Graph（Priority: P1）

**Goal**：用 LangGraph 明确表达 Main Graph 与 Agent Subgraph 的状态边界和工具调用路径，为后续多轮检索提供可测试骨架。

**Independent Test**：使用确定性 Fake provider 和测试 Child/Parent 数据运行图，确认首个工具调用是 `search_child_chunks`，ToolNode 执行后回到 `orchestrator`，有证据时生成答案并执行现有评估，无证据时返回 fallback。

- [x] T025 [US3] 新增 `backend/app/rag/graph_state.py`，定义 MainState、AgentState、Evidence 和图运行结果模型
- [x] T026 [US3] 新增 `backend/app/rag/tools.py`，实现 `search_child_chunks` 和 `retrieve_parent_chunks` 两个受控工具
- [x] T027 [US3] 新增 `backend/app/rag/nodes.py`，实现 `orchestrator`、`collect_answer`、`fallback_response` 和评估节点
- [x] T028 [US3] 新增 `backend/app/rag/graph.py`，使用 LangGraph StateGraph、ToolNode 和条件路由组装 Main Graph 与 Agent Subgraph
- [x] T029 [US3] 将 Graph 服务接入现有 `RagPipeline`，保持既有 SSE stage、answer、evaluation、complete 事件兼容，不暴露模型私有思维链

## Phase 4: Polish & V2-3 Validation

- [x] T030 [P] 更新 `backend/.env.example`、`backend/README.md`、`specs/002-agentic-rag-v2/quickstart.md` 和 `v2-3-report.md`
- [x] T031 运行 Graph 定向测试、后端完整测试、编译检查和真实服务启动、健康及检索链路验证，确认本阶段完成后停止

## V2-3 Dependencies & Execution Order

- T021 → T022/T023/T024 → T025/T026/T027/T028 → T029 → T030/T031
- T022、T023、T024 可并行；T031 完成后只汇报 V2-3，不自动进入 V2-4。

---

# Tasks: PDF-RAG V2-4 Multiple Retrieval Loop

**范围**：在 V2-3 Graph 骨架上增加受控的第二次 Query、Parent Retrieval 路由、工具/迭代预算、重复 Query/Parent 去重和可控 fallback；不实现 V2-5 上下文压缩或 V2-6 会话记忆。

## Phase 1: Setup

- [x] T032 增加多轮检索配置和状态字段，确保新 Query、Parent 阈值、工具预算和图递归限制均来自配置

## Phase 2: Foundational Tests

- [x] T033 [P] 为 Query 生成器编写新 Query、重复 Query 去重和空候选测试
- [x] T034 [P] 扩展 Graph 测试，覆盖一次搜索直接回答、Child 碎片后读取 Parent、首次无结果后第二次 Query、达到预算后 fallback
- [x] T035 [P] 扩展工具/状态测试，验证 Parent 证据合并、`search::{normalized_query}` 与 `parent::{parent_id}` 去重键和工具调用计数

## Phase 3: User Story 4 - Multiple Retrieval Loop（Priority: P1）

**Goal**：让 Agent 在证据不足时有限次生成新 Query 或读取 Parent，并在达到预算、重复调用或索引不可用时安全结束。

**Independent Test**：使用确定性 Fake Retriever、QueryGenerator 和 Parent Store，分别跑通直接回答、Child→Parent、第一次 Query→第二次 Query 三条路径，并验证预算不会死循环。

- [x] T036 [US4] 新增 `backend/app/rag/query_planner.py`，实现可注入的 QueryGenerator 和默认去重候选生成
- [x] T037 [US4] 扩展 `backend/app/rag/graph_state.py`、`nodes.py`，记录 query history、Parent 上下文、最后工具、预算和去重状态
- [x] T038 [US4] 扩展 `backend/app/rag/graph.py` 和 `tools.py`，实现 search/判断/search、search/Parent/answer 路由，合并证据并阻止重复调用
- [x] T039 [US4] 更新 `RagPipeline` 的 Graph 结果映射和错误状态，保持现有 SSE answer/evaluation/complete 兼容

## Phase 4: Polish & V2-4 Validation

- [x] T040 [P] 更新 `specs/002-agentic-rag-v2/quickstart.md`、`backend/README.md` 和 `v2-4-report.md`
- [x] T041 运行 V2-4 定向测试、后端完整测试、编译检查和真实服务健康/检索验证，完成后停止并汇报

## V2-4 Dependencies & Execution Order

- T032 → T033/T034/T035 → T036/T037/T038 → T039 → T040/T041
- T033、T034、T035 可并行；T041 完成后只汇报 V2-4，不自动进入 V2-5。

---

# Tasks: PDF-RAG V2-5 Context Compression

**范围**：在 V2-4 检索循环完成后增加动态 Token 阈值、上下文压缩、`context_summary` 和
SSE 压缩事件；保留原始 `retrieved_contexts` 用于审计，不实现 V2-6 会话记忆或
`conversation_summary`。

## Phase 1: Setup

- [x] T042 增加 `BASE_TOKEN_THRESHOLD`、`TOKEN_GROWTH_FACTOR` 配置，并扩展 Graph 状态和结果字段记录压缩状态

## Phase 2: Foundational Tests

- [x] T043 [P] 为 `should_compress_context`、动态 Token 阈值和 `compress_context` 编写单元测试
- [x] T044 [P] 扩展 Graph、Pipeline 和 SSE 测试，验证逐条 `retrieval_result` 记录、长上下文压缩、原始证据保留、`conversation_summary` 隔离和 `context_compression` 事件

## Phase 3: User Story 5 - Context Compression（Priority: P1）

**Goal**：上下文超过动态预算时生成可审计的 `context_summary`，只把摘要和必要证据交给答案生成，避免重复检索和超长上下文。

**Independent Test**：使用确定性长 Parent/Child 数据运行 Graph，确认压缩前后 Token 数、摘要、必要来源和工具轨迹可验证，并通过 Pipeline 收到 `context_compression` SSE 事件。

- [x] T045 [US5] 新增 `backend/app/rag/context_compression.py`，实现 Token 估算、动态阈值、`should_compress_context` 和确定性 `compress_context`
- [x] T046 [US5] 扩展 `backend/app/rag/graph_state.py`、`nodes.py` 和 `graph.py`，在答案生成前压缩上下文并保留 `retrieved_contexts` 与 `context_summary` 分离
- [x] T047 [US5] 更新 `backend/app/rag/pipeline.py`，映射压缩结果并发出 `context_compression` SSE 事件，保持答案评估和 complete 事件兼容

## Phase 4: Polish & V2-5 Validation

- [x] T048 [P] 更新 `specs/002-agentic-rag-v2/quickstart.md`、`backend/README.md` 和 `v2-5-report.md`
- [x] T049 运行 V2-5 定向测试、后端完整测试、编译检查和真实服务长上下文验证，完成后停止并汇报

## V2-5 Dependencies & Execution Order

- T042 → T043/T044 → T045 → T046 → T047 → T048/T049
- T043、T044 可并行；T049 完成后只汇报 V2-5，不自动进入 V2-6。


# Tasks: PDF-RAG V2-6 Conversation Memory

**范围**：在 V2-5 上下文压缩基础上增加同一 `thread_id` 的短期会话记忆、滚动
`conversation_summary`、上下文问题改写和模糊问题澄清；不实现 V2-7 的完整可观察性
面板和最终端到端交付。

## Phase 1: Setup

- [x] T050 增加 `MAIN_HISTORY_MESSAGES_TO_KEEP=4` 配置，并为会话记忆、查询改写和澄清定义默认边界，更新 `backend/app/config.py`、`backend/.env.example` 和状态初始化

## Phase 2: Foundational Tests

- [x] T051 [P] 为 `backend/app/rag/conversation_memory.py` 编写同一 `thread_id` 复用、不同 `thread_id` 隔离、滚动摘要和进程内重启丢失测试
- [x] T052 [P] 扩展 `backend/tests/unit/test_graph.py`、`backend/tests/unit/test_graph_state.py` 和 `backend/tests/contract/test_chat_stream_api.py`，覆盖历史消息保留、上下文追问改写、模糊问题澄清和 thread_id 返回

## Phase 3: User Story 6 - Conversation Memory（Priority: P1）

**Goal**：让同一个聊天线程能够理解上下文追问，同时避免不同聊天之间串线；对缺少
明确实体的问题先返回澄清请求，不启动无依据检索。

**Independent Test**：使用确定性 Fake Graph/Generator 连续请求同一 `thread_id`，确认第二
个问题能够使用历史摘要改写；使用不同 `thread_id` 确认历史不共享；发送“它的保护功能呢？”
等缺少实体的问题时返回 `clarification`，且不执行 Child 搜索。

- [x] T053 [US6] 新增 `backend/app/rag/conversation_memory.py`，使用 LangGraph `InMemorySaver` 保存进程内线程状态，按 `MAIN_HISTORY_MESSAGES_TO_KEEP` 保留最近消息并生成独立的 `conversation_summary`
- [x] T054 [US6] 扩展 `backend/app/rag/graph_state.py`、`backend/app/rag/graph.py` 和 `backend/app/rag/nodes.py`，接入线程恢复、历史摘要、上下文问题改写、实体缺失澄清和澄清后继续检索路由
- [x] T055 [US6] 扩展 `backend/app/rag/pipeline.py`、`backend/app/api/chat.py` 和 `backend/app/schemas/chat.py`，支持可选 `thread_id`/`conversation_id`，在 SSE 首个事件和最终事件返回线程标识，并保持现有答案评估兼容
- [x] T056 [US6] 更新 `frontend/src/api/client.ts`、`frontend/src/pages/Chat.tsx` 和相关类型，保存当前 `thread_id`、连续提问复用线程，并提供新会话入口

## Phase 4: Polish & V2-6 Validation

- [x] T057 [P] 更新 `specs/002-agentic-rag-v2/quickstart.md`、`backend/README.md` 和 `v2-6-report.md`，记录线程记忆、澄清分支、启动和验证命令
- [x] T058 运行 V2-6 定向测试、后端完整测试、前端测试、编译检查和真实 SSE 同线程/新线程验证，完成后停止并汇报

## V2-6 Dependencies & Execution Order

- T050 → T051/T052 → T053 → T054 → T055/T056 → T057/T058
- T051、T052 可并行；T058 完成后只汇报 V2-6，不自动进入 V2-7。


# Tasks: PDF-RAG V2-7 Observability and Frontend Delivery

**范围**：完善 Agent 节点、工具调用、查询、Parent、检索结果、压缩、预算和错误的
SSE/JSONL 可观察性，前端 Process 面板展示可审计执行摘要，并完成 V2 最终回归验收；
不实现 V3 的大模型查询改写或新的业务能力。

## Phase 1: Setup

- [x] T059 增加执行日志开关和长度限制配置，统一事件字段与脱敏边界，更新 `backend/app/config.py`、`backend/.env.example`、`backend/app/observability/events.py` 和状态模型

## Phase 2: Foundational Tests

- [x] T060 [P] 为 `backend/app/observability/logger.py` 编写结构化字段、长度截断、API Key/Authorization 脱敏和 request/thread 过滤测试
- [x] T061 [P] 扩展后端 SSE/Graph 集成测试，验证节点、工具、Query、Parent、迭代、预算、压缩、错误和 complete 事件字段完整且不包含私有思维链
- [x] T062 [P] 扩展 `frontend/src/components/ProcessPanel.test.tsx` 和 SSE 类型测试，验证 Agent/工具/检索/预算事件可展示，敏感字段不渲染

## Phase 3: User Story 7 - Auditable Delivery（Priority: P1）

**Goal**：让一次问答可以通过 `request_id`/`thread_id` 串起后端日志和前端 SSE，用户能看到
Agent 的可审计步骤、工具和证据摘要，但看不到模型私有思维链或密钥。

**Independent Test**：使用确定性测试数据调用 SSE，确认事件包含节点、工具、查询、Parent、
分数、耗时、迭代和工具调用数；前端 Process 面板显示这些摘要；日志和事件中不出现 API Key、
完整 Prompt 或模型 reasoning。

- [x] T063 [US7] 新增 `backend/app/observability/execution.py`，实现统一执行事件构造、字段长度限制和敏感字段过滤
- [x] T064 [US7] 扩展 `backend/app/observability/logger.py`，记录 `request_id`、`thread_id`、`node`、`event`、`tool`、`query`、`parent_id`、分数、耗时、迭代和工具调用数，并保留现有日志查询兼容性
- [x] T065 [US7] 扩展 `backend/app/rag/pipeline.py`、`backend/app/rag/graph.py` 和 `backend/app/api/chat.py`，发出 query_rewritten、agent_decision、tool_call、hybrid_search、parent_retrieval、context_compression、budget、evaluation、error 和 complete 事件
- [x] T066 [US7] 更新 `frontend/src/types/api.ts`、`frontend/src/api/client.ts` 和 `frontend/src/components/ProcessPanel.tsx`，展示 Agent 节点、工具参数摘要、检索模式、Parent、分数、迭代预算和压缩状态，禁止渲染 prompt/reasoning/token/key
- [x] T067 [US7] 增加 `backend/tests/integration/test_v2_final_acceptance.py` 和前端端到端事件测试，覆盖健康检查、认证、文档上传、Hybrid 检索、同线程追问、澄清、答案评估和完整 SSE 链路

## Phase 4: Polish & V2 Final Validation

- [x] T068 [P] 更新 `backend/README.md`、`specs/002-agentic-rag-v2/quickstart.md`、`specs/002-agentic-rag-v2/v2-7-report.md` 和最终验收清单，明确 V2 与 V3 边界
- [x] T069 运行 V2-7 定向测试、后端全量测试、前端全量测试、编译/构建检查、真实服务健康检查和 SSE 脱敏验收，完成 V2 并停止

## V2-7 Dependencies & Execution Order

- T059 → T060/T061/T062 → T063 → T064/T065 → T066/T067 → T068/T069
- T060、T061、T062 可并行；T069 完成后 V2 全部结束，不自动进入 V3。
