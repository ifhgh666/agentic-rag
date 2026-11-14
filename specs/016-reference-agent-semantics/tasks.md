# Tasks: 恢复参考 Agent 执行语义
**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/chat.md](contracts/chat.md)、[quickstart.md](quickstart.md)。
**原 B 授权沿革（历史保留）**: 用户在 A 总报告后继续授权 B；首题失败后停止。A=T001–T016 保持工程完成，T017 部分完成，T018 失败报告交付，不自动修复或补测。
**状态口径**: `[x]` 表示有可定位完成证据，不表示用户验收。未勾选可能为已有实现但收尾未核对，不能解释为从未开始。保留原 T001–T018 编号。

2026-10-28 C 收尾结果：F1/F2 已修复，T024–T026 完成交付，累计 26 项工程/采集任务有完成证据，待用户验收。产品仅删除两处闲置装配引用；本轮没有运行测试或模型，见 [C 报告](phase-framework-cleanup-20261028-report.md)。

2026-10-27 B 续测：用户在 R 报告后“继续计划”，恢复 Phase 6/T017 剩余四场景；只引用同条件的 R B01 证据，不重跑首题。原任务编号/历史报告保持，T017 在所有必要场景真实完成前仍未勾选。操作和停止规则见 [续测协议](phase-b-resume-20261027-protocol.md)。

2026-10-27 B 续测结果：四题真实首答 4 passed/0 failed/0 pending/0 not_run；引用同产品/模型条件的 R B01 证据，完成五类场景覆盖，T017 现已勾选。T001–T023 均有完成证据，旧计数段属于其日期的历史记录。用户验收仍待本轮报告；不自动扩大正式 PDF/ONNX/浏览器或旧题库评测。

2026-10-27 真实诊断补充：用户要求直接使用真实模型后，确认 B01 的思考模式/指定工具选择冲突，临时关闭思考的完整 B01 通过；未改产品代码/配置、未执行 B02–B05，不改变上述任务勾选。见 [phase-b-diagnosis-20261027-report.md](phase-b-diagnosis-20261027-report.md)。

## Phase 1: Setup（A）
- [x] T001 保存源码、Git状态/diff及历史失败快照到 `output/reference016/phase-a/before/` 和 `before-hashes.json`；本次文档改前快照另存 `output/reference016/planning-review-20261027-01/before-docs/`。
- [x] T002 按 Spec Kit 生成并维护 `specs/016-reference-agent-semantics/` 的规格、设计、契约和要求检查表，记录替代旧限制；文档完整不等于工程通过。
- [x] T003 固定 `backend/tests/fixtures/reference016/manifest.json`、`upstream/` 与 LICENSE，复用 `output/reference016/phase-a/reference016_guard.py` 和 `run.py`，保存 `before-full.json` / `.log` / `-guard.json`；基线退出 1 如实保留。

## Phase 2: Foundational（A）
- [x] T004 在 `backend/tests/unit/test_reference016_graph.py` 建立初始参考图红测并保存 `output/reference016/phase-a/red-reference.json` / `.log`；两项缺接口失败有记录，不将其冒称全部契约的行为红测。后续追加红测逐批保留。
- [x] T005 核对 `backend/app/core/legacy_{prompts,schemas,state,cache,summary}.py` 和独立 `query_analysis.py`、`answering.py`、`conversation.py`、`model_call.py`、`model_provider.py`、`legacy_rag.py` 的冻结消费边界，以 `backend/tests/unit/test_rag_architecture.py` 证明新图无旧治理/主图回退；已由架构守护、完整隔离回归与独立审查核对。

## Phase 3: US1 参考闭环（A，P1）
**目标**: 单问与三分支均沿参考节点收集和聚合，多轮不累计旧分支答案。
**独立验证**: `backend/tests/unit/test_reference016_graph.py`、`test_reference016_parity.py`、`test_rag_tools.py`；参考对照记录消息、调用、上下文、输出及有序聚合，不将并发完成先后当成稳定顺序。

