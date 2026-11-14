# 任务：问题理解、澄清与 RAGAS 标准答案评估

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[接口契约](contracts/chat-and-evaluation.md)、[验收指南](quickstart.md)。

**执行边界（2026-10-07 首批结束）**：阶段 1～4 已实施；全部 15 题已获用户批准，T020 完成。T026 首批真实采集/评估已执行，并达到批准的 80 次 Judge 上限；22 项评分、13 项超时、15 项预算不足、Q9 的 5 项链路失败及 20 项不适用如实保存，见[本批报告](formal-ragas-report.md)。完整评分、回答人工签收和 T027/T028 总验收未完成；本批汇报后暂停，不追加调用或进入业务修复。历史报告保留原结论。复选框不等于答案准确率。

**2026-10-08 当前切片**：用户要求“先校准题集”，仅执行下方 T030。新版全部待人工确认，不继承旧批准及预算。原批 Q2 的保护动作漏答归因须按[校准报告](dataset-calibration-report.md)修正；旧原始结果不覆盖，T026/T027/T028 不因校准而变为通过。

## 阶段 1：准备与基线（计划阶段 A）

**目标**：冻结当前缺陷和 PDF 来源，形成五题标准答案草案；不改生产问答逻辑。

- [X] T001 核对当前 Git 状态、`.gitignore`、`specs/004-query-clarification-ragas/checklists/requirements.md` 与 `.specify/extensions.yml`，在 `specs/004-query-clarification-ragas/phase-a-report.md` 记录准备状态。
- [X] T002 运行现有 `backend/tests/` 相关 pytest 与适用的 V3-5 基线检查，核对 `specs/003-v3-ollama-rag-quality/v3-5-report.md` 和正式库验收记录，在 `specs/004-query-clarification-ragas/phase-a-report.md` 区分本轮实测与历史数据。
- [X] T003 [P] 读取 `backend/data/documents/b8d6bda5-5ff7-4b2c-9e72-1157f199bf8b/source.pdf` 的 SHA-256、页数、原文和必要页面渲染，核对文档清单后在 `specs/004-query-clarification-ragas/phase-a-report.md` 记录 PDF 身份与索引匹配状态。
- [X] T004 [P] 在 `backend/tests/unit/test_phase_a_known_gaps.py` 编写三项预期失败的回归样例：明确型号被代词正则误判、待澄清时新题被拼接、缺少安全前置步骤仍获高分；测试不得调用云模型或修改正式索引。
- [X] T005 依据 T003 的 PDF 原文，在 `specs/004-query-clarification-ragas/gold-cases-draft.json` 建立 Q1–Q5 五题草案，逐题记录 `case_id`、问题、`document_sha256`、页码/逐字引文、标准答案、必答事实、禁止误答与 `review_status=draft`；未经人工确认不得标为正式题集。
- [X] T006 汇总 T001–T005 的命令、结果、缺陷复现、五题草案与未决事项至 `specs/004-query-clarification-ragas/phase-a-report.md`，复查不包含密钥/密码，并向用户汇报后暂停。

**独立验收**：三个已知缺陷均有可重复证据；PDF 的真实 SHA-256 和页码已核对；五题均为草案且来源可追溯；未修改正式 PDF/索引和生产代码。

---

## 阶段 2：共用基础（计划阶段 B 前置）

**依赖**：阶段 1 完成且用户确认继续。

- [X] T007 为 `backend/app/rag/model_schema.py` 中的问题分析结果定义 `relation` 取 `new_question/clarification/uncertain`、`questions` 为 0～3 条去重非空问题、不清楚时 `questions=[]` 且 `clarification_needed` 必填的验证契约，并在 `backend/tests/unit/test_v4_query_schema.py` 先写失败测试。
- [X] T008 为 `backend/app/rag/graph_state.py` 与 `backend/app/rag/conversation_memory.py` 设计唯一线程状态：`thread_id` 非空、`state_version` 递增、`phase` 仅 `idle/awaiting_clarification/answering`、`pending_query` 仅在待澄清时存在、普通消息排除工具/内部消息；在 `backend/tests/unit/test_v4_thread_state.py` 先写失败测试。

