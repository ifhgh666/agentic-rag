# Agentic RAG 当前交接状态

2026-11-14 / 019 A。新增 `python start.py`，本地工作台使用固定演示账号 `admin / 123456`，快速开始默认配置 OpenAI 兼容接口。13 项隔离定向测试和独立启动联调通过，现有服务尚未切换。见[阶段 A 报告](../specs/019-simple-startup/phase-a-report.md)。

2026-11-14 / 018 A 身份修正。直接回答提示补充「文脉」知识助手身份，身份与模型问句走直接回答。32 项隔离定向测试通过。随后已应用户要求重启后端，前端代理、后端健康检查及索引就绪通过。真实模型的身份回答仍待验收。见[修正记录](../specs/018-tool-routing/phase-a-identity-20261114-report.md)。

2026-11-14 / 018 A。聊天入口先由模型判断是否需要知识库，再直接回答或改写并按需澄清。后端定向 49 项通过，完整隔离回归 729 项通过、2 项既有断言失败；前端 89 项测试及构建通过。报告后应用户要求重启后端，健康检查与索引就绪通过。见[阶段 A 报告](../specs/018-tool-routing/phase-a-report.md)。

2026-11-02 / 017 E：真实浏览器、隔离后端、当前deepseek-flash及真实ONNX/BM25联调通过；登录/上传到就绪、跨页两轮、来源、删除/退出均验证。两题首答均正确（72小时/45天），8次模型、2次搜索，provider Token6479。正式数据与配置未操作；临时账号与自有实例结束。见[报告](../specs/017-frontend-nova-workspace/phase-e-report.md)与[原答对照](../specs/017-frontend-nova-workspace/phase-e-answer-comparison-20261102.md)。报告后暂停，等待用户验收。

2026-11-02 / 017 D：三页最终收尾完成，移除无消费旧样式；88项前端测试、31项受控浏览器检查、构建/依赖审计通过。CSS由77.98降至51.86kB，六组页面计算样式保持。A–D工程任务已交付，真实后端/模型未联调；见[阶段报告](../specs/017-frontend-nova-workspace/phase-d-report.md)。报告后暂停，等待用户验收。

2026-10-29 / 017 C：知识库Nova改版完成，支持单PDF选择/拖入、名称与状态交集、真实响应状态轮询和统一删除确认。88项前端测试、22项受控浏览器检查、构建/依赖审计通过；真实后端与正式文档未操作，D未执行。见[阶段报告](../specs/017-frontend-nova-workspace/phase-c-report.md)。报告后暂停，等待用户验收。

2026-10-29 / 017 B：连续对话、Enter发送/Shift换行/输入法保护、底部输入、轮内折叠过程与Markdown来源已实现；前端日志页及入口移除，后台保留。78项测试、23项受控浏览器场景、构建/依赖审计与108项保护核对通过；真实后端/模型未联调，C/D未执行。见[阶段报告](../specs/017-frontend-nova-workspace/phase-b-report.md)。报告后暂停，等待用户验收。

---

## 历史交接记录

2026-10-29 / 017 A：用户要求先写完整计划再执行；当前功能指针为017-frontend-nova-workspace，实际Git分支保持。已落盘规格/计划/29任务及四张确认图，并完成A/T001–T015：居中登录、Nova基础、导航/移动Sheet、健康状态与依赖约束。最终56项前端测试、22项受控浏览器检查、构建、check:deps及实际npm ls通过；200保护文件、12项原前端业务及SSE正文保持。问答B、文档/日志C、全站矩阵D未执行。见[A报告](../specs/017-frontend-nova-workspace/phase-a-report.md)、[任务](../specs/017-frontend-nova-workspace/tasks.md)。报告后暂停，等待用户验收。

下列016及更早日期记录保留各自历史事实；017不改判模型质量结果。

2026-10-28 / 016 E 全量测试完成：依用户新指示失败继续，gold-1.0 全15场景/19轮均采集首次输出，0未运行、无重试。完整答复审阅11通过/4部分正确未通过；独立事实题36/36要点全覆盖，但Q3/Q15附加断言错误、Q14数值推理错误，Q9末答缺完整上电流程且误述自检依据。4个交互场景8轮行为均符合，Q13无答案处理符合。模型79次、真实搜索20次、压缩16次，provider Token115247，采集批次348.010秒；346项运行保护无差异，产品/正式数据未改，旧D失败保留。见[全部原答与正确答案对照](../specs/016-reference-agent-semantics/phase-e-answer-comparison-20261028.md)和[E报告](../specs/016-reference-agent-semantics/phase-e-full-gold-20261028-report.md)。T030–T032交付不等于全通过，报告后暂停，等待用户验收。

