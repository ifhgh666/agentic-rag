# Tasks: P3 失效依赖清理

**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[兼容契约](contracts/compatibility.md)、[quickstart.md](quickstart.md)。

**Status**: A/B 共 20 项工程任务完成，待用户验收；本轮仅 B。完整后端 802 passed / 2 failed / 24 skipped / 2 deselected，前端 27 passed、noEmit 通过，见 [B 阶段报告](phase-b-report.md)。报告后暂停，等待用户验收。

**Tests**: FR-009–FR-012 和 SC-001–SC-006 明确要求受控工程验证，故包含测试。先保存行为红测，再局部实现；导入/收集失败不冒充业务红测。旧失败和首答不覆盖。

**Organization**: 对应已规划的两阶段，US1=主图依赖真实、US2=独立能力与兼容。既有项目无需另建无交付价值的初始化/基础阶段；必要基线和保护归入每阶段入口，最终收尾归入 B。公开兼容装配是 A 解除主图关联的必要组成。

## 格式和边界

任务格式 `- [ ] Tnnn [P?] [USn?] 描述与相对仓库路径`。[P] 只表示不同文件可独立处理，不自动授权子代理或跨阶段并行。每个阶段报告保存后暂停；不提交、推送、发布 GitHub ticket 或调用真实模型。

## Phase 1 / A：US1 主图实际依赖与兼容装配（MVP）

**Goal**: 正常图不再构造/依赖旧改写、专用 rewrite cache 或 EvidenceSelector，原合法入口、注入和显式属性访问仍可用。

**Independent Test**: 在 graph.run 证明旧构造计数为 0、预算/cache 身份及行为保持；原 builder 调用、按需属性读写和并发首次读取可独立验证，不要求先完成 B。

- [x] T001 [US1] 在 output/cleanup012/engineering/phase-a-20261022/ 保存源码/Git/原文档与失败基线，从 P2 D guard/运行器准备本阶段版本；自检拒绝真实 Dense/普通连接、允许 Windows socketpair、禁用 dotenv，所有数据/basetemp 隔离；只读核对 requirements、hooks、适用 AGENTS 和 ignore。
- [x] T002 [P] [US1] 在 backend/tests/unit/test_inactive_graph_dependencies.py 先保存默认 fake/scripted ollama 图的旧服务及专用缓存构造红测，另保存真实 scripted 检索→回答/缓存/预算基线；保留 isinstance 类型关系，不断言所有 BoundedCache=0（依赖 T001）。
- [x] T003 [P] [US1] 在 backend/tests/unit/test_graph_compatibility.py 建立原 builder 位置/关键字调用、注入身份和按需属性行为测试；覆盖“赋值 None 不等于尚未创建”“setter 不新增绑定”“并发首次只发布一个对象”、原 provider/fake 选择/TTL/容量捕获（依赖 T001）。
- [x] T004 [US1] 在 backend/app/rag/graph.py 实现同文件唯一 _build_model_subgraph，正常图显式传五项实际依赖；旧 build_agent_subgraph 保留签名适配。落实 settings 原优先级、“budget/cache 引用同一对象，不复制计数”，旧六项参数不新增语义，不创建新模块（依赖 T002、T003）。
- [x] T005 [US1] 在 backend/app/rag/graph.py 去正常初始化的 QueryGenerator/rewrite cache/EvidenceSelector；保留 ctor 原 or 选择、显式 ModelQueryGenerator budget/request_cache 绑定，不替换 provider/cache/index_version，不为注入对象创建多余旧缓存（依赖 T004）。
- [x] T006 [US1] 在 backend/app/rag/graph.py 完成两个普通按需属性和实例锁：UNINITIALIZED/READY/ASSIGNED 区分，“主图构造/执行不得读取兼容属性”“赋值后原样返回，含 None”；捕获原引用和缓存策略标量，读取不调用 generate/select，异常不缓存半成品（依赖 T005）。
- [x] T007 [US1] 在 backend/tests/unit/test_inactive_graph_dependencies.py、backend/tests/unit/test_graph_compatibility.py 完成行为绿测，包含注入不调用、构造 0、旧入口闭环、并发/赋值/异常、provider 延迟初始化与有效 settings/共享对象身份；不比较动态 ID、耗时或资源剩余提示字节（依赖 T006）。
- [x] T008 [US1] 运行 backend/tests/unit/test_graph.py、test_model_agent_loop.py、test_query_planner.py、P1 四组准入与对应 contract、P2 governance/attempts/consumers/delivery、request_deadline 和 diagnostics/privacy 相关检查；记录实际结果至 output/cleanup012/engineering/phase-a-20261022/，原失败仍明示（依赖 T007）。
- [x] T009 [US1] 核对 backend/app/rag/graph.py 及公开 SSE/私有样本，保存阶段差异/guard/源码 hash；确认 model_call/provider/budget/prompts/schema、B 的 nodes/edges/procedure/config 和前端源码未改，不删除独立接口或延期常量（依赖 T008）。
- [x] T010 [US1] 更新 specs/012-inactive-dependencies/spec.md、plan.md、tasks.md 实际工程状态，保存 phase-a-report.md，列实际命令/退出码、红绿/原失败、构造与兼容证据、未测真实范围及 B 边界；“报告后暂停，等待用户验收”，不得自动进入 B（依赖 T009）。