**检查点**：结构化分析与线程状态契约固定，尚未改变在线行为。

---

## 阶段 3：用户故事 1——自然理解每条问题（P1，计划阶段 B）

**独立测试**：清楚独立题、指代追问、双问题、失败降级各至少一个用例；型号/数值/限定条件不得凭空改变。

- [X] T009 [P] [US1] 在 `backend/tests/unit/test_v4_query_analysis.py` 编写上述四类失败测试及分析输出越界/无效 JSON 测试，不依赖正式索引。
- [X] T010 [US1] 在 `backend/app/rag/query_analysis.py` 实现每条新消息至多一次结构化模型分析，移除正则语义直通决定权，保持清楚题原样和最多 3 个独立问题，保留 `thread_id+问题+历史指纹+索引版本` 缓存。
- [X] T011 [US1] 在 `backend/app/rag/graph.py` 和 `backend/app/rag/cost_control.py` 接入分析调用预算/追踪；普通简单题分析＋生成最多 2 次，失败不得伪装 `is_clear=true`，摘要额外调用须有独立闸门。
- [X] T012 [US1] 运行 `backend/tests/unit/test_v4_query_analysis.py` 及相关 `backend/tests/integration/test_question_answering.py`，将结果、每题 Token/耗时记录在 `specs/004-query-clarification-ragas/phase-b-report.md`。

**检查点**：用户故事 1 独立可测；未自动进入下一故事。

---

## 阶段 4：用户故事 2——澄清不会吞掉新问题（P1，计划阶段 B）

**独立测试**：待办补充、新题、取消、不确定各至少两个样例，且不同 `thread_id` 不串题。

- [X] T013 [P] [US2] 在 `backend/tests/integration/test_v4_clarification_flow.py` 为同线程补充/换题/取消/不确定、跨线程隔离及同线程并发先写失败测试。
- [X] T014 [US2] 在 `backend/app/rag/conversation_memory.py`、`backend/app/rag/graph_state.py` 与 `backend/app/rag/graph.py` 合并待办唯一事实来源，实现 `pending_query`、补充列表、普通近期消息和摘要分离；`phase` 转移及 `state_version` 必须防止并发覆盖。
- [X] T015 [US2] 在 `backend/app/schemas/chat.py`、`backend/app/api/chat.py` 和 `backend/app/rag/pipeline.py` 增加可选 `action=auto/continue_clarification/new_question/cancel`；除 `cancel` 外问题非空且不超过 2000 字符，`cancel` 必须有 `thread_id`，澄清轮次不得发送普通答案。
- [X] T016 [US2] 在 `frontend/src/pages/Chat.tsx`、`frontend/src/types/api.ts`、`frontend/src/api/client.ts` 增加继续补充/新题/取消交互与新 `analysis/clarification` SSE 契约，并补充前端对应测试。
- [X] T017 [US2] 在 `backend/tests/integration/test_v4_clarification_flow.py` 和前端测试运行全部场景，更新 `specs/004-query-clarification-ragas/phase-b-report.md`，阶段 B 汇报后暂停。

**检查点**：澄清不吞新题；模型不确定时提供明确选择；阶段 B 结束。

---

## 阶段 5：用户故事 3——维护可信标准答案集（P2，计划阶段 C）

**独立测试**：每题逐字引文可在相同 PDF 页码找到，只有 `reviewed` 且文档 SHA-256 匹配者进入正式评估。