2026-10-28 / 016 D 真实 PDF/ONNX 首批未通过：用户“开始真实测试”后，沿用当前 deepseek-flash、gold-1.0 Q1–Q4 和正式测试 PDF 索引隔离副本。原 BM25 临时缓存缺失的准备失败保留，补齐历史 hash 一致的官方词表后真实预检通过。Q1 链路 completed，但遗漏已召回的“合格的万用表”，0通过/1失败/3未运行，无重试；模型 5 次、真实搜索 2 次、压缩 1 次、聚合 1 次，14.547 秒，provider Token 9527。运行结束时 423 项保护无差异，产品/配置/正式数据未改；收尾只新增失败记录。见 [D 报告](../specs/016-reference-agent-semantics/phase-d-real-pdf-20261028-report.md)、[当前失败](../specs/016-reference-agent-semantics/CURRENT_FAILURES.md)。T027–T029 交付表示按失败停止协议完成本批，不代表四题全测或质量通过。报告后暂停，等待用户验收，不自动修复或运行剩余题目。

2026-10-28 / 016 C 收尾：已修复框架审阅 F1/F2，移除 main 的闲置 ContextBuilder 装配，更新仓库架构指南为当前原生模型/checkpoint/参考图并单列 legacy。静态 AST 确认产品只删除该导入名与一条赋值，其他 68 项保护文件未变，指南 6 个相对链接有效。没有运行测试、模型或服务。T024–T026 交付，原 A/B/R 和审阅报告保持，见 [C 报告](../specs/016-reference-agent-semantics/phase-framework-cleanup-20261028-report.md)。报告后暂停，等待用户验收。

2026-10-27 / 016 B 续测完成：用户“继续计划”后，remaining-20261027-01 的 B02–B05 真实首答 4 passed/0 failed/0 pending/0 not_run。B02 保留待办且不检索；B03 auto 恢复原题并清空 pending；B04 实际 compress_context 模型调用 2 次，五步顺序/A7-C9 正确；B05 三个自包含分支研究后正确聚合 72 小时/45 天/8 GB。模型 21 次、工具 7 次，provider Token 40367，317 项指纹无差异。已校验 R B01 的相同源码/模型/索引证据，首题未重跑；T017 现勾选，T001–T023 交付完成待用户验收。原 B01 首次失败和历史记录保持；英文澄清、Parent 未调用及正式 PDF/ONNX/浏览器未测明确保留。见 [续测报告](../specs/016-reference-agent-semantics/phase-b-resume-20261027-report.md)。报告后暂停，等待用户验收，不自动新增阶段或正式评测。

2026-10-27 / 016 R 修复：用户继续授权后，产品工厂对精确 `deepseek-flash` 正常参考图默认 `thinking.type=disabled`；覆盖入口/研究/摘要/聚合，其他模型/Ollama/legacy 保持。51 项隔离定向检查通过；无诊断 override 的真实 B01 completed，4 次模型、1 次搜索，72 小时与实际来源正确，请求 `29fdc3e5-6942-4a76-94e2-e9a4b876d8a6`，采集 4.350 秒。307 项原保护文件未变，唯一产品变化为 factory，真实复验期间 314 项无差异。代码对新建实例生效，未重启服务。R=T019–T023 交付；T017 仍部分完成，原 B 失败/未测四题及历史失败保持。见 [R 报告](../specs/016-reference-agent-semantics/phase-r-report.md)。报告后暂停，等待用户验收。

2026-10-27 / 016 真实诊断：用户要求“直接用真实模型呀”后，原入口复现 HTTP 400，服务明确返回 `Thinking mode does not support this tool_choice`。同模型的诊断请求关闭思考后，入口及完整 B01 成功；原图模型 4 次、真实搜索 1 次、2.763 秒，回答 72 小时并附实际来源。本轮共 6 次真实模型调用尝试，三次运行各 308 项保护指纹无差异。产品源码和 `.env` 未改，尚未实施正式修复；原 B 失败不改判，B02–B05 未测，T017 仍部分完成。见[诊断报告](../specs/016-reference-agent-semantics/phase-b-diagnosis-20261027-report.md)。报告后暂停，等待用户验收。