- [x] T006 [US1] 核对 `backend/app/rag/graph_state.py`、`schemas.py`、`prompts.py` 的 reducer/两类摘要状态和原始提示；三必填字段 `is_clear: bool`、`questions: list[str]`、`clarification_needed: str`，允许空值容器，不新增旧 strict/anyOf/清空联动/列表硬上限；固定参考 AST 与包含节点访问的对照已核对。
- [x] T007 [US1] 在 `backend/app/rag/graph.py`、`nodes.py`、`edges.py` 核对主图和六节点子图：无工具先 collect；有工具且 `iteration_count >= 10` 或 `tool_call_count > 8` 时当前整批不执行；单问仍聚合；通过上述 US1 独立验证。
- [x] T008 [US1] 在 `backend/app/rag/tools.py` 核对参考字符串/真实 artifact、`limit=7` 及 `1<=limit<=20` 外围校验、完整 Parent 无分页/先搜索硬前置；工具后严格大于动态 `2000 + int(summary_tokens*0.9)` 才压缩，等于不压缩；覆盖 `test_rag_tools.py` 与实际参考阈值检查 `test_context_admission.py`；旧 test_context_compression 保留独立 legacy 行为。
- [x] T009 [US1] 核对 `backend/app/core/reference_model.py` 与 `backend/tests/unit/test_reference016_model.py`：兼容入口显式 function_calling、本地沿用 SDK 默认，研究 bind_tools；不传旧期限/配额/准入/输出上限，不业务重试或切换 provider；已有脚本模型不能代替 B 实测。
- [x] T010 [US1] 在 `backend/app/core/reference_session.py` 和 `backend/tests/integration/test_reference016_session.py` 核对 checkpoint 唯一会话、递归 50、同线程互斥、跨线程隔离、auto/continue/new/cancel 和失败清理；补充传输失败保留原 pending，普通失败不变澄清；原 pending 传输失败和本轮重复清理修复均进入最终完整回归。

## Phase 4: US2 交付（A，P2）
**目标**: 保留正常 API，公开真实事件，最终答案累计覆盖，来源由本次工具记录限定。
**独立验证**: `backend/tests/contract/test_reference016_stream.py`、`test_reference016_observation.py`、`test_reference016_diagnostics.py`、`backend/tests/security/test_reference016_privacy.py` 与前端 Chat/SSE/ProcessPanel 测试。

- [x] T011 [US2] 核对 `backend/app/core/pipeline.py`、`reference_observation.py`、`backend/app/api/chat.py`、`backend/app/main.py` 的真实事件、累计聚合答案、本次 Sources 交集、白名单、错误投影和只统计用量；`model_call_limit=null`，无 verification；按 `specs/016-reference-agent-semantics/contracts/chat.md` 验证断开后的实际清理边界。
- [x] T012 [P] [US2] 在 `frontend/src/pages/Chat.tsx`、`components/ProcessPanel.tsx`、`types/api.ts`、`api/client.ts` 及对应测试完成默认续答、隐藏核验、null 无分母、节点状态和工具正文展示；本轮 `output/reference016/phase-a/a-close-frontend-tests-20261027-01.log` 为 40 passed，`a-close-frontend-build-20261027-01.log` 退出 0；不代表浏览器或真实模型验收。
- [x] T013 [US2] 核对上述 API/SSE/隐私/会话覆盖，将 `output/reference016/phase-a/legacy-test-migration.md`、`unit-test-migration.md` 和 `api-test-migration.json` 汇入 `specs/016-reference-agent-semantics/test-migration.md` 索引；逐旧 nodeid 区分保留/替代/缺覆盖，不能以删测试或重写旧失败制造通过；149 个退役函数均在原账本有入口，最终实际覆盖及变化已由独立审查核对。

