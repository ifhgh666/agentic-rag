# Implementation Plan: 集中提示词与改写函数审阅

**Branch**: `codex/model-driven-agent-loop`（沿用，未切换） | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)
**Status**: 2026-10-13：B工程交付完成，11提示函数全部按需接入，入口独立schema与缓存隔离保持；12项接入检查、15项等价场景及566项后端工程回归通过。20项工程任务完成，真实质量未测，C取消。见[阶段B报告](phase-b-report.md)，报告后暂停，等待用户验收。

**后续变更（2026-10-18）**：用户授权删除模型驱动压缩；随后进一步明确只保留 `base_token_threshold=2000`、`token_growth_factor=0.9` 的动态阈值与 Token 估算。Agent Loop 超出动态窗口时直接返回容量边界，不执行摘要、摘录或压缩；`model_compression.py`、两类压缩提示函数及对应测试已删除。会话历史摘要仍保留。

**A2历史、现已被A3取代**：2026-10-18曾按截图把Agent实现暂时整理到`backend/app/rag_agent/`并保留兼容导出。2026-10-19用户明确要求去掉多余代码后，A3将实现收回现有`backend/app/rag/`，作为当前唯一架构。

**A3交付（2026-10-20）**：单包结构与唯一提示来源已核验。117项定向检查通过；完整后端回归588通过、3失败，详见[A3阶段报告](phase-single-rag-package-20261018-report.md)。报告后暂停，等待用户验收。

## Summary

生产提示与schema目前分别集中在`backend/app/rag/prompts.py`和`backend/app/rag/schemas.py`；提示由纯函数按职责返回，调用模块只传动态数据并取得所需消息。上游结构参考[GiovanniPasq的提示词模块](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/rag_agent/prompts.py)，其目录名只属于参考项目，不是本仓库运行时包。

原A已交付实际模块。用户审阅后要求独立schema绑定，入口提示保留角色、允许操作、澄清边界和保真约束，删除重复输出格式段；三个字段的类型、说明及结构校验放在既有QueryAnalysis。B已接入其他10提示函数，正文与既有行为保持。

规划、取消C和原A的事实报告保留。006已补全题集10通过/7失败保留，本轮不启动真实测试或F。

## Technical Context

| 项目 | 决策 |
|---|---|
| 语言与平台 | 现有Python 3.11+后端、Windows；React前端无改动 |
| 依赖 | 复用现有provider/Pydantic/pytest，不升级或添加依赖 |
| 模块 | `backend/app/rag/` 内按职责分文件；`prompts.py` 为提示唯一来源，无模型、网络、文件或会话副作用 |
| 存储 | 不增加存储；现有缓存增加独立改写提示版本维度 |
| 模型 | 原A/B保持qwen3:4b-instruct；2026-10-13用户另行明确授权补充M，改为上游granite4.1:8b，范围见末节 |
| 输出 | 入口保留三字段query-rewrite-v1协议；摘要、确定性证据压缩、答案JSON与引用格式保持各自原契约 |
| 预算 | 入口最多1次，单次等待≤120秒、整请求≤300秒；其他节点沿用8/12总模型与16工具额度，不增修正次数 |
| 范围 | 8类系统提示及3类固定辅助指令；动态问题/历史/证据与消息角色由原节点构建 |
| 性能目标 | 取提示只是返回字符串，不额外调用模型；不承诺真实质量或时延一定改善 |
| 验证 | 模块静态检查与必要隔离工程回归，真实题集测试不在本计划内；测试目录位于仓库独立output |

## Constitution Check

研究前检查与设计后复核均通过：一次只执行一个获准阶段；提示定义与业务模型/检索职责分开；不弱化证据及引用；不改.env或正式数据；保留指纹和失败，工程与真实结果分别报告。没有新架构、模型下载、云端切换或生产部署。所有技术选择来自已查阅调用链，未知项为零，无需研究代理。

## Project Structure