2026-10-27 / 016 B：用户在 A 总报告后明确继续；本轮真实首题失败后按规则停止，**0 通过 / 1 失败 / 0 待定 / 4 未运行**。当前实际 provider/model 为 `openai_compatible / deepseek-flash`，温度 0、种子 42；原入口函数调用链记录 `OpenAIInvalidRequestError`，0.448 秒，没有 analysis、检索或答案。请求 `5d626400-28f1-45ef-9f0a-264cd3f8ea38`，观测模型尝试/云路径计数各 1、工具 0；远端实际受理、Token 与计费不可得，失败路径 Token=0 是估算占位。T017 部分完成仍未勾选，T018 失败报告交付；未修产品、未重试或进入正式题库。见 [B 报告](../specs/016-reference-agent-semantics/phase-b-report.md)、[协议](../specs/016-reference-agent-semantics/phase-b-protocol.md)与[016 失败清单](../specs/016-reference-agent-semantics/CURRENT_FAILURES.md)。308 项指纹无差异，报告后暂停，等待用户验收。

2026-10-27 / 016 A：参考执行语义与工程收尾完成，待用户验收。当前功能指针为 `specs/016-reference-agent-semantics`；A=T001–T016 工程完成，B=T017–T018 未执行。正常主图采用 checkpoint、默认续答、模型研究压缩、完整 Parent 和统一聚合；用量仅统计，在线核验卡与旧总额度/截止/准入退出正常路径，独立 legacy 能力保留。收尾修复重复原题补充导致 pending 清理不完整、ASGI 断开遗留 queue.get 消费线程两处问题。

本轮完整隔离回归 **720 passed / 2 failed / 24 skipped / 2 deselected**，退出 1，仅两项既有 legacy prompt 措辞断言失败；前端 **40 passed**、构建退出 0。最初新增六项回归红测失败后修复，相关 29 项通过，含节点访问的参考对照 8 项通过。86 项边界指纹、原 12 项代码/配置保护和 132 份旧证据保持；正式数据仅只读核对指纹，不用于测试。真实模型/云端/Judge、服务重启、提交推送均未执行。详见 [016 A 总报告](../specs/016-reference-agent-semantics/phase-a-report.md)与[任务](../specs/016-reference-agent-semantics/tasks.md)。报告后暂停，等待用户验收，不自动进入 B。

以下为 2026-10-22 及此前的历史交接记录；其中“当前”描述属于对应日期，不能覆盖上述 016 状态。

2026-10-22 / 015 A：Agent 核心职责迁移完成，待用户验收。`rag/` 保留八个实际核心文件，`core/` 承担模型/调用治理/分析/答案/会话/交付和独立旧接口，`knowledge/` 承担编码/索引/检索。tools 1840→285、nodes 1376→548；不是总量减码。完整隔离回归迁移前 817 通过/2 失败，迁移后 820 通过/相同2失败；均有24正式PDF跳过与2真实Dense排除。96定向、6保护证明与71模块导入检查通过，161定义AST等价，无新增产品失败。当前指针为015，A 20项工程完成，B 5项未执行；原真实质量失败保留。见[阶段 A 报告](../specs/015-rag-responsibility-clarity/phase-a-report.md)及[任务](../specs/015-rag-responsibility-clarity/tasks.md)，报告后暂停，等待用户验收。以下日期化记录保留历史事实。

2026-10-20 Agent 单包收敛：当前工作区只有`backend/app/rag/`实现，生产代码、采集器和测试不再依赖第二个包或旧兼容路径；唯一提示来源为`rag/prompts.py`，版本`rewrite-prompt-v6-zh`。117项定向检查通过；完整后端回归588通过、3失败，含两项既有v4提示措辞断言和一项单独复跑通过的截止时间测试。详见[单包收敛报告](../specs/007-centralize-prompts/phase-single-rag-package-20261018-report.md)，报告后暂停等待用户验收。