- [X] T018 [P] [US3] 在 `backend/tests/unit/test_v4_gold_dataset.py` 编写题集模式、文档指纹、页码/逐字引文、审核状态与无答案题验证测试。
- [X] T019 [US3] 在 `backend/scripts/validate_v4_gold_dataset.py` 实现只读题集验证；`case_type` 仅 `answerable/unanswerable/clarification_flow`，可回答题须有标准答案、至少一条来源、必答事实和审核记录，文档版本不符时拒绝正式评分。
- [X] T020 [US3] 将 `specs/004-query-clarification-ragas/gold-cases-draft.json` 扩充为 `specs/004-query-clarification-ragas/gold-cases-v1.json`，至少 15 题且含 Q1–Q5 与 10 个不同类别变体/异常；逐题核对 `backend/data/documents/b8d6bda5-5ff7-4b2c-9e72-1157f199bf8b/source.pdf`，记录 reviewer/reviewed_at，Q3 步骤与顺序必须完整。
  - 2026-10-02：已建立 15 题候选集、核对 26/26 条来源引文并完成四页渲染检查；[人工审核稿](gold-cases-review.md)等待维护者确认。所有题目仍为 `draft`，`reviewer/reviewed_at/review_kind` 均为空，不把自动核对冒充人工审核。
  - 2026-10-07：用户明确确认全部 15 题及本批 Judge 上限 80 次；登记为 `gold-1.0/reviewed`，只更新审核/版本字段与说明，不改变任何题目事实。正式准入 true、26/26 条引文通过，详见[授权记录](gold-review-approval.md)。系统回答复核与 T026 仍未完成。
- [X] T021 [US3] 运行 `backend/scripts/validate_v4_gold_dataset.py` 和单元测试，在 `specs/004-query-clarification-ragas/phase-c-report.md` 记录 100% 核对结果、未审核题与失配演练；阶段 C 汇报后暂停。

**历史检查点（阶段 C 当时）**：题集可以溯源，但人工审核未通过；见[阶段 C 报告](phase-c-report.md)。**当前更新（2026-10-07）**：用户批准后正式准入为 `true`，T020 完成；不改变阶段 C 当时的记录。

---

## 阶段 6：用户故事 4——离线评估与诚实在线展示（P2，计划阶段 D）

**独立测试**：固定一题能重复得到分项结果；缺步骤/无证据不会在线显示固定可信分；Judge 不进入在线请求。

- [X] T022 [P] [US4] 在 `backend/tests/unit/test_v4_eval_runner.py` 和 `backend/tests/integration/test_v4_verification_event.py` 先写离线指标、`not_applicable`、错误状态、SSE 版本与无额外在线 Judge 调用的失败测试。
- [X] T023 [US4] 在 `backend/scripts/evaluate_v4_ragas.py` 与实施时锁定的离线依赖清单中实现本地 Judge 兼容性冒烟、五项指标和逐题结果保存；记录回答模型/Judge/RAGAS 版本、真实答案与检索上下文、各自 Token/耗时，不适用不得填 0。
  - 2026-10-02：合成一题在兼容性调试环境及不继承系统包的干净评估环境各通过一次；每次五项均成功、Judge 8 次/6,745 Token、云端 0 次。101 个依赖全部固定版本，干净环境 `pip check` 通过。实际 Graph 输出导出函数已交付，正式题集采集/人工验收仍属于 T026，并未执行。
- [X] T024 [US4] 在 `backend/app/rag/evaluator.py`、`backend/app/schemas/chat.py` 和 `backend/app/rag/pipeline.py` 迁移 `schema_version=2` 的 `verification` SSE：证据、引文、数值及完整性分别报告已核验/存在问题/未评估，停止输出固定 `overall` 分数。
- [X] T025 [US4] 在 `frontend/src/components/ScoreCard.tsx`、`frontend/src/pages/Chat.tsx` 和 `frontend/src/types/api.ts` 迁移为可核验状态卡，故意漏掉 Q3 安全步骤时不得显示“完整可信”；运行前端测试。
- [ ] T026 [US4] 执行本地离线评估和人工必答点复核，在 `specs/004-query-clarification-ragas/phase-d-report.md` 保存逐题分项与冲突结论；阶段 D 汇报后暂停。
  - 2026-10-07：15 题/19 轮真实输出已保存并验证；80 次 Judge 上限已达到，22/50 个适用事实指标有分数，只有 Q7 五项齐全。原始 `completed_with_errors` 报告及 Q2 高分/必答点冲突已保存；全部回答人工签收待完成，T026 不勾选，不自动追加调用。后端 326 项通过，见[本批记录](formal-ragas-report.md)。

**检查点**：在线无伪分数，合成一题离线指标可重跑且无云端模型调用；正式 15 题评估与人工复核尚未完成，阶段 D 未整体验收通过。见[阶段 D 报告](phase-d-report.md)，本次报告后暂停。

---

## 阶段 7：收尾与正式库回归（计划阶段 E）

