# Tasks: 集中提示词与改写函数审阅

输入：[spec](spec.md)、[plan](plan.md)、[research](research.md)、[data-model](data-model.md)、[函数契约](contracts/prompt-functions.md)、[函数审阅](prompt-review.md)。
状态：2026-10-13：B工程交付完成，11提示函数全部按需接入，入口独立schema与缓存隔离保持；12项接入检查、15项等价场景及566项后端工程回归通过。20项工程任务完成，真实质量未测，C取消。见[阶段B报告](phase-b-report.md)，报告后暂停，等待用户验收。

## Phase 1: Setup（属于阶段A）

- [x] T001 在 `output/prompt007/implementation-<date>/baseline.json` 保存执行时的git状态、生产源码、旧报告/首答、.env及正式数据只读指纹，保护既有修改；不重新使用本轮规划基线冒充实施基线，覆盖FR-011/SC-006。

## Phase 2: Foundational（属于阶段A）

- [x] T002 在 `specs/007-centralize-prompts/contracts/prompt-functions.md` 核对11函数与消费点，冻结摘要max_chars、native/structured附文、两类压缩/修正及汇总instruction，确认无遗漏；记录提示版本与query-rewrite-v1协议分离，覆盖FR-001/FR-006/FR-008/FR-009。

## Phase 3: US1 在一处审阅提示规则（阶段A）

目标：可独立展示模块与函数，暂不改变运行调用；用户能检查实际返回文本。

- [x] T003 [US1] 创建 `backend/app/rag/prompt.py`，按契约提供除入口外的10个纯文本函数；摘要传原长度、Loop按协议返回原附文，其他正文与修正次数行为等价，不导入provider、读取.env或调用模型，覆盖FR-001/FR-006/FR-009。
- [x] T004 [US1] 在 `backend/app/rag/prompt.py` 实现 `get_rewrite_query_prompt() -> str` 和独立REWRITE_PROMPT_VERSION，按 `prompt-review.md` 完整原句、指代澄清、独立拆分≤3、共享条件与容量例外编写；不新增运行时语义校验，覆盖FR-002–FR-005/FR-007。
- [x] T005 [US1] 在 `specs/007-centralize-prompts/prompt-review.md` 对照实际函数全文更新审阅位置与上游差异，静态确认11函数返回非空str、无导入副作用或模型/文件访问；本步不接入任何业务模块，覆盖SC-001/SC-002。
- [x] T006 [US1] 保存 `specs/007-centralize-prompts/phase-a-report.md`，列实际函数链接、返回文本、检查命令、未接入状态及“报告后暂停，等待用户验收”；供用户最后检查函数，不自动进入B，覆盖FR-007/FR-011。

## Phase 4: US2 按规则整理问题（阶段B）

T007已在A补充完成。用户“执行b阶段”授权T008–T014，本轮已完成其他消费点接入及完整工程交付，报告后暂停。

- [x] T007 [US2] 在 `backend/app/rag/query_analysis.py` 改为显式导入并调用get_rewrite_query_prompt，在缓存键加入REWRITE_PROMPT_VERSION；保留原题、动态上下文、三字段结构检查和零入口重试，不改policy协议版本，覆盖FR-002–FR-005/FR-008。
- [x] T008 [P] [US2] 在 `backend/app/rag/conversation_summary.py` 使用get_conversation_summary_prompt(max_chars)，保留原memory.summary_max_chars、摘要JSON与保真检查，覆盖FR-006/FR-009。
- [x] T009 [P] [US2] 在 `backend/app/rag/agent_loop.py` 使用orchestrator/context_compression/loop_repair函数，保留native/structured协议、keep/gaps、工具注册及既有修正次数，不改模型决策/期限，覆盖FR-006/FR-009。
- [x] T010 [P] [US2] 在 `backend/app/rag/generator.py` 使用aggregation/answer_generation/answer_repair/aggregation_instruction函数，保留原始问题与payload、答案和citation JSON、修正次数，覆盖FR-001/FR-006/FR-009。
- [x] T011 [P] [US2] 在 `backend/app/rag/model_compression.py`、`backend/app/rag/query_planner.py` 使用对应证据/检索词提示函数；原excerpts/gaps和兼容路径保持，不重新启用旧图决策，覆盖FR-001/FR-006/FR-009。
- [x] T012 [US2] 在 `backend/tests/unit`、`backend/tests/integration`、`backend/tests/contract`、`backend/tests/security` 复用受影响调用、缓存、动作、工具协议、摘要、汇总、预算/期限/隐私检查，补必要缓存版本与提示来源断言并执行后端工程回归；只用scripted/fake和仓库新临时目录，不进行真实模型/检索，覆盖SC-001/SC-002/SC-004。

