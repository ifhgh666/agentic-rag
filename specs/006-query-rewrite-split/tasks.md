# Tasks: 问题补全、改写与拆分 V1

**Input**: [plan.md](plan.md)、[spec.md](spec.md)、研究、数据模型、契约、验收矩阵。
**Status**: 2026-10-11：A–D工程完成；用户要求E遇错继续，新版完整输入17题首答已采齐，10通过、7失败、0未运行。见[完整E报告](phase-e-completed-all-20261011-report.md)。采集器继续模式26项scripted工程检查通过；产品prompt未改，原补全失败及F失败保留。T031质量仍未通过，T034及005 T018不变，本轮未执行F。报告后暂停，等待用户验收。
**Tests**: 规格明确要求针对性工程测试和有限真实人工验收。两类结论必须分开。
**Latest run**: 新版完整输入首答覆盖17/17；前八题原记录保留，本轮只采剩余九题并遇错继续。完整结果10通过、7失败、0未运行，质量验收仍未通过，未将原代词补全案例或新版失败改判通过。
**Organization**: 按四个用户故事分组；计划 A–F 与下述 Phase 的对应是唯一执行边界。本轮明确授权仅继续E；普通空格差异按用户澄清接受，实质补全/拆分质量仍人工验收。阶段报告后暂停。

## Phase 1: Setup（阶段A）

- [x] T001 固定RW01–RW24案例原文、历史/待办、预期与验证类型于 `backend/tests/fixtures/query_rewrite_v1_cases.json`，对应FR-003–FR-010、FR-017及 `acceptance-matrix.md`。
- [x] T002 在 `specs/006-query-rewrite-split/implementation-baseline.md` 记录既有修改、模型/非敏感预算、005未通过项及正式库指纹，不变更.env或索引，覆盖FR-015、FR-018。

## Phase 2: Foundational（阶段A，故事前置）

- [x] T003 在 `backend/app/rag/model_schema.py` 定义严格三字段QueryAnalysis：“必填严格bool/list[str]/str、禁止额外字段、最多3问、每问≤2000、清楚需1–3问及空澄清、不清楚需空问题及非空澄清”；仅trim正文首尾，判重不改正文，覆盖FR-002。
- [x] T004 在 `backend/app/rag/query_analysis.py`、`backend/app/rag/graph_state.py`、`backend/app/rag/graph.py` 迁移运行适配：模型不输出relation/requires_procedure，兼容关系来自明确动作；有待办auto先零调用返回动作选择，保证A切换协议后不靠旧relation处理；source/error/trace来自实际执行，不新增意图分类，覆盖FR-001、FR-008–FR-009、FR-014。
- [x] T005 在 `backend/app/rag/query_analysis.py` 改入口缓存为原题精确哈希+上下文/动作/线程/索引/模型身份+query-rewrite-v1版本，保留TTL300秒/256条，覆盖FR-013。
- [x] T006 在 `backend/app/rag/graph.py`、`backend/app/rag/conversation_memory.py` 修复原题/确认补充历史保存及失败回滚；禁止把rewritten_query存为用户原话，覆盖FR-007、FR-009–FR-010。
- [x] T007 在 `backend/tests/fakes/providers.py`、`backend/tests/unit/test_v4_query_schema.py`、`backend/tests/unit/test_v4_query_analysis.py` 迁移旧模型输出夹具和协议预期；不把fake当真实质量证明，覆盖FR-002、FR-017。

## Phase 3: User Story 1 — 完整单问（P1，阶段A，MVP）

**Independent Test**: 原题承载、严格输出、缓存、一次调用/失败的工程用例通过；真实原文保留待E。

- [x] T008 [US1] 在 `backend/tests/unit/test_query_rewrite_v1.py` 覆盖RW01–RW06原题承载、内部空白/大小写与RW22缓存失效；替换 `test_v4_query_analysis.py` 中接受无益单问改写的旧断言，覆盖FR-003、FR-013、SC-001。
- [x] T009 [US1] 在 `backend/app/rag/query_analysis.py` 更新单节点三字段提示和解析，移除入口 `_analysis_literals_supported`/constraint_mismatch阻断；保留摘要使用的 `_literal_constraints_preserved`，不强制len==1恢复原句，覆盖FR-001、FR-003、FR-006、FR-011。
- [x] T010 [US1] 在 `backend/tests/unit/test_query_rewrite_v1.py`、`backend/tests/unit/test_v4_query_analysis.py` 覆盖RW20–RW23格式失败/空值/零重试/无预算/窗口/错误数字承载，验证原题仍保留且无隐式工具或云切换，覆盖FR-011–FR-012、FR-015、SC-004。
- [x] T011 [US1] 运行A范围针对性工程检查，保存命令/退出码/限制到 `specs/006-query-rewrite-split/phase-a-report.md`，标记真实保真未测，报告后暂停，覆盖FR-017–FR-018、SC-007。