## Phase 2 / B：US2 无效状态与兼容收尾

**Goal**: 正常图不再传无业务作用的 procedure 状态，独立公开能力、参数和配置含义明确；完成 P3 最终组合回归。

**Independent Test**: 旧参数四组合、Outcome/schema、独立证据/改写/生成及旧配置解析保持；完整图/SSE/历史/诊断/前端消费与原约束一致。

- [x] T011 [US2] 在 output/cleanup012/engineering/phase-b/ 创建不覆盖 A 的新基线和 guard，读取 A 报告及原失败，保存本阶段源码/文档/Git 状态；不把 A 成绩当 B 已运行。
- [x] T012 [US2] 在 backend/tests/unit/test_inactive_graph_dependencies.py 和 test_graph_compatibility.py 先保存正常 procedure 写入/转发的行为证据及兼容矩阵，覆盖 Outcome 默认 False/缓存、三字段 schema 拒绝 extra、生成两个 bool 四组合、空证据/有限修复/首答（依赖 T011）。
- [x] T013 [US2] 在 backend/app/rag/nodes.py、edges.py 移除正常 prepare→Send→agent 的 procedure 写入/复制；graph_state.py 保留 total=False 可选声明并标注兼容，不改 GraphRunResult、ThreadState 或诊断结构（依赖 T012）。
- [x] T014 [US2] 在 backend/app/rag/generator.py、query_analysis.py 只补兼容说明：旧关键字、默认值、结果三元组及 requires_procedure 字段保持；不恢复分类/引用选择，不新增 warning，不删除 BUDGET_FALLBACK_PREFIX 或预存低收益符号（依赖 T013）。
- [x] T015 [US2] 在 backend/app/config.py、backend/.env.example 说明 agent_parent_threshold_chars 当前无主图作用；保留字段/环境名/默认 240/解析，不读取覆盖 .env，不恢复自动 Parent 路由（依赖 T014）。
- [x] T016 [US2] 运行 backend/tests/unit/test_v3_7_procedure_evidence.py、test_v3_4_evidence.py、test_query_planner.py、test_prompt_consumers.py、test_v4_query_schema.py、P3 新用例及 scripts/replay_v3_6_q3.py 的调用形状核对；脚本只作静态/隔离契约，不运行真实模型（依赖 T015）。
- [x] T017 在 output/cleanup012/engineering/phase-b/ 运行 quickstart.md 的完整后端 guard 回归，明确排除两项真实嵌入用例，不算通过；保留两项旧提示词断言及任何新失败，不扩大额度或改 prompt 造通过（依赖 T016）。
- [x] T018 运行 frontend/src/api/sse.test.ts、pages/Chat.test.tsx、components/ProcessPanel.test.tsx 所代表的全部前端单测和 noEmit/incremental false 类型检查；如源码未改不构建，保存完整命令/退出状态到本阶段 output（依赖 T017）。
- [x] T019 核对 backend/tests/security/、公开事件、私有首次结果与历史/诊断边界，更新 docs/repository-guide.md、specs/012-inactive-dependencies/quickstart.md、contracts/compatibility.md、plan.md 最终事实；逐项列移除/保留/延期，不重写 CURRENT_FAILURES.md 或旧报告（依赖 T018）。
- [x] T020 更新 specs/012-inactive-dependencies/tasks.md 并保存 phase-b-report.md，逐项对照 FR-001–FR-012 / SC-001–SC-006，列实际命令/退出码、原失败与真实未测；“报告后暂停，等待用户验收”，不自动真实复验、关闭 GitHub、提交/推送（依赖 T019）。

## Dependencies & Execution Order

```mermaid
flowchart LR
    P[已交付规划] --> A[A / Phase 1：US1]
    A -. 报告暂停，用户指示后 .-> B[B / Phase 2：US2 与最终组合]
```

A：T001 → {T002,T003} → T004 → T005 → T006 → T007 → T008 → T009 → T010。B：T011 → T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020。B 最终验证依赖 A，技术上独立 procedure/公开能力测试可自成闭环，不构成跨阶段授权。

## Parallel Examples

US1：T001 后 T002 与 T003 可分别编写不同测试文件，共用既有 tests helper，无未完成依赖；生产 graph.py 变更串行。US2：涉及同一 nodes/edges/state 和兼容测试，默认串行，不为凑 [P] 拆无意义任务；前端单测与类型检查可在 T018 内独立执行。

## 覆盖与交付策略

| 范围 | 任务 |
|---|---|
| FR-001–FR-004 / SC-001–SC-002 | T001–T009、T019 |
| FR-005–FR-006 / SC-004 | T003–T007、T012–T016 |
| FR-007–FR-008 / SC-003、SC-005 | T007–T009、T012–T019 |
| FR-009–FR-012 / SC-001、SC-005–SC-006 | 各阶段基线/guard/报告及 T017–T020 |

数据模型的依赖条目以本表和证据映射维护，不新增运行期清单类；按需属性状态、共享对象、setter/None/provider 捕获约束已明确落入 T003–T007。20 项中 A/US1 10 项、B/US2 6 项、B 收尾 4 项；2 项 [P]。A 为最小独立交付；A/B 分轮执行完成，任务勾选不等于验收。