## Phase 5: US3 工程可追溯与最终交付（仍属阶段B）

目标已完成：记录实际函数版本、调用映射和工程证据；真实质量保持未验证。

- [x] T013 [US3] 在 `output/prompt007/implementation-<date>/delivery.json` 记录prompt.py源码哈希、REWRITE_PROMPT_VERSION、调用映射和工程命令/退出状态；同步 `README.md`、`docs/CURRENT_STATUS.md` 及本任务清单，只记录实际完成，不修改真实采集器或旧题集/首答，覆盖FR-008/FR-010/SC-005/SC-006。
- [x] T014 [US3] 保存 `specs/007-centralize-prompts/phase-b-report.md`，交付实际函数全文链接、版本/缓存生效证据、工程结果、真实未测状态与旧失败保留；报告后暂停，计划结束，不开展已取消的C或006 F、模型切换及30题，覆盖FR-007/FR-011/SC-005/SC-006。

## 补充Phase: US4 独立结构定义与入口绑定（本轮A补充）

目标：prompt只维护业务规则，schema独立并传入生成请求。隔离验收不代表真实质量。用户“先补好这个”授权本节及原T007，不授权其余B。编号避开历史取消的T015–T018。

- [x] T019 在 `output/prompt007/structured-20261013/baseline.json` 保存本轮代码、未跟踪文件、历史证据及正式数据指纹；按Spec Kit更新007设计与契约，覆盖FR-011/SC-006。
- [x] T020 [US4] 在 `backend/tests/unit/test_query_analysis_structured_output.py` 先定义请求绑定、两种状态、原始返回/用量、失败不降级、截止时间与缓存隔离检查，覆盖FR-012–FR-014/SC-007。
- [x] T021 [US4] 在 `backend/app/rag/model_schema.py` 补字段说明，保留“严格bool、list[str]最多三问、str非null、禁止额外字段”及现有联动校验；在 `backend/app/rag/prompt.py` 删除入口格式段并升提示版本，其余10函数保持，覆盖FR-012/FR-005。
- [x] T022 [US4] 在 `backend/app/rag/model_provider.py` 绑定可选response_schema并保留raw/usage和总等待；在 `backend/app/rag/query_analysis.py` 使用集中提示、直接消费结构化字段、计入schema输入和缓存指纹；适配测试替身，动作和失败码保持，同时完成T007，覆盖FR-013–FR-014/FR-008。
- [x] T023 [US4] 在新output临时目录执行针对性单元及入口/动作/API/隐私/期限/provider后端工程回归，保留每次结果；不调用真实模型、检索或云端，覆盖SC-004/SC-007。
- [x] T024 [US4] 同步 `specs/007-centralize-prompts/prompt-review.md`、导航和任务，保存 `specs/007-centralize-prompts/phase-a-structured-output-report.md` 及指纹核对；说明真实未测、其余B待办及“报告后暂停，等待用户验收”，覆盖FR-007/FR-010–FR-011/SC-006。

A补充历史顺序T019→T020→T021→T022（覆盖T007）→T023→T024，报告后停止；用户随后授权B，T008–T014本轮完成，计划工程任务结束，不恢复C。

## Polish & Cross-Cutting（包含于T013/T014，仍属B）

在最终工程交付中核对导航、函数来源、文件保护和未测说明，不新增真实测试任务。

## Dependencies & Execution Order

T001→T002→T003→T004→T005→T006（A停止）；T007在A补充完成；用户继续B后T008–T011→T012→T013→T014（B停止，计划结束）。US1独立交付函数审阅，US2依赖已检查模块，US3交付工程追溯记录。

T008–T011在共享函数完成后分属不同文件，可并行编辑；这里只说明依赖，不自动要求或授权多代理。US1同一模块顺序处理，US3记录在工程检查完成后生成。