```text
specs/007-centralize-prompts/
  spec.md
  plan.md
  research.md
  data-model.md
  prompt-review.md          # 当前实际改写函数全文与差异
  contracts/prompt-functions.md
  quickstart.md
  tasks.md
  checklists/requirements.md
  planning-report.md
backend/app/rag/
  edges.py
  graph.py
  graph_state.py
  nodes.py
  prompts.py              # 固定提示与模型消息模板的唯一来源
  schemas.py
  tools.py
  query_analysis.py       # 按函数取入口提示，绑定QueryAnalysis
  conversation_summary.py
  agent_loop.py
  generator.py
  context_compression.py  # Token估算与动态阈值
  query_planner.py
backend/tests/
  unit/
  integration/
  contract/
  security/
```

主图组装、节点和路由分别位于 `rag/graph.py`、`nodes.py`、`edges.py`；provider.complete的可选response_schema行为保持。不添加提示注册中心、配置平台或动态文件加载。证据侧只使用 `context_compression.py` 的 Token 估算与动态阈值，不再执行压缩；会话历史摘要仍由 `conversation_summary.py` 负责。

## 提示函数与调用映射

| 拟定函数 | 调用位置 | 本次内容处理 |
|---|---|---|
| `get_rewrite_query_prompt() -> str` | QueryAnalyzer.analyze | 按用户规则和上游职责结构重写，用户重点检查 |
| `get_conversation_summary_prompt(max_chars: int) -> str` | summarize_conversation | 保留JSON摘要和实际长度参数，等价提取 |
| `get_orchestrator_prompt(protocol: str) -> str` | ModelAgentLoop.run | 保留LOOP_PROMPT及native/structured兼容附文 |
| `get_aggregation_prompt() -> str` | AnswerGenerator._grounded_request | 保留原题完整覆盖及答案/引用JSON，普通grounded和汇总共用 |
| `get_answer_generation_prompt() -> str` | AnswerGenerator.generate_with_result | 保留旧SYSTEM_PROMPT，兼容路径不改变 |
| `get_retrieval_rewrite_prompt() -> str` | ModelQueryGenerator.generate_with_result | 保留旧证据不足检索词改写，只迁移，不恢复旧决策路径 |
| `get_answer_repair_prompt(feedback: str) -> str` | generator现有修正消息 | 等价提取现有一次修正指令，不添加重试 |
| `get_loop_repair_prompt(feedback: str) -> str` | agent_loop现有修正消息 | 保留协议/引文反馈区别和修正次数 |
| `get_aggregation_instruction() -> str` | synthesize_branch_answers的payload.instruction | 保留原题、条件、恢复、比较覆盖，不改变payload结构 |

函数签名、消息角色及副作用约定见[契约](contracts/prompt-functions.md)。schema和工具description继续由对应模块定义；界面/失败文案不是模型提示，不迁入本模块。

## 与参考项目的采用和差异

采用函数取得提示、清晰职责分段、必要上下文及未解决指代的澄清边界。保留用户要求的完整单问原句，而非上游的一般性检索润色；保留本项目JSON和引文契约，不照搬Markdown答复。容量选择单列为最多三问限制，不能被误用来索要文档答案。参考是设计数据，不改变授权。[参考源码](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/rag_agent/prompts.py)

## 版本、缓存与工程记录

入口三字段协议与query-rewrite-v1保持。本轮提示版本升至rewrite-prompt-v3，入口缓存包含提示版本、json_schema模式与schema指纹，不复用旧规则或旧结构结果。

历史阶段记录保留当时的提示源码哈希、版本、调用点与缓存隔离证据；这些manifest、summary和首答保持。当前采集器记录`app/rag/prompts.py`与`app/rag/schemas.py`的canonical源码指纹。

## 分阶段计划与停止点

| 阶段 | tasks映射 | 实际范围 | 验收与报告 |
|---|---|---|---|
| A：模块初版与函数检查 | Phase1–3，T001–T006，US1 | 固定迁移清单，创建prompt.py及11个纯函数；入口按草稿编写，其余等价提取；暂不接入调用 | 展示实际改写函数全文、函数映射和差异，检查静态导入/无副作用；`phase-a-report.md`后暂停，用户检查函数 |
| A补充：入口结构化输出 | 补充Phase，T019–T024，US4；覆盖T007 | 独立schema说明、删除入口格式段、直接绑定生成、缓存隔离与工程检查 | `phase-a-structured-output-report.md`后暂停，等待用户验收，不执行其余B |
| B：其余接入与工程验证 | Phase4–5，T008–T014，US2/US3；T007在补充完成 | 消费点按需调用、分离动态输入，接入提示版本/cache，记录工程源码指纹，保持原协议 | 必要入口/动作/Loop/汇总/预算/隐私检查及后端回归；交付实际函数和工程证据，`phase-b-report.md`后暂停，计划结束 |