## Phase 4: User Story 2 — 补全与澄清（P1，阶段B）

**Independent Test**: 固定上下文、动作、待办回滚及前端选择均可单独验证；真实语义待E。

- [x] T012 [P] [US2] 在 `backend/tests/integration/test_v4_clarification_flow.py` 覆盖RW07–RW10、RW17–RW19的明确动作、待办隔离与失败回滚，覆盖FR-004、FR-008–FR-010、SC-002。
- [x] T013 [US2] 在 `backend/app/rag/query_analysis.py` 明确最少必要上下文输入、当前条件优先、未确认触发的条件式、陌生术语保留及具体澄清提示，覆盖FR-004、FR-006。
- [x] T014 [US2] 在 `backend/app/rag/graph.py`、`backend/app/rag/conversation_memory.py` 沿用A动作适配，完善continue确认补充的合并/保存、new屏蔽旧待办及取消/无待办的事务回滚；与T012固定案例联调，覆盖FR-008–FR-010。
- [x] T015 [US2] 更新 `frontend/src/pages/Chat.tsx`、`frontend/src/pages/Chat.test.tsx` 中待办提示和三个按钮，去掉直接auto输入被理解为自动关系分析的承诺，验证B前端/契约检查，覆盖FR-008–FR-009。
- [x] T016 [US2] 保存B工程结果、真实未测项及停止点到 `specs/006-query-rewrite-split/phase-b-report.md`，报告后暂停，覆盖FR-017–FR-018、SC-007。

## Phase 5: User Story 3 — 拆分与完整原题（P1，阶段C）

**Independent Test**: 现有Send分支承载共同条件、原题和比较目标；单分支无多余汇总调用，多分支保留汇总额度。

- [x] T017 [P] [US3] 在 `backend/tests/unit/test_graph.py`、`backend/tests/unit/test_query_rewrite_v1.py` 覆盖RW11–RW15及原题/相关子问分发、≤3容量和不可分需求，覆盖FR-005–FR-007、SC-003。
- [x] T018 [US3] 在 `backend/app/rag/query_analysis.py` 的同一提示中明确独立需求拆分、共同条件、如果触发依赖和四问容量澄清；不加入Python语义分类或新调用，覆盖FR-005–FR-006。
- [x] T019 [US3] 在 `backend/app/rag/graph.py`、`backend/app/rag/generator.py` 沿用独立Loop与单/多汇总，强化原题全部目标覆盖和比较，保留题设/来源区分及引用检查，覆盖FR-007、FR-014。
- [x] T020 [US3] 在 `backend/tests/unit/test_model_loop_budget.py`、`backend/tests/unit/test_v3_3_multi_agent.py` 及 `backend/tests/unit/test_graph.py` 验证5/4/3分支额度、多问汇总预留、原题/共享条件承载；mock不能证明真实条件推理，覆盖FR-014–FR-015、SC-003–SC-004。
- [x] T021 [US3] 保存C工程结果和比较/条件推导真实未评估状态到 `specs/006-query-rewrite-split/phase-c-report.md`，报告后暂停，覆盖FR-017–FR-018、SC-007。

## Phase 6: User Story 4 — 观测与异常（P2，阶段D）

**Independent Test**: 公共契约、显示、调用关联/来源、失败与真实时间可核对，敏感内容不公开。

- [x] T022 [P] [US4] 在 `backend/tests/contract/test_chat_stream_api.py`、`backend/tests/contract/test_chat_request_deadline.py` 覆盖三字段结果映射、澄清、真实来源及300秒/迟到事件，覆盖FR-002、FR-015–FR-016、SC-004–SC-005。
- [x] T023 [US4] 在 `backend/app/rag/pipeline.py`、`backend/app/rag/graph_state.py` 保留版本1事件兼容字段，明确relation来自动作、query_analysis是同一入口预算键，记录模型/缓存/状态来源，覆盖FR-016。
- [x] T024 [US4] 同步 `frontend/src/types/api.ts`、`frontend/src/api/client.ts`、`frontend/src/components/ProcessPanel.tsx`、`frontend/src/api/sse.test.ts` 的契约和“问题补全与拆分”显示，保持完成后回放语义，覆盖FR-016。
- [x] T025 [US4] 在 `backend/tests/security/test_query_rewrite_log_privacy.py` 覆盖日志脱敏，在 `backend/tests/unit/test_request_deadline.py` 验证同一deadline与迟到历史回滚；保留本地诊断范围，不新增调试接口，覆盖FR-010、FR-015–FR-016。