- [ ] T027 在 `backend/tests/integration/test_v4_formal_regression.py` 覆盖 Q1–Q5、至少 10 个扩展样例、Q3 连续 3 次安全步骤与来源核验，显式检查旧 V3-6～V3-8 的生成修复前置依赖。
  - 2026-10-07：回归文件已交付，23 项离线检查通过。15 个场景只检查脚本化分析/空索引协议；既有五题 UI 与 Q3 三次同版本捕获已审计。扩展题真实质量未采集，Q2 缺少候选必答点“立即断开主回路”，因此完整验收仍不勾选。
- [ ] T028 运行 `backend/tests/` 与前端测试、构建和正式库问答，在 `specs/004-query-clarification-ragas/phase-e-report.md` 对比 V3-5 的 9,377 Token/约 225 秒基线，列出实际/估算用量及未完成事项。
  - 2026-10-07：后端 318 项、前端 20 项通过，构建成功；已交付成本与差异报告。复用同版本 V3-8 正式 UI 记录（10 次/12,216 Token/248.995 秒），本轮新增实际模型调用为 0；正式 15 题回归与复核仍待准入，不将旧口径结果当作全量验收。
- [X] T029 检查 `specs/004-query-clarification-ragas/quickstart.md` 的验收场景、`specs/004-query-clarification-ragas/spec.md` 的成功标准与 `specs/004-query-clarification-ragas/phase-e-report.md` 一致；向用户汇报后暂停。
  - 2026-10-07：已逐项列出 SC-001～SC-006 的证据与未完成项，修正文档旧评分/引用编号说明，保持原成功标准；工程交接不等于全部功能验收通过。

## 校准后追加任务（逐项确认，不自动执行）

- [X] T030 [US3] 校准题干与核心事实、可选补充、语义表述及澄清前置；保留旧题集与报告，生成 `gold-cases-v2.json`、`gold-cases-v2-rubrics.json`、`clarification-state-fixtures-v2.json`、`gold-cases-v2-review.md`、`dataset-calibration-report.md` 与离线产物完整性测试。只做原文／结构核对，模型调用为 0，汇报后暂停。
- [ ] T031 [US3] 维护者审核 `candidate-2.0` 的 23 个场景、可选事实与流程规约；仅在明确确认后登记新版人工审核，旧版批准不继承。确认题集不同时授权模型重跑。
- [ ] T032 [US4] 在另获实施确认后对齐离线采集与报告：端到端前置失败阻塞后续、隔离待办夹具与真实入口分开、改写问题按对象／意图／约束核验、知识组与挑战结果分别汇总；先离线边界测试，不改业务语义路由。
- [ ] T033 [US4] 在 T031/T032 通过且用户另行确认样本和新预算后，选择组内代表与必要挑战执行小批真实采集／评估；错误与未测保持诚实记录，实际回答另行人工签收，不复用旧版分数为新版成绩。汇报后暂停。

**依赖**：T030 → T031 → T032 → T033；只新增后续工作说明，不代表用户已授权执行 T031–T033。T026/T027/T028 的未满足标准继续保留。

## 原阶段依赖与并行机会

- 阶段 1 不依赖后续功能；T003 的 PDF 核对与 T004 的纯代码复现可并行，T005 依赖 T003，T006 汇总全部阶段 A 结果。
- 阶段 2 依赖阶段 1。用户故事 1、2 的测试可准备为并行文件，但线程状态与入口分析集成要按 T010→T014/T015 顺序验证；阶段 B 的共同验收由 T017 收束。
- 用户故事 3 可在阶段 B 后独立构建离线题集；用户故事 4 依赖题集与在线结果契约。正式库阶段 E 依赖旧 Q3 生成修复，不可单凭指标代替答案修复。
- 并行示例：T003 与 T004；T009 与 T013；T018 可与前端展示设计准备并行，但同一文件的改动必须串行。

## 实施策略

最小交付是阶段 A 的可复现基线和五题草案；在用户确认后才进入阶段 B 的模型优先入口与澄清。阶段 C、D、E 分别可独立演示和验收。所有测试任务先于相应实现；每个阶段结束都停止，不能因为任务清单已列出就自动执行余下阶段。