## Phase 5: A Polish（停止点）
- [x] T014 按 `specs/016-reference-agent-semantics/quickstart.md` 使用全新标签运行定向对照和修复后完整隔离回归，前端单测/构建；证据存 `output/reference016/phase-a/`。仅两项已列明旧 prompt 断言可为历史例外，仍报告退出 1；24 skipped/2 deselected 不算通过，任何新失败或 collection error 均不闭合本项。
- [x] T015 按 `specs/016-reference-agent-semantics/plan.md` 和 `test-migration.md` 完成独立规格/代码审查、必要修复并复验；核对原 `.env`、knowledge、正式数据及 `CURRENT_FAILURES.md` 保护清单；审查报告和哈希差异存 `output/reference016/phase-a/`，解释测试数量变化。
- [x] T016 保存 `specs/016-reference-agent-semantics/phase-a-report.md`，列实际命令/退出码、工程与真实区别、失败/限制、T 状态、B 范围，并更新 `README.md`、`docs/CURRENT_STATUS.md`；报告后暂停，等待用户验收。本项只表示工程交付，不表示用户验收。

## Phase 6: B真实验收（本轮获准）
2026-10-27 补充：用户在 A 总报告后明确继续，本轮 B 已获准，按 [phase-b-protocol.md](phase-b-protocol.md)依序执行；以下两项在真实完成前保持未勾选。
- [x] T017 [US1] 冻结真实模型身份和独立知识库，按 B 协议完成场景/判据、逐题首答和审阅。原 B01 首次失败保留；R 修复后的 B01 通过，本轮 `remaining-20261027-01` B02–B05 全部通过，源码/身份与 R 一致，引用首题而不重跑。五类必要场景均有真实证据，见 `phase-r-report.md` / `phase-b-resume-20261027-report.md`。本勾选表示采集交付完成，不代替用户验收。
- [x] T018 保存 `specs/016-reference-agent-semantics/phase-b-report.md` 和独立失败记录，列请求/模型工具次数/用量/耗时/首答结论；报告后暂停，不自动正式题库。

## Dependencies与策略
T001→T002→T003→T004→T005→T006→T007/T008/T009→T010→T011/T012→T013→T014→T015→T016→用户验收和明确指示→T017→T018。审查产生修复时，回到相应任务及 T014，不能沿用修改前结果。

A 对应 Phase 1–5，B 对应 Phase 6。US1 是算法最小闭环，US2 在它之上交付现有产品入口；内部独立可测不构成提前阶段验收。A 报告后用户明确继续，随后本轮 B 在首题失败后停止，不跨越后续诊断/修复/新批次边界。

US1 核心文件相互依赖，默认串行；US2 的 T012 在契约固定后可独立处理前端文件，和 T011 后端实现并行，集成前必须通过 T013。相同代码版本的后端和前端验证可独立运行，但不得并行真实模型采集。规划阶段的研究子代理只核对 SDK；本轮 T015 两位独立审查者分别完成规范和规格轴审查及修复复核。

## 已有证据与剩余工作

| 任务 | 当前事实 | 尚未闭合的事项 |
|---|---|---|
| T001–T004 | 原快照、设计、参考冻结、基线与初始红测已定位 | 不补造缺失的历史执行顺序 |
| T005–T009 | 架构守护、参考对照、完整隔离及静态审查已完成 | 工程交付待用户验收 |
| T010 | 原 pending 失败及新重复补充清理已修复 | 最终完整批次仅保留两项旧 prompt 失败 |
| T011/T013 | 公开事件、断开消费者、来源、隐私与迁移核对完成 | 真实服务兼容和质量留 B |
| T012 | mock/DOM 工程检查和构建记录已核对 | 真实 UI/模型质量不属于此勾选结论 |
| T014–T016 | 720 passed/两项旧失败，审查/保护及 A 总报告交付 | 报告后暂停，等待用户验收 |
| T017–T018 | B01 首次调用失败，0通过/1失败/4未运行；T018 报告交付 | T017 不宣称完成；诊断/修复/补测待明确指示 |

## Phase 7: R 兼容修复（2026-10-27 本轮获准）