MVP是A：取得实际函数供检查，不因计划修订就开始实施。原T015–T017真实采集已取消；原采集器指纹改造不再实施，原T018文档收尾并入现T013/T014。取消时全部任务未执行，旧规划报告与快照保留；后续A实际完成另有报告，取消不计作完成。T031等历史质量任务不自动勾选。

B最终交付：新增12项消费点绑定检查，15项非入口提示等价场景、完整后端566项回归通过；均为工程模拟，历史真实质量待办不勾选。见[阶段B报告](phase-b-report.md)，报告后暂停，等待用户验收。

## 补充Phase M: US5 使用上游同款本地模型

2026-10-13用户明确授权模型切换；原20项工程任务和C取消保持。独立验收是实际配置/安装一致、项目结构化及原生工具接口完成最小合成调用；不等于历史题集质量通过。

- [x] T025 [US5] 在 `output/prompt007/model-alignment-20261013/baseline.json` 保存现有文件、旧报告和17项正式数据指纹，核对上游config.py；按Spec Kit补充 `specs/007-centralize-prompts/plan.md`、研究、数据边界及模型契约，覆盖FR-015/FR-016。
- [x] T026 [US5] 通过本机Ollama API下载granite4.1:8b并记录 `output/prompt007/model-alignment-20261013/pull-result.json`；只修改 `backend/.env` 的OLLAMA_MODEL行并同步 `backend/.env.example`，保留旧模型、其他配置和代码，覆盖FR-015。
- [x] T027 [US5] 在 `output/prompt007/model-alignment-20261013/` 保存已有provider/schema/缓存针对性工程检查及最多两次首次真实合成协议探测，核对Settings实际模型、安装指纹和服务状态；无正式检索/题集、无自动重试，覆盖SC-008。
- [x] T028 [US5] 更新 `README.md`、`docs/CURRENT_STATUS.md` 和当前任务状态，保存 `specs/007-centralize-prompts/phase-model-alignment-report.md`，记录实际命令/退出码、下载/真实与模拟区别、保护指纹和限制；报告后暂停，等待用户验收，覆盖FR-016。

依赖T025→T026→T027→T028，全部顺序执行；配置和共享模型状态不并行修改，不委派代理。M是本轮唯一补充，完成后无自动下一阶段。

M实际结果：配置交付和88项工程检查通过，真实合成探测1通过/1失败，SC-008未全部通过。T027完成的是检查与首次证据保存，不表示结构化质量通过。24项工作完成，旧质量任务不勾选；见[模型补充报告](phase-model-alignment-report.md)，报告后暂停，等待用户验收。

## 补充Phase T: US6 当前版本真实入口测试

用户2026-10-13“开始测试”授权本阶段；只测完整输入17题，按此前要求遇错继续，不恢复原C或后续端到端。

- [x] T029 [US6] 在 `output/prompt007/entrance-20261013/baseline.json` 保存现有代码/证据/配置和正式数据指纹，核对模型/题集；按Spec Kit补充 `specs/007-centralize-prompts/plan.md`、研究、数据边界与真实测试契约，覆盖FR-017/FR-018。
- [x] T030 [US6] 在 `backend/scripts/capture_query_rewrite_v1.py` 适配已授权Granite8B许可、prompt/schema版本指纹与续测核对；在 `backend/tests/unit/test_query_rewrite_capture.py` 验证新增本地模型和旧prompt续测拒绝，使用新临时目录执行采集器工程检查，覆盖FR-018。
- [x] T031 [US6] 在 `output/prompt007/entrance-20261013/run` 保存完整17题当前版本首次真实入口及逐题审阅，失败继续、每题最多1次；原始输出先保存，标准答案不进入输入，分类结构失败与业务失败，覆盖FR-017/SC-009。
- [x] T032 [US6] 更新 `README.md`、`docs/CURRENT_STATUS.md` 和当前任务状态，保存 `specs/007-centralize-prompts/phase-entrance-20261013-report.md`，记录实际命令/退出码、真实结果/用量/时延、失败与覆盖限制、保护指纹及“报告后暂停，等待用户验收”，覆盖SC-009。

依赖T029→T030→T031→T032，全部顺序执行，无并行模型或代理。以上编号仅属于007，不能与006 T031质量验收混同。

T实际结果：28项采集器工程检查通过，真实首答17题全部失败；覆盖与审阅完成，质量未通过。T031完成记录/审阅工作不表示质量合格，原006 T031/T034和005 T018保持未完成。007累计28项工作交付，见[入口测试报告](phase-entrance-20261013-report.md)，报告后暂停，等待用户验收。

