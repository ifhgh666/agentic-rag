# Tasks: 清楚的 Agent 核心与基础能力归属

**Input**: 本目录 spec.md、plan.md、research.md、data-model.md、contracts/ownership.md、quickstart.md。
**授权**: 用户“继续”授权 A；B 待 A 验收后另行指示。任务勾选是工程状态，不是用户验收。
**格式**: `- [ ] T编号 [P?] [US?] 动作与文件路径`。本轮单代理依次执行，不隐含提交、发布或真实模型授权。

## Phase 1: Setup（A）

- [x] T001 将源码、Git diff/未跟踪清单、历史报告和失败清单保存到 output/clarity015/phase-a/before/，核对 output/clarity015/plan/source-baseline.json。
- [x] T002 核对 .gitignore、目录内代理指令与 specs/015-rag-responsibility-clarity/checklists/requirements.md 的只读门禁，记录命令。
- [x] T003 在 output/clarity015/phase-a/run.py 和 clarity015_guard.py 复用最终隔离保护；保存迁移前完整后端回归。

## Phase 2: Foundational（A，阻塞 US1）

- [x] T004 根据 output/clarity015/plan/proposed-symbol-map.json 为 161 个符号生成迁移及 AST 核对工具 output/clarity015/phase-a/relocate.py 和 audit.py。
- [x] T005 在 backend/tests/unit/test_rag_architecture.py 添加职责归属守护，迁移前验证其确实发现 provider/index/store 位于 Agent 核心的问题。

## Phase 3: US1 维护者从核心目录理解一次问答（P1，A / MVP）

**独立验收**: 161 项实现归属/AST、跨目录依赖无环、真实 Agent 核心职责、隔离后端回归无新增产品失败。既有两项提示断言及未测范围单列。

- [x] T006 [US1] 将 ModelResult/PreparedAttempt、提供商及 estimate_tokens/正则迁到 backend/app/core/model_provider.py，保持协议和用量回退。
- [x] T007 [US1] 将 CallContext/CallSpec/CallRecord/CallOutcome、预算/lease/缓存/runner 迁到 backend/app/core/model_call.py，保持原绝对期限和计数。
- [x] T008 [US1] 将 Dense/Sparse adapter 迁到 backend/app/knowledge/embeddings.py，索引/清单迁到 index.py，Retriever/ContextBuilder/normalize_query 迁到 retrieval.py。
- [x] T009 [US1] 将 ConversationTurn/ThreadState/MemorySnapshot/PreparedQuery 和原子存取迁到 backend/app/core/conversation.py，图数据仍在 backend/app/rag/graph_state.py。
- [x] T010 [US1] 将 AnalysisOutcome/QueryAnalyzer 及约束校验迁到 backend/app/core/query_analysis.py，将解析/生成/引文格式化/核验迁到 answering.py，禁止 answering 回导 nodes。
- [x] T011 [US1] 将独立旧查询、证据筛选/恢复/冲突能力迁到 backend/app/core/legacy_rag.py，保持原接口且不接回正常图。
- [x] T012 [US1] 将请求交付/诊断移交迁到 backend/app/core/pipeline.py；backend/app/core/__init__.py 保持轻量；不改既有主图及兼容 builder 行为。
- [x] T013 [US1] 让 backend/app/rag/nodes.py 实际保留模型循环、摘要和节点，tools.py 保留工具准入/请求单飞缓存，schemas.py 只保留 Agent/工具结构；prompts.py 字节保持。
- [x] T014 [US1] 迁移 backend/app/main.py 及其余生产调用、backend/scripts/ 与 backend/tests/ 的导入、模块别名和 monkeypatch；不留转发模块或动态别名。
- [x] T015 [US1] 更新 backend/scripts/capture_query_rewrite_v1.py 的两处源码冻结清单与 backend/tests/unit/test_query_rewrite_capture.py 的失配探针；旧冻结批次仍拒绝 code mismatch。
- [x] T016 [US1] 完善 backend/tests/unit/test_rag_architecture.py 的跨 core/rag/knowledge 无环、实际实现归属和提示唯一来源守护。
- [x] T017 [US1] 在 output/clarity015/phase-a/ 保存最终静态审计：161 项等价、实际模块依赖、配置/前端/提示/历史未变、全部调用入口可导入。
- [x] T018 [US1] 迁移 clarity015_guard.py 的 EmbeddingService 入口，执行保护证明、定向及完整隔离后端回归；所有失败和修复复跑分别保存在 output/clarity015/phase-a/。

## Phase 4: A Polish 与交付（A 的停止点）

- [x] T019 更新 README.md、docs/repository-guide.md、docs/CURRENT_STATUS.md 和本目录 spec.md/plan.md/quickstart.md 的当前结构与状态，历史日期化报告保持。
- [x] T020 保存 specs/015-rag-responsibility-clarity/phase-a-report.md：实际改动、命令/退出码、隔离与未测、失败、下一阶段；报告后暂停，等待用户验收。

## Phase 5: US2 重复执行流程有可验证的简化依据（P2，B，未授权）

**独立验收**: 各候选先证明调用用途和行为，再以假调用对照正常/失败/迟到路径、顺序、次数与期限；没有等价证据则不改。

- [ ] T021 [US2] 在 specs/015-rag-responsibility-clarity/phase-b-candidates.md 固定 graph.py 单节点壳、pipeline.py 事件投影与 SDK 复用候选的调用证据及逐项选择。
- [ ] T022 [US2] 在 output/clarity015/phase-b/ 验证本机 SDK 和候选前后假调用，不升级依赖、不调用真实模型。
- [ ] T023 [US2] 仅在 backend/app/rag/graph.py、nodes.py 或 core/pipeline.py 实现经验证等价的候选，记录实际删减与独立契约保留情况。
- [ ] T024 [US2] 运行受影响及完整隔离回归，将新失败/实际结果保存到 output/clarity015/phase-b/。

## Phase 6: B Polish（未授权）

- [ ] T025 保存 specs/015-rag-responsibility-clarity/phase-b-report.md 及相应状态导航；报告后暂停，等待用户验收。

## Dependencies 与执行策略

`T001 → T002 → T003 → T004/T005 → T006…T016 → T017/T018 → T019 → T020 → 用户验收/指示 → T021…T025`。

US1 是独立可交付 MVP；US2 依赖 A 的真实实现与用户验收。迁移期间共享 import 图，实施任务依次执行，避免中间状态被误作可运行结果。没有依赖安装、数据迁移或生产启动任务。

可并行的只读示例：US1 的 AST/hash 审计与隔离 pytest 子进程；US2 候选固定后，各候选的只读调用搜索与静态规模统计。此处不要求或授权并行代理，所有源码变更顺序落地。

按计划 A 对应 Phase 1–4（20 项），B 对应 Phase 5–6（5 项）。US1 13 项、US2 4 项，跨故事任务 8 项。完成 A 不勾选 B，不将迁移行数宣称为减码量。