用户“先补好这个”授权A补充并完成T007，随后“执行b阶段”授权本轮T008–T014。B已完成工程交付；原C和真实复测仍移除。报告后暂停，等待用户验收，B是本计划最终交付。

## 2026-10-13结构化入口设计

- 复用QueryAnalysis，只补三个字段description；严格类型、extra=forbid、max_length=3及现有联动校验保持，不新增重复schema或语义拦截。
- QueryAnalyzer取得集中业务提示，传response_schema=QueryAnalysis，直接消费ModelResult.structured_output；content仍保存首答原文。
- OllamaProvider显式with_structured_output(schema, method="json_schema", include_raw=True)，保留raw/usage。兼容接口仅在显式选择时发送response_format/json_schema/strict；不支持时按原model_unavailable失败，不降级、重试或换提供方。
- complete_model同一次提供方调用仍有总等待保护；结构化校验失败保留原输出，入口按invalid_model_output处理，错误详情不公开。未传schema的工具/答案/摘要调用保持原路径。
- 输入窗口保守计入schema文本，缓存计入提示版本、模式与schema哈希。动作、原题、历史、续补、公开API/SSE及失败码不改。
- 针对性检查覆盖实际请求绑定、真实LangChain包装器加假传输、两种字段状态、失败、超时和缓存；适配必要入口测试替身，执行共享provider相关后端工程回归，临时目录位于新output，不运行真实模型/检索。
- 只修改四个入口生产文件与必要测试和当前设计文档，A补充当时其他10函数/消费者、.env、数据、采集器及历史证据保持，原基线为1108项文件和17项正式数据；B仅迁移其消费点，正文不变，另有本轮基线。

## 验证与风险

静态/工程验证确认集中来源、实际发送消息、native/structured协议、摘要长度、引用/候选输出格式、缓存版本和既有动作/预算边界，不新增数字/空格语义拦截。使用现有有意义检查，不给每句提示编写字符串镜像测试。本计划不运行真实测试，文件抽取和fake通过不能证明七项旧失败消失。

本计划内真实模型/检索/Judge调用为零。旧E题集、指代补全能力和F端到端状态不改变；若以后要求复测、切模型或开展F，另轮明确范围，不能隐含在B工程检查中。

主要风险是提取时丢失协议附文/动态长度、修改提示但缓存仍旧、错误采用上游的Markdown或宽泛改写权限、当前4B模型仍不遵守规则。按映射、版本、契约和分别报告处理，不承诺只换prompt即可修复。

## 补充M：同款模型配置与准备（2026-10-13）

授权来自用户直接要求模型与GitHub项目一样；本轮只执行此补充，原A/B历史结论和C取消保持。目标是上游project/config.py当前的granite4.1:8b，temperature=0、seed=42。技术栈与依赖保持，修改已有backend/.env的单一OLLAMA_MODEL行、backend/.env.example及README当前安装说明；Settings原有显式模型配置机制保持。

| 阶段 | tasks映射 | 范围 | 验收与停止点 |
|---|---|---|---|
| M：模型配置补充 | T025–T028，US5 | 保存保护基线；首次下载约5.3GB模型；定点更新实际配置及示例；验证项目结构化和原生工具接口 | phase-model-alignment-report.md记录实际命令、首次结果、服务状态及限制；报告后暂停，等待用户验收 |

研究未知项为零：目标由用户要求和上游实际配置确定，使用已运行的本机Ollama API，不新增依赖、切云端或改变索引。接口和数据关系保持，详见[模型契约](contracts/model-selection.md)。窗口4096、输入3072、输出768、单次120秒、整请求300秒及所有调用预算不变。