## 2026-10-13 补充R：字段状态生成约束修复

目标：补齐US4生成约束，保留旧证据。工程/真实验收分别记录，一次只执行R。

- [x] T033 [US4] 保存output/prompt007/schema-fix-20261013基线，按Spec Kit补充设计与契约；核对16/16只读规格门禁。
- [x] T034 [US4] 在backend/tests/unit/test_v4_query_schema.py及test_query_analysis_structured_output.py补回归，旧schema应拒绝矛盾结果的测试先失败；修改backend/app/rag/model_schema.py把两种状态约束绑定生成，不改变运行时校验。
- [x] T035 [US4] 在output/prompt007/schema-fix-20261013记录相关及完整后端隔离回归、最多两次真实合成首答和原始用量；旧17题不重测/不改判。
- [x] T036 [US4] 核对源码/数据/旧报告保护，更新README.md/docs/CURRENT_STATUS.md及schema审阅文件，保存specs/007-centralize-prompts/phase-schema-fix-20261013-report.md，说明方法、实际命令/退出码、限制与‘报告后暂停，等待用户验收’。

依赖T033→T034→T035→T036，顺序执行，无并行代理。

R交付：相关工程133项/后端完整585项通过，真实合成结构2/2有效、预期状态1/2通过（无历史代词误判保留）；旧17题不改判，未开展题集或端到端。见[修复报告](phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充T2：字段联动修复后的真实入口复测

目标：检验修复后真实17题；工程采集完成与质量通过分开。

- [x] T037 [US6] 在output/prompt007/entrance-retest-20261014保存基线/模型身份/配置/源码/题集指纹，按Spec Kit更新设计与测试契约；只读门禁16/16保持。
- [x] T038 [US6] 复用capture_query_rewrite_v1，以output/retest_prompt007_entrance_20261014.py采集17题首次输出、逐题审阅并保存；错误继续、零重试，不修改旧报告或标准答案。
- [x] T039 [US6] 核对保护指纹，更新README.md/docs/CURRENT_STATUS.md及本任务状态，保存specs/007-centralize-prompts/phase-entrance-retest-20261014-report.md，包含实际命令/退出码、协议/业务分类、调用/用量/时延与‘报告后暂停，等待用户验收’。

依赖T037→T038→T039，顺序执行，无并行模型或代理。T038记录工作完成不等于质量合格，旧006/005质量任务保持。

T2实际交付：14通过、3失败、0待定、0未运行，17/17条首答结构有效，零重试；采集/审阅工作完成不表示质量全通过。模型与产品配置/代码、旧首答/报告及正式数据保持。见[入口复测报告](phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充P：改写业务规则的顺序与通用示例

- [x] T040 [US2] 在output/prompt007/business-repair-20261014保存当前基线及prompt-before.py，先冻结diagnostic-fixture.json的三原题/三变体，再按Spec Kit补设计/契约；只读门禁16/16保持。
- [x] T041 [US2] 在backend/app/rag/prompt.py调整资料目标/容量/完整原句/共享条件顺序，加入三类通用业务示例并升rewrite-prompt-v4；schema/其他10函数/生产调用与预算保持。
- [x] T042 [US2] 用新output目录执行必要145项已有工程检查及23输入窗口/版本预检，AST确认其他提示正文不变，模拟不能计真实质量。
- [x] T043 [US6] 冻结新prompt，保存diagnostic/run的6次首次及regression/run的17次首次真实入口和Codex逐题依据；两批分开报告，失败继续，禁止途中修规则/重试选优。
- [x] T044 [US6] 核对保护/调用/用量/版本及UTF-8，更新prompt-review.md/README.md/docs/CURRENT_STATUS.md/tasks.md，保存specs/007-centralize-prompts/phase-business-prompt-20261014-report.md，报告后暂停，等待用户验收。

依赖T040→T041→T042→T043→T044，顺序执行，一个P阶段，无并行代理。

P候选修改/验证/记录工作已交付，质量未通过：145项工程通过；真实诊断6题4通过/2失败/0待定/0未运行、原17题回归12通过/5失败/0待定/0未运行，各批独立计分。v4新增误澄清/历史混入退步，已仅撤回本轮候选，当前prompt字节恢复测试前v3；候选全文/原始失败保存，schema修复保持。T041勾选表示候选编写与试验完成，不表示最终采纳。旧失败不改判，见[候选报告](phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充L：轻量英文入口prompt候选

- [ ] T045 [US2] 在output/prompt007/light-prompt-20261014保存当前v3 prompt、模型/config/schema/fixture指纹，按Spec Kit补充轻量prompt实验设计与契约。
- [ ] T046 [US2] 在backend/app/rag/prompt.py采用用户提供的英文轻量prompt，升REWRITE_PROMPT_VERSION为rewrite-prompt-v5；schema/provider、其他10函数和预算保持。
- [ ] T047 [US6] 执行结构相关工程检查与窗口预检，随后对D13/D14/D15/N13/N14/N15各做一次真实入口调用，先存首答、再逐题Codex检查，错误继续、零重试。
- [ ] T048 [US6] 审计版本/调用/数据保护，更新prompt-review.md、README.md、docs/CURRENT_STATUS.md和本任务状态，保存phase-light-prompt-20261014-report.md，报告后暂停。

依赖T045→T046→T047→T048，单阶段、无并行代理。

## 2026-10-18 补充A2：Agent职责目录与提示唯一来源

- [x] T049 [US1] 按用户给出的八文件结构补充007规格、计划、契约和任务，核对16/16只读规格门禁；明确本轮不推进009、不调用真实模型或正式数据。
- [x] T050 [US1] 将真实图、状态、节点、边、schema和工具整理到`backend/app/rag_agent/`；生产入口直接使用新图，原`app/rag`同名文件改为显式兼容导出，保持对象身份和行为。
- [x] T051 [US1] 以`rag_agent/prompts.py`为唯一生产提示与模型消息模板来源，保持`rewrite-prompt-v6-zh`；迁移生产消费者、schema回退与预算提示，并让采集器冻结新prompt/schema源码。
- [x] T052 [US3] 增加架构守护测试并执行编译、导入、图/状态、提示、schema/provider、工具、截止时间、采集器及受影响后端回归；使用独立basetemp，记录真实/模拟边界。
- [x] T053 [US3] 更新README、仓库导航、CURRENT_STATUS、prompt审阅与契约，保存`phase-rag-agent-architecture-20261018-report.md`；报告后暂停，等待用户验收。

依赖T049→T050→T051→T052→T053，属于一个已授权架构阶段。T045–T048是旧候选阶段记录，本轮不恢复或改写其历史状态。

## 2026-10-18 补充A3：单一RAG包收敛

- [x] T054 [US1] 按用户最新授权补充007规格、计划、任务与架构契约，确认16/16只读清单通过；范围只含单包收敛、冗余兼容代码删除、工程验证和文档。
- [x] T055 [US1] 将Agent图、状态、节点、边、prompt、schema和工具的canonical实现迁入`backend/app/rag/`，保持`rewrite-prompt-v6-zh`和无副作用`rag/__init__.py`，删除无生产调用的节点兼容函数及旧`QueryDecision` schema。
- [x] T056 [US1] 将`backend/app`、`backend/scripts`和`backend/tests`全部导入及采集指纹迁到`app.rag`复数模块，删除`backend/app/rag_agent/`、`backend/app/rag/prompt.py`和`backend/app/rag/model_schema.py`，不保留转发层。
- [x] T057 [US3] 更新架构守护测试并执行无旧路径扫描、编译、导入、graph/state/prompt/schema/tools/deadline/capture定向检查及完整后端隔离回归；不运行真实模型、正式检索或题集。
- [x] T058 [US3] 更新README、仓库导航、CURRENT_STATUS、007设计/契约/审阅/quickstart和任务状态，保存`specs/007-centralize-prompts/phase-single-rag-package-20261018-report.md`；报告后暂停等待用户验收。

依赖T054→T055→T056→T057→T058，属于一个已授权收敛阶段。A2报告保留为历史过程，不改写当时验证结果；T045–T048仍是旧候选记录，不恢复执行。

A3结果：无旧模块导入引用，编译/导入检查通过；定向回归117 passed。完整后端回归588 passed、3 failed：两项历史v4提示措辞断言保持失败；截止时间测试在完整套件运行时超时，单独复跑1 passed。详见[A3报告](phase-single-rag-package-20261018-report.md)，报告后暂停，等待用户验收。