## Phase 7: Polish & Cross-Cutting（仍属阶段D）

- [x] T026 在 `README.md` 和 `docs/CURRENT_STATUS.md` 更新入口/预算事实及006进度，005失败继续明确，覆盖FR-014–FR-018。
- [x] T027 运行 `backend/tests/unit`、`backend/tests/contract`、`backend/tests/integration`、`backend/tests/security` 必要全量回归，保存原始记录于 `output/query-rewrite-v1/engineering/`；临时索引隔离，覆盖FR-015–FR-018、SC-004、SC-007。
- [x] T028 在 `frontend/` 运行npm test -- --run及npm run build，保留输出于 `output/query-rewrite-v1/engineering/`，覆盖FR-016–FR-018、SC-004。
- [x] T029 保存D回归/未测真实质量到 `specs/006-query-rewrite-split/phase-d-report.md`，报告后暂停，不启动E，覆盖FR-017–FR-018、SC-007。

## Phase 8: 有限真实入口验收（阶段E）

最新结果（2026-10-11）：用户要求E遇错继续，完整输入17题已采齐，10通过、7失败、0未运行，见[完整E报告](phase-e-completed-all-20261011-report.md)。T030继续模式26项scripted工程检查通过；本次只采剩余九题，新增3通过、6失败，无重试、无改判，生产prompt不变。T031质量仍未通过，不因采集完成而勾选。下列首次失败即停描述保留原计划，当前E运行例外以[继续规则](phase-e-continue-policy-20261011.md)为准。

- [x] T030 实现仅用于验收的 `backend/scripts/capture_query_rewrite_v1.py`，读取T001夹具、冻结17次调用清单、保留首次输出/调用ID/时间/用量/上下文来源、拒绝覆盖记录及顺序失败停止，不新增模型Judge，覆盖FR-016–FR-017、SC-001–SC-005。
- [ ] T031 在 `output/query-rewrite-v1/<run-id>/` 采集RW01–RW16、RW18本地真实入口首次结果并人工逐项核对，数字/否定/依赖失真即失败并停止；未运行标未运行，覆盖FR-003–FR-006、FR-008–FR-009、FR-017、SC-001–SC-005。
- [x] T032 保存E真实结果、失败/耗时和下一步范围到 `specs/006-query-rewrite-split/phase-e-report.md`，报告后暂停，不自动运行F，覆盖FR-017–FR-018、SC-007。

T031 首批事实：`e-first-20261011-01` 实际执行 RW01–RW03，RW01/RW02 通过，RW03 将文件名后的内部双空格改为单空格而失败；RW04–RW16、RW18 为 `not_run`。遵守顺序失败停止，没有重试。此勾选状态不等于质量验收；失败和原始记录保留，修复/另批次复验须另行明确授权。

T031 续测事实（2026-10-11）：用户明确接受不影响题意的普通空格变化并要求继续E。[验收澄清](phase-e-whitespace-acceptance-20261011.md)及独立审阅补充接受原RW03首答，原失败记录不覆盖、不重跑前三题。T030采集工具新增新目录续测支持，97项fake/scripted工程检查通过。`e-resume-20261011-01` 实际执行RW04–RW07；RW04–RW06通过，RW07面对历史唯一对象PN8733仍询问“它”指哪个设备，未完成代词补全，失败停止。RW08–RW16、RW18共10项未运行。按本轮标准累计6通过、1失败、10未运行；T031保持未勾选，T032新增[E续测报告](phase-e-resume-20261011-report.md)，报告后暂停，本轮不执行F。

后续题集调整（2026-10-11）：用户明确要求把需要补充的测试题写成补充完毕的完整问题。新增 `query_rewrite_v1_completed_cases.json`，题集版本 `query-rewrite-completed-v1-20261011`；仍含17个E案例，RW07/RW08直接写明对象和条件，RW09明确选择PN8733启动电压，RW10合并为MN-42上电检查完整问。其余13个E案例保持不变；旧24组夹具与原工程覆盖不修改。本轮只准备及离线校验数据，不调用模型；新题集17项均未运行。它测完整问题处理，不替代原SC-002代词/省略/澄清能力成绩，原RW07失败不改为通过。后续真实运行须用新题集、新目录，不沿用旧续测summary。