下载先于配置切换，避免配置指向不存在的模型。验证使用合成问题，无知识库/正式检索；最多两次真实模型调用，分别测试已有QueryAnalysis绑定和原生工具调用，每次遵守120秒总等待、无自动重试。若协议失败，保留首次结果并如实报告，不修改prompt/schema或放宽校验。后端当前不可连接时不为此启动正式服务，直接读取新进程Settings和项目提供方验证，下次正常启动加载新模型。

宪章设计后复核：仅一个获准补充，配置和模型准备职责分离，未扩大证据/引用或数据访问边界。现有.env除目标行外字节保持；旧模型、正式数据、报告和首次失败保护。工程检查与真实协议探测分别报告，不承诺8B解决所有历史质量问题，不恢复17题或F。

补充M交付：目标模型安装和Settings/提供方生效检查通过；88项工程检查通过。首次真实结构化探测失败（清楚状态返回非空澄清“无”），原生工具探测通过；真实协议验收未全部通过。所有首次结果保存，未重试、改prompt/schema或运行题集。原20项提示任务和4项模型补充任务完成仅表示工作已交付，见[模型补充报告](phase-model-alignment-report.md)，报告后暂停，等待用户验收。

## 补充T：当前版本真实入口测试（2026-10-13）

用户“开始测试”授权本节一个测试阶段，T029–T032/US6。沿用已批准的完整输入17题，顺序RW01–RW16、RW18；原四道需要补充的输入不恢复，不用其成绩证明原代词补全质量。当前源码/schema和Granite8B冻结，每题独立线程、首次调用1次，无缓存、工具、检索、云端、Judge或自动重试。

复用capture_query_rewrite_v1：当前硬编码旧4B许可需补已授权granite4.1:8b，其他模型/远程提供方继续拒绝。manifest追加当前prompt版本、schema指纹及prompt.py源码，续测核对同样包含prompt，避免未来混用版本。工具改动先用scripted临时目录检查；产品代码、题集、.env及正式数据保持。

输出位于新 `output/prompt007/entrance-20261013/run`，先保存原始记录，协议失败直接记failed并继续；有效结构由Codex逐题审阅，审阅rubric只在模型完成后读取，不反馈给模型。已有普通空格许可继续，不增加产品语义拦截或修正“无”为空串。使用file gate提交审阅而非要求用户实时输入；这是代理检查，不冒充用户验收。

| 阶段 | 任务 | 验证/停止点 |
|---|---|---|
| T：真实入口17题 | T029–T032 | 采集器隔离检查→最多17次顺序真实入口→逐题分类与当前版本证据→phase-entrance-20261013-report.md；报告后暂停，等待用户验收 |

单题失败/误澄清/结构错误/超时继续，整体预算违规或用户明确中断停止；保留未运行状态和已采首答。模型等待≤120秒，整请求≤300秒，不调高预算或因CPU慢自动换模型。入口测试不需要登录或启动FastAPI/Qdrant，正式平台端到端另轮按用户范围执行。

未知设计项为零，直接复用已有工具和批准题集；不委派代理。宪章复核：仅一个获准阶段，测试工具与产品职责分开，正式数据及旧证据保护，工程与真实首答分别报告。仅采集工具、必要测试、当前设计/导航与新证据可改变。原C不恢复，旧006 T031/T034与005 T018不因本轮采集完成而勾选。

补充T已交付：28项采集器隔离检查通过；17题首答全测，0通过/17失败/0未运行，17次模型调用，工具/检索/云端/Judge/缓存/重试0。全部字段状态联动无效，RW13–RW15同时有语义问题。题目问题部分的14项可接受观察不改整体失败；质量未通过。原始记录和版本冻结均保留，见[入口测试报告](phase-entrance-20261013-report.md)，报告后暂停，等待用户验收；没有自动修复或端到端阶段。

## 2026-10-13 补充R：字段状态生成约束修复

沿用US4，执行一个补充修复阶段R（T033–T036）。使用Pydantic的json_schema_extra回调生成两个完整对象分支anyOf；每个分支复制现有字段/必填/禁止额外字段，分别固定is_clear及问题数量、澄清长度。保留根object及字段元数据以保持调用/审阅接口；不使用可能被语法编译器忽略的if/then，不放宽后置校验，不添加结构字段或格式prompt。schema哈希已进入缓存，因此自动隔离旧结果，预算/期限不变。