用户在确认真实根因后“继续”，只执行本阶段；工程检查不能替代真实复验。原 T001–T018 编号和状态保持，T017 不因单题成功勾选。

- [x] T019 保存 `output/reference016/phase-b/fix-20261027-01/` 代码/Git/文档及保护快照，按 Spec Kit 在 spec/plan/research/data-model/contracts/quickstart/tasks 补齐 R 设计和边界。
- [x] T020 [US1] 在 `backend/tests/unit/test_reference016_model.py` 经真实 LangChain/OpenAI SDK 和假 HTTP 服务复现思考模式指定工具 400，保存修复前红测；覆盖实际产品 factory 的入口、工具往返及普通生成接缝。`r-fix-red-20261027-01` 为 1 failed/3 passed，失败类型与真实服务一致。
- [x] T021 [US1] 在 `backend/app/core/reference_model.py` 仅对精确 `deepseek-flash` 构造非思考原生模型，验证其他模型/Ollama 与不重试契约；`r-fix-related-20261027-01` 的 51 项隔离工程检查通过，真实质量另见 T022。
- [x] T022 [US1] 在 `output/reference016/phase-b/r-fix-20261027-b01-01/` 用无临时 override 的真实产品工厂执行一次完整 B01，completed、答案/来源经 Codex 核对通过；模型 4 次、搜索 1 次，原失败保留，不进入剩余 B 场景。
- [x] T023 保存 `specs/016-reference-agent-semantics/phase-r-report.md`，核对保护与文件差异，更新 README、docs/CURRENT_STATUS 和当前失败清单；报告后暂停，等待用户验收。

依赖 T019→T020→T021→T022→T023；全部属于同一 R 阶段，因单个模型工厂与单次真实请求依次验证，默认串行。原阶段和任务计数为历史记录，R 新增 5 项，不重排旧任务。

## 原 A/B 需求覆盖映射（历史保留）

| 需求 | 任务 | 验证定位 |
|---|---|---|
| FR-001 | T006/T007/T010/T014 | graph/parity/session |
| FR-002 | T006/T009/T014 | schema/prompt/model 对照 |
| FR-003 | T007/T008/T009/T010/T014 | edges/compression/model 参数 |
| FR-004 | T008/T011/T014 | rag_tools/observation |
| FR-005 | T003/T009/T015 | provider 参数/保护清单 |
| FR-006 | T010/T012/T013 | session/Chat |
| FR-007 | T011/T012/T013 | stream/SSE/ProcessPanel |
| FR-008 | T011/T013/T015 | sources/privacy/diagnostics |
| FR-009 | T005/T013/T015 | architecture/迁移账本 |
| FR-010 | T001/T003/T013/T014/T016 | 基线/日志/迁移/报告 |
| FR-011 | T016/T017/T018 | 报告停止点/授权门槛 |
| SC-001 | T003/T004/T007/T014 | 固定参考/脚本模型对照 |
| SC-002 | T007/T008/T010/T013/T014 | 闭环及交付验证 |
| SC-003 | T001/T011/T013/T015 | 保护/隐私证据 |
| SC-004 | T003/T014/T016/T017 | guard/活动范围/授权 |

合计 18 项：US1 6 项、US2 3 项、跨故事 9 项；A 的 16 项工程完成，T018 失败报告完成；T017 因四个场景未运行保持未勾选。B 质量未通过。表中覆盖表示计划关联，不表示运行通过。
# Phase 8: C 框架审阅收尾（2026-10-28 本轮获准）

用户在 F1/F2 静态审阅后继续授权本阶段；仅清理闲置装配并纠正架构指南，不新增产品行为或运行测试。原 T001–T023 完成记录及审阅报告保留。