2026-10-18云兼容端点连续真实验证（009）：用户重新登录后以 `PX-200 的过流保护阈值是多少？` 独立提交3次，HTTP 200 为3/3；入口结构化回退3/3记录 `json_object + structured_fallback=true`。三次均在答案生成前以 `context_budget_exceeded` 结束（11.1 s / 2.9 s / 1.8 s），答案与来源均为0；`cloud_calls == model_calls`（2/2、3/3、2/2），未触发300秒/120秒上限。真实证据见[连续验证报告](../specs/009-cloud-provider-compat/phase-real-rerun-20261018-report.md)，报告后暂停，等待用户验收。

2026-10-18 A2历史架构整理：当时先将Agent职责放入独立目录并保留旧路径兼容。该中间结构已由2026-10-19单包收敛阶段替代；A2报告仍作为当时实现与验证的历史记录，不代表当前路径。

2026-10-18阈值保留：用户进一步要求只保留 `base_token_threshold=2000`、`token_growth_factor=0.9` 的动态阈值与 Token 估算。Agent Loop 不再执行任何证据摘要、摘录或压缩，超出动态窗口直接返回 `context_budget_exceeded`；详见[阈值保留阶段报告](../specs/007-centralize-prompts/phase-threshold-only-20261018-report.md)，报告后暂停，等待用户验收。

2026-10-15云端兼容路径修复并真实复跑（009）：新建 [`specs/009-cloud-provider-compat`](../specs/009-cloud-provider-compat/plan.md)（spec / plan / research / data-model / contracts / quickstart / tasks / checklist），功能指针已切到该目录。修复两处根因——环境 `brotli` 与 `httpx2` 绑定不兼容（产品侧改为不使用压缩编码）、端点不支持严格 JSON Schema（回退到通用 JSON 模式并注入 schema 文本，仅重试一次）。后端全量 **591 passed / 2 failed**，两处失败均为 007 改写提示词后的既有措辞断言。真实入口两次运行：第 1 次 `completed / model_answered`，16.8 秒，240 字回答与 1 条来源，`citation_status=issue_found`、数值与完整性未评估；第 2 次同一问题 `failed / budget_exceeded`。结论：**云端路径可用，真实问答稳定性与答案质量未通过**。见[阶段A报告](../specs/009-cloud-provider-compat/phase-a-report.md)，报告后暂停，等待用户验收。

2026-10-15唯一对象代词代码兜底已实现并复测：模型对RW07原始仍误澄清，代码识别历史唯一PN8733并改写为完整问题，真实入口**1通过/0失败/0待定/0未运行**；新增多对象保守性测试通过。见[唯一对象兜底报告](../specs/007-centralize-prompts/phase-reference-fallback-20261015-report.md)，报告后暂停，等待用户验收。

2026-10-15唯一对象代词RW07复测：历史包含PN8733、当前问“它的恢复条件是什么？”，`rewrite-prompt-v6-zh` 真实入口首答仍误澄清，**0通过/1失败/0待定/0未运行**。无工具、检索、云端、Judge或重试。见[RW07代词复测报告](../specs/007-centralize-prompts/phase-pronoun-rw07-20261015-report.md)，报告后暂停，等待用户验收。