先保存基线及回归测试（验证旧schema失败）→修改独立schema→相关测试与完整后端工程回归→两次合成清楚/待澄清首答探测→审计/报告。探测采用当前本机Granite8B、项目QueryAnalyzer、每题最多1次、120秒模型/300秒请求、零工具/检索/云端/重试，不运行17题。

宪章设计后复核通过：单阶段、模块职责分离、无数据或配置变更、工程与真实区别记录。未知项已通过本地绑定代码、官方说明和隔离/真实验证方案解决，无研究代理。保存phase-schema-fix-20261013-report.md后暂停，等待用户验收。

验证依赖：独立生成schema测试采用本机已安装jsonschema，requirements.txt显式登记同一4.x范围；未安装或升级依赖，不把该库用于生产输出修复。

R交付：相关工程133项/后端完整585项通过，真实合成结构2/2有效、预期状态1/2通过（无历史代词误判保留）；旧17题不改判，未开展题集或端到端。见[修复报告](phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充T2：字段联动修复后的真实入口复测

本轮唯一阶段T2，任务T037–T039。现有capture_query_rewrite_v1及旧helper复用，新wrapper只在内存改输出目录与命令记录，旧文件不改；不修改产品/题集/预算。输出output/prompt007/entrance-retest-20261014，manifest沿用采集器历史phase=E，真实授权范围为007 T2。

保存当前基线/模型digest/配置与源码一致性→固定17题首次采集→每题先存raw、再由Codex按既有rubric审阅后继续→审计与phase-entrance-retest-20261014-report.md。审阅文件门禁由编码代理提交，属于代理质量检查、待用户验收，不要求用户实时输入；标准答案不回传模型。失败继续，整体预算违规或用户中断按既有规则停止。

R的585项工程结果与当前生产源码一致已核对，采集器未改，不重复pytest；纯测试包装器不改变模型调用逻辑。普通空格许可不新增运行时语义检测。无新的未知技术决策、不委派代理；宪章设计后复核通过：一个阶段、正式数据保护、模型与代理审阅职责分离、首答与真实质量诚实记录。报告后暂停，等待用户验收。

T2实际交付：14通过、3失败、0待定、0未运行，17/17条首答结构有效，零重试；采集/审阅工作完成不表示质量全通过。模型与产品配置/代码、旧首答/报告及正式数据保持。见[入口复测报告](phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充P：改写业务规则的顺序与通用示例

唯一阶段P/T040–T044：基线与先冻诊断题→更新设计与业务prompt/version→相关隔离工程和所有23输入窗口预检→诊断6首答（D13/D14/D15/N13/N14/N15）→回归原17首答→审计/报告。输出output/prompt007/business-repair-20261014，两批结果分别计分。

复用原采集器；6题诊断的ENTRANCE_ORDER仅在新wrapper进程内限定为已冻结6题，生产采集器文件与原17题不改。每次运行使用实际Settings/Granite digest、新schema保持、prompt一次冻结，先保存raw再由Codex逐题检查（待用户验收），标准答案不回传。诊断业务失败继续完成6题及17题，不在批次间调prompt或重试。整个阶段最多23模型调用；其他预算与失败码不改。

仅入口业务prompt改变，按必要范围执行schema/绑定/缓存/改写/采集器/其他消费点的145项既有工程检查，不添加字符串镜像测试或重复完整后端585项。AST核对其他10函数正文等价；缓存依独立prompt版本隔离。所有输入按真实窗口算法用scripted提供方预检，不能当成真实质量。

未知项为零，无代理委派。宪章设计后复核：一个阶段、职责分离、不增加语义代码拦截/模型重试、正式数据保护、工程与真实质量区别记录。保存phase-business-prompt-20261014-report.md后暂停，等待用户验收；模型对照不在P范围。

P候选修改/验证/记录工作已交付，质量未通过：145项工程通过；真实诊断6题4通过/2失败/0待定/0未运行、原17题回归12通过/5失败/0待定/0未运行，各批独立计分。v4新增误澄清/历史混入退步，已仅撤回本轮候选，当前prompt字节恢复测试前v3；候选全文/原始失败保存，schema修复保持。T041勾选表示候选编写与试验完成，不表示最终采纳。旧失败不改判，见[候选报告](phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充L：轻量英文入口prompt候选

补充L为一个小范围prompt实验，任务T045–T048。先保存v3源码/配置/schema/模型和6题冻结fixture→应用用户提供的英文prompt并升rewrite-prompt-v5→运行结构相关工程检查与窗口预检→6题真实入口首答、失败继续、逐题Codex审阅→审计/报告。输出目录output/prompt007/light-prompt-20261014；旧v3报告和P候选均保留。

每题最多一次、最多6次真实入口调用；模型≤120秒、请求≤300秒、工具/检索/云端/Judge/缓存/自动重试0。标准答案不进入模型输入，先保存raw再审阅；本轮不跑完整17题，避免在小诊断未判定前扩大批次。schema字段联动修复保持。若候选效果不足，报告中说明是否保留候选，不自动用旧成绩替代。

工程测试排除一个只断言旧中文措辞的历史测试，另运行schema/结构化绑定/采集器/提示消费相关检查；不修改该历史测试。未知项为零，不委派代理；报告后暂停等待验收。

## 2026-10-18 补充A2：Agent职责目录整理

本轮唯一阶段为 A2（T049–T053），直接采用用户给出的目录边界：

```text
backend/app/rag_agent/
  __init__.py
  edges.py
  graph.py
  graph_state.py
  nodes.py
  prompts.py
  schemas.py
  tools.py
```

`graph.py` 只装配图并提供 `AgentGraphService`；节点行为移到 `nodes.py`，条件路由移到 `edges.py`。状态、Pydantic 输出结构和只读工具分别由 `graph_state.py`、`schemas.py`、`tools.py` 维护。`prompts.py` 统一保存固定系统提示、修正提示、预算提示、schema 回退提示及动态消息格式函数，入口版本保持 `rewrite-prompt-v6-zh`。

现有检索、generator、provider、conversation memory、cost control 等通用服务继续位于 `app/rag`，它们直接依赖 `rag_agent` 的职责模块。旧 `app/rag/{graph,graph_state,nodes,prompt,model_schema,tools}.py` 只显式 re-export canonical 对象，避免一次性破坏脚本和第三方调用；生产入口不经过这些兼容层。采集器源码指纹改为真实 `rag_agent/prompts.py` 与 `rag_agent/schemas.py`。

验证包括编译/导入、架构唯一来源、提示消费者、图与状态、schema/provider、工具、请求截止及采集器回归，再执行受影响后端回归。使用 fake/scripted provider 和独立 basetemp，不启动或停止服务，不读取/重建正式 Qdrant，不调用真实模型或题集。保存 `phase-rag-agent-architecture-20261018-report.md` 后暂停，等待用户验收。

## 2026-10-18 补充A3：收敛到单一`app/rag`包

用户否决A2的双包与兼容层后，本轮唯一阶段为A3（T054-T058）。canonical职责文件直接位于现有`backend/app/rag/`：

```text
backend/app/rag/
  __init__.py
  edges.py
  graph.py
  graph_state.py
  nodes.py
  prompts.py
  schemas.py
  tools.py
  ...现有检索、模型、生成、会话、预算、索引和pipeline模块
```

先把A2的真实实现落回`rag`并改为包内相对导入，再把生产、脚本和测试统一到复数`prompts`/`schemas`路径，最后删除`rag_agent`、`prompt.py`、`model_schema.py`、无生产调用的节点兼容函数和旧`QueryDecision` schema。`rag/__init__.py`不做eager import，避免图和服务之间形成初始化循环。

采集器的新manifest只记录`app/rag/prompts.py`与`app/rag/schemas.py`；旧报告和原始manifest作为历史证据保留，不增加旧路径兼容代码。验证使用fake/scripted provider、独立basetemp和临时索引，不触碰正式Qdrant，不调用真实模型或正式题集。完成后更新当前导航并保存A3报告，报告后暂停等待用户验收。