- [x] T024 在 `backend/app/main.py` 移除闲置 ContextBuilder 导入及实例化，保留 `backend/app/knowledge/retrieval.py` 类及独立旧消费方；改前文件/哈希存 `output/reference016/framework-cleanup-20261028-01/`。
- [x] T025 在 `docs/repository-guide.md` 更新正常在线模块地图、调用图、模型/会话/工具/观察职责，并单列独立旧治理能力，纠正 F1；不覆盖原审阅或历史报告。
- [x] T026 用静态 AST、精确 diff、UTF-8/链接和原文件哈希核对范围，保存 `specs/016-reference-agent-semantics/phase-framework-cleanup-20261028-report.md` 并更新交接导航；报告后暂停，等待用户验收。

执行顺序 T024→T025→T026，均属单个 C 阶段；模型/图/接口没有变更，不运行新回归批次。新增 3 项，原 23 项编号保持。

## Phase 9: D 真实 PDF/ONNX 首批测试（2026-10-28 当前获准）

用户要求“开始真实测试”，只执行 [D 协议](phase-d-real-pdf-20261028-protocol.md) 的 Q1–Q4；目标是验证 US1 在真实 PDF/ONNX 与当前模型下的事实回答和证据，不把原工程/合成通过视为本轮成绩。

- [x] T027 在 `output/reference016/phase-d/formal-pdf-20261028-01/` 冻结题集/产品/配置/正式数据和旧证据，使用 `output/reference016/phase-d/capture_real_pdf.py` 创建只读隔离快照并检查真实 ONNX/BM25、PDF hash 和索引 ready；不打开正式 Qdrant 客户端或重建。真实预检 16 Point/384 维/7 结果；原 BM25 缓存缺失及原 hash 词表补齐单列，准备模型调用 0。
- [x] T028 [US1] 在同一输出目录按 Q1→Q2→Q3→Q4 的失败停止协议执行并保存首答、实时 events.jsonl、安全用量及 Codex review.json；实际 Q1 遗漏已召回的“合格的万用表”，0通过/1失败/3未运行，Q2–Q4 未执行，不重试、不注入答案、不运行 Judge。本勾选是按协议交付本批结果，不称四题全测或质量通过。
- [x] T029 保存 `specs/016-reference-agent-semantics/phase-d-real-pdf-20261028-report.md`，运行结束时 423 项保护无差异；报告阶段仅向当前失败清单增加 D 记录，旧内容保持。已更新状态与证据，报告后暂停，等待用户验收。

依赖 T027→T028→T029，无可并行的模型采集项；三个任务为同一 D 阶段。任务完成仅表示有结果证据，不表示四题通过或用户验收。若先遇到失败/阻断，报告实际执行范围，后续题目不自动恢复。

## Phase 10: E 全量真实测试与答案比较（2026-10-28 当前获准）

用户要求全测且前题失败不阻断后题，按 [E 协议](phase-e-full-gold-20261028-protocol.md)只执行本阶段。

- [x] T030 在 `output/reference016/phase-e/full-gold-20261028-01/` 冻结全部 gold-1.0/产品/配置/数据和旧证据，使用 `output/reference016/phase-e/capture_full_gold.py` 创建真实 PDF/ONNX/BM25 隔离快照并预检；原 D 首答保持。15 场景/19 轮、16 Point/384 维预检通过，准备模型调用 0。
- [x] T031 [US1] 使用同一侧车依序完成 Q1–Q15/19 轮原问题和动作（同时覆盖 US2 澄清动作），场景隔离、场景内保留 checkpoint，失败继续、无重试；每轮 raw/events、用量、每场景命令和 capture-summary.json 均已保存。15 个子进程退出 0，无未运行输入，不代表语义全通过。
- [x] T032 在 `specs/016-reference-agent-semantics/phase-e-answer-comparison-20261028.md` 和 `phase-e-full-gold-20261028-report.md` 交付完整原答/正确答案/行为与逐题审阅，保存 comparisons.json 和 15 份 review；11通过/4部分正确未通过，346 项运行保护无差异。分类型统计与额外错误区分，报告后暂停，等待用户验收。

依赖 T030→T031→T032，无并行模型采集，旧任务编号不变。任务完成不等于质量全通过；用户全测要求优先于 D 的停止策略，执行中不插入框架修复。