2026-10-14中文轻量入口prompt三题复测：当前工作区使用 `rewrite-prompt-v6-zh`；D13/D14/D15 三次真实入口调用结构有效但语义均失败，**0通过/3失败/0待定/0未运行**。D14已输出中文，D13共享条件和D15容量澄清仍失败；无工具、检索、云端、Judge、缓存或重试。见[中文prompt复测报告](../specs/007-centralize-prompts/phase-chinese-prompt-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-14轻量英文prompt三题复测：当前工作区暂用用户提供的 `rewrite-prompt-v5` 候选；D13/RW13、D14/RW14、D15/RW15 三次真实入口调用均结构有效但语义失败，**0通过、3失败、0待定、0未运行**。没有重试、工具、检索、云端或Judge调用；v5尚未接受为稳定版本，也未自动回滚。见[三题复测报告](../specs/007-centralize-prompts/phase-light-prompt-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-14 P业务prompt候选未通过质量验收：v4的145项相关工程检查通过；真实诊断6题4通过/2失败/0待定/0未运行，原17题回归12通过/5失败/0待定/0未运行。两批分别保存首答，错误继续、零重试；新增完整问误澄清/历史混入退步，已仅撤回本轮候选，当前prompt恢复测试前v3；schema修复与其他配置保持。候选/首答和旧成绩均保留。见[业务提示候选报告](../specs/007-centralize-prompts/phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-14：字段联动修复后的真实入口17题复测T2已完成，**14通过、3失败、0待定、0未运行**；17/17条首答结构有效。每题首答1次、失败继续，未重试。模型/prompt/schema/配置/题集冻结，旧失败记录保持。这是Codex逐题审阅，待用户验收；完整输入题集不证明原代词/省略补全或端到端质量。见[入口复测报告](../specs/007-centralize-prompts/phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-13用户授权字段联动生成约束修复R：独立schema已增加清楚/待澄清两个完整anyOf分支，不改prompt或清空‘无／否’。133项相关工程检查与585项完整后端回归通过；两次真实合成首答结构2/2有效、预期状态1/2通过（无历史代词仍误判清楚）。原17题0通过/17失败记录保留，未重跑题集或端到端。见[字段联动修复报告](../specs/007-centralize-prompts/phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

> 以下为 2026-10-19 及此前的交接快照。当前功能和验收状态见本文顶部。

### 当时的功能与进度

- 最新测试为007补充T：用户“开始测试”授权当前版本入口17题，完整输入题集不改、遇错继续。17次真实模型首答全部保存，**0通过/17失败/0未运行**；无工具、检索、云端、Judge、缓存或重试。全部invalid_model_output来自清楚状态的澄清字段非空（无10题、否6题、记录保留期限1题），其中RW13/RW14/RW15另有共同条件/比较/容量问题。14题问题部分可接受仅是观察，不算整题通过。28项采集器隔离检查通过，只有工具许可和版本记录适配，产品prompt/schema/.env及正式数据保持。最新[入口测试报告](../specs/007-centralize-prompts/phase-entrance-20261013-report.md)后暂停，等待用户验收，不进入端到端。

- 最新资源操作：用户明确允许删除之前的模型，已通过本机Ollama删除 `qwen3:4b-instruct`；安装清单仅有 `granite4.1:8b`，新模型digest和当前配置保持。旧报告与失败证据不覆盖，本轮模型推理/工具执行/测试均0。见[旧模型清理记录](../specs/007-centralize-prompts/model-removal-20261013-report.md)，记录后暂停。

- 最新授权补充为007模型配置M：用户要求与GitHub项目同款，已下载 `granite4.1:8b`（5347933017字节，Q4_K_M，本机参数标识8.8B），并只更新实际.env和示例的OLLAMA_MODEL行，其他配置字节保持。88项针对性工程检查通过；两次首次真实合成探测为1通过/1失败：原生工具请求正确，结构化输出虽保留原题，但is_clear=true同时clarification_needed="无"，现有联动校验拒绝。没有重试或修改prompt/schema，旧质量状态保持。8000健康检查仍ConnectError，未启动/重启后端；下次正常启动使用新模型。最新[模型补充报告](../specs/007-centralize-prompts/phase-model-alignment-report.md)后暂停，等待用户验收。

- 当前功能：[007-centralize-prompts](../specs/007-centralize-prompts/plan.md)。用户“执行b阶段”授权B，现T008–T014完成，20项工程任务全部完成。原11个prompt函数的历史接入记录保留；当前固定prompt函数为9个，证据侧仅保留动态 Token 阈值，入口独立QueryAnalysis绑定及rewrite-prompt-v3/json_schema/schema哈希缓存隔离保持。12项消费点检查、15项等价场景及566项后端回归通过（scripted/fake/假传输/确定性嵌入），真实模型/检索/云端/Judge0。最新[阶段B报告](../specs/007-centralize-prompts/phase-b-report.md)、[阈值保留报告](../specs/007-centralize-prompts/phase-threshold-only-20261018-report.md)和[实际审阅](../specs/007-centralize-prompts/prompt-review.md)交付后暂停，等待用户验收；C取消，原A及补充报告不覆盖，未启动/重启服务。

- 最新交付：[完整E报告](../specs/006-query-rewrite-split/phase-e-completed-all-20261011-report.md)。用户明确要求E遇错继续，完整输入17题首答已采齐，**10通过、7失败、0未运行**。失败为RW08、RW11–RW16；原前八题保留，只新增九题，未重试。26项采集器scripted工程检查通过，生产prompt和配置未改；质量验收未通过，T031仍未完成。本轮未进入F。

- 最近实施功能：[`006-query-rewrite-split`](../specs/006-query-rewrite-split/plan.md)，以下为已有实施与失败事实；007规划不改变这些结果。
- A–C（T001–T021）工程工作已完成，报告分别保存在当前功能目录。C 最终记录为 **115 passed**，使用 fake/scripted provider、确定性嵌入和临时索引。
- 用户已确认 C 完成，并在 2026-10-11 授权 D；D 报告交付后又明确要求继续下一阶段 **E（T030–T032）**。D 工程工作已完成：[阶段报告](../specs/006-query-rewrite-split/phase-d-report.md)保留。
- D 范围：公共 API/SSE 来源与关联、动作适配说明、日志隐私、同一截止时间与迟到输出隔离、前端显示、必要全量后端回归和前端测试/构建。
- D 最终结果：后端 **494 passed**；前端 **8 个测试文件、26 tests passed**；`npm run build` 退出 0。中间失败保留于 `output/query-rewrite-v1/engineering/phase-d-20261011/`；结果均为工程检查。
- E首批历史：RW01/RW02通过、RW03因普通双空格合为单空格被判失败，14项未运行，工程检查87 passed；[原E报告](../specs/006-query-rewrite-split/phase-e-report.md)和 `e-first-20261011-01` 证据保留。
- 用户随后明确接受不影响题意的普通空格变化并授权“继续执行阶段e”。[验收澄清](../specs/006-query-rewrite-split/phase-e-whitespace-acceptance-20261011.md)及独立审阅补充接受原RW03首答；不重跑前三题，不修改入口prompt。
- 本轮T030采集工具增加新目录续测支持，针对性fake/scripted工程检查 **97 passed**。`e-resume-20261011-01` 从RW04开始，RW04–RW06通过，RW07失败后停止；新增模型4次、工具/云端/Judge/重试0，入口耗时合计38.979秒。按本轮标准累计 **6通过、1失败、10未运行**，T031仍未完成。
- 原E续测实质失败：历史中只有PN8733一个对象，问“它的恢复条件是什么？”时模型仍询问“它”指哪个设备，未完成代词补全。已核对历史确实进入模型输入，见[E续测报告](../specs/006-query-rewrite-split/phase-e-resume-20261011-report.md)。
- 用户随后要求把需要补充的测试输入全部写成完整问题。已另存[E已补全17题](../backend/tests/fixtures/query_rewrite_v1_completed_cases.json)，四道RW07–RW10改为完整输入，其余13题不变；准备时17题全部未运行。[题集调整报告](../specs/006-query-rewrite-split/phase-e-completed-fixture-20261011-report.md)只记录离线数据校验。原补全失败、旧题集和工程覆盖保留；新版不能证明代词/省略补全能力通过。
- 用户随后明确指示“执行”，新版以 `e-completed-first-20261011-01` 从RW01独立首测，**7通过、1失败、9未运行**。RW07完整输入通过；RW08虽已明确PX-200、245 V、400 ms和如果触发的前提，仍被模型误判不清楚并反问所求恢复条件。8次本地模型调用、工具/云端/Judge/重试0，入口耗时合计55.657秒；在RW08人工判失败后停止。最新交付为[新版E首次报告](../specs/006-query-rewrite-split/phase-e-completed-first-20261011-report.md)。生产prompt、采集器及冻结题集未修改，T031仍未完成，不执行F。
- 用户在 E 失败报告后再次要求“继续下一个阶段”，本轮仅授权 F；这项继续指令不改变 E 的失败结论或 T031 的未完成状态。
- F 的采集工具 T033 已完成；HTTP stub/fake 隔离检查 **39 passed**。本地后端 PID52988/8000、前端 PID57652/5173 已启动，健康检查 `index_ready=true`，正式库和配置指纹不变。
- 用户随后提供本机登录输入，使用正常认证和隐藏 stdin 完成 F 首批 `e2e-first-20261011-01`。Q16 实际耗时 **217.046 秒**、模型 6 次、工具 2 次、云端 0；入口将恢复子问拆为“之后如何恢复？”，没有共同条件，验收 **failed**。核心数值比较、过压与恢复结论人工核对正确；完整答案为 **not_verified**，引用卡为 `issue_found`、页码未知。
- F顺序失败后停止，**C-UV、比较题均未运行**，没有重试或后台续测。T034未完成；[F首次真实报告](../specs/006-query-rewrite-split/phase-f-first-20261011-report.md)、原[F待测报告](../specs/006-query-rewrite-split/phase-f-report.md)和历史证据均保留，本轮没有新的F请求。
- E完整单问在本轮标准下6/6可接受，但RW07补全失败；RW08–RW16、RW18共10项未测，F欠压与比较仍未验证。Q16单次核心结论正确不代表全部真实质量通过。

### 当时核对的配置边界

2026-10-13非敏感本地配置核对：Ollama `granite4.1:8b`，温度0、种子42。原单/多分支总模型预算 **8/12**、入口 **1**、工具总量 **16**保持；整请求 **300 秒**，单次模型等待最多 **120 秒**且不超过请求剩余时间。窗口4096、输入3072、输出768、安全余量256；缓存300秒/256条。代码仍要求显式模型配置；旧qwen3:4b-instruct已按后续用户指令删除，其历史结果保留。

进度事件不会重置整请求期限；SSE 为执行完成后的轨迹回放。工程期限测试使用缩短等待的模拟，不是 300 秒真实模型到期实测。

### 005 尚未关闭的历史事项

- 005 C 的真实场景验收仍未通过，`T018` 未完成，005 D 未启动。
- Q16 原题 `245 V / 400 ms` 在 2026-10-09 复验时仍被改成 `40或 ms`，耗时 **32.644 秒**；没有检索或正常答案。
- 006 F 于 2026-10-11 原题首次补测已保留这两个数字，并产生正确核心结论；但恢复子问未带共同条件、完整引用验收未通过，005 T018 仍不勾选，旧数字失真证据不覆盖。
- C-UV 原题曾耗时 **1962.902 秒**并以 timeout 结束。超时工程保护已修复，但顺序第一题失败后未提交该题复验；不能把 300 秒配置或 mock 测试视为真实到期与回答质量通过。
- 006 的新协议和工程完成不会自动勾选 005 T018，也不自动恢复 005 或 30 题正式评测。

原始事实见 [`CURRENT_FAILURES.md`](../CURRENT_FAILURES.md)、[005 C 复验报告](../specs/005-model-driven-agent-loop/phase-c-recheck-20261009-report.md)及[超时补充报告](../specs/005-model-driven-agent-loop/timeout-300s-report.md)。历史报告和失败证据保留。

### 当时的接手入口与停止点

1. 读取根AGENTS、README及007规格、计划、任务和最新[入口测试报告](../specs/007-centralize-prompts/phase-entrance-20261013-report.md)。原A、结构化补充、B、模型M和资源清理报告保留；本轮17题覆盖完成、全部失败，等待用户验收和下一步指示。
2. 核对[E续测报告](../specs/006-query-rewrite-split/phase-e-resume-20261011-report.md)、[空格验收澄清](../specs/006-query-rewrite-split/phase-e-whitespace-acceptance-20261011.md)与原E/F报告，不以修改时间推定授权。
3. 核对[完整E报告](../specs/006-query-rewrite-split/phase-e-completed-all-20261011-report.md)与[继续规则](../specs/006-query-rewrite-split/phase-e-continue-policy-20261011.md)。新版17题已采齐，10通过、7失败、0未运行；原RW07补全失败与新版RW08失败保留。不能混用不同题集成绩或改写首次输出；后续诊断、prompt修改、另批次运行及F需相应明确指示。

**009 停止点（2026-10-15）：云端兼容路径修复已交付并真实复跑，报告后暂停，等待用户验收。云端路径可用，真实问答稳定性与答案质量未通过；2 项既有提示词措辞断言仍失败；引用核验 `issue_found`。不自动修复既有失败、不自动扩展真实运行次数、不启动 30 题评测、不改前端。**

**上一停止点：007当前版本入口17题测试报告后暂停，等待用户验收；0通过/17失败，质量未通过。仅测试入口，未进入端到端；原C取消、旧B和历史失败记录保留，不自动开展006 F、005或30题。**