T031新版完整输入首测事实（2026-10-11）：`e-completed-first-20261011-01` 从RW01重新采集，不继承旧成绩。RW01–RW07通过，RW03普通空格变化按用户标准接受；RW08已明确PX-200、245 V、400 ms及如果触发的前提，模型仍输出不清楚、空问题，并让用户说明恢复条件，人工判failed后停止。共7通过、1失败、9未运行，8次本地模型调用、工具/云端/Judge/重试0；入口耗时合计55.657秒。新版RW07通过不证明原代词补全修复，T031保持未勾选；T032新增[新版E首次报告](phase-e-completed-first-20261011-report.md)。生产prompt和采集器未变，报告后暂停，不执行F。

## Phase 9: 真实端到端补测（阶段F）

- [x] T033 实现 `backend/scripts/capture_query_rewrite_e2e.py` 的正常API首次三题采集、隐藏交互凭据、独立新线程、正式库前后指纹及零标准答案注入，按RW24原题顺序且失败停止，覆盖FR-007、FR-015–FR-018、SC-005–SC-007。
- [ ] T034 在 `output/query-rewrite-v1/e2e-<run-id>/` 保存Q16、C-UV及比较题实际原题/模型输出/工具/答复/引用/条件/耗时，入口与完整答案分别验收，未提交剩余题标未运行，旧记录保留，不将本次补测自动勾选005 T018，覆盖FR-006–FR-007、FR-017、SC-003、SC-006。
- [x] T035 保存F真实结果、知识库QA泄漏限制及未评估项；原 `specs/006-query-rewrite-split/phase-f-report.md` 待测报告不覆盖，本次保存到 `specs/006-query-rewrite-split/phase-f-first-20261011-report.md`，仅用户验收后更新006完成状态，报告后暂停；不得启动005 D/30题，覆盖FR-017–FR-018、SC-006–SC-007。

F首轮准备记录：T033的39项HTTP stub/fake工程检查通过，T034三题均为 `not_run`，因为平台密码尚未通过隐藏交互输入；没有聊天API请求、模型或工具调用。T035保存的是待测状态报告，不是F真实验收通过或006完成。已停止等待登录的采集进程，服务保持可用；后续仍限于F，不能跳过原Q16。

F首次真实记录：用户随后提供本机登录输入，经getpass隐藏stdin和正常API认证完成 `e2e-first-20261011-01`。仅Q16提交一次，217.046秒、模型6/工具2/云端0；数值保留且最终保护/恢复核心结论正确，但恢复子问没有共同条件，入口failed，完整答案not_verified（引文issue_found、页码未知）。C-UV/COMPARE未提交；T034不勾选，不自动完成005 T018。首次记录与人工依据保存，未重试，报告后暂停。

## Dependencies & Execution Order

`A(Phase1–3) → 用户验收 → B(Phase4) → 用户验收 → C(Phase5) → 用户验收 → D(Phase6–7) → 用户验收 → E(Phase8) → 用户验收 → F(Phase9)`。

基础任务T003–T007先于故事；US1提供MVP，US2/US3共享同节点并保持独立案例可测；US4覆盖公共输出。T030依赖工程D验收，T033依赖真实E验收与明确F授权。阶段报告任务总在本阶段末执行，不提前写“通过”。

## Parallel Opportunities

- B中T012测试材料可以与T013提示材料并行准备，T014依赖相关约定完成；T015不与另一个同文件任务并行。
- C中T017与T018不同文件可并行准备，但测试运行须等实现完成；T019/T020按依赖顺序。
- D中T022契约测试可与T024前端文件准备并行，执行回归依赖T023/T024完成。
- `[P]`只表示本阶段不同文件可并行，不授权跨阶段或自动派代理；用户故事不会跨阶段并行执行。

## Implementation Strategy

先完成A的协议与完整单问MVP，并交付报告。其后每次仅添加一个获准阶段，验证并停。先工程后真实；真实入口通过也不自动代表端到端答案通过。任何顺序真实失败先保留证据并结束本批次。

## Coverage

18项FR、7项SC均有上文任务ID映射。35项均含明确路径和工程进度复选框。故事任务：US1 4项、US2 5项、US3 5项、US4 4项；基础7项，跨故事/报告/真实验收10项。计划生成、规格检查不勾选实施任务。
