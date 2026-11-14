# Implementation Plan: 恢复参考 Agent 执行语义

**Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)
**Status**: 2026-10-27 A 工程交付后用户继续授权 B；B 首题入口调用失败，0通过/1失败/4未运行，报告交付后暂停。A 的 720 passed / 两项既有失败保持历史结论。
**B 授权补充**: 用户在 A 总报告后再次“继续”，本轮进入 B；首答场景、冻结、失败停止和采集边界见 [B 协议](phase-b-protocol.md)，A 原始报告不改写。
**B 结果**: 首个真实输入在 rewrite_query 调用记录 OpenAIInvalidRequestError，约 448 ms，无答案/工具；0通过/1失败/4未运行，无重试。B 未通过，T017 部分完成，T018 失败报告交付，见 `phase-b-report.md` 和 [016 失败清单](CURRENT_FAILURES.md)。
**Branch**: 实际 Git 分支仍为 `codex/model-driven-agent-loop`；Spec Kit 按功能指针解析为 `016-reference-agent-semantics`，不切分支。

**最新 D 真实测试（2026-10-28）**：gold-1.0 Q1 使用真实 PDF/ONNX/BM25 隔离快照和当前 deepseek-flash，链路完成但遗漏已召回的“合格的万用表”；0通过/1失败/3未运行，按协议停止。模型 5 次、搜索 2 次、14.547 秒、provider Token 9527。运行结束时 423 项保护无差异，产品和正式数据未改。见 [D 报告](phase-d-real-pdf-20261028-report.md)，报告后暂停，等待用户验收。

**最新 C 收尾（2026-10-28）**：框架审阅 F1/F2 已修复；main 只移除闲置 ContextBuilder 导入/赋值，仓库指南按当前参考图更新并单列 legacy。仅做静态 AST/差异/链接核对，未运行测试、模型或服务。T024–T026 完成交付，见 [C 报告](phase-framework-cleanup-20261028-report.md)，报告后暂停，等待用户验收。

**最新 R 结果（2026-10-27）**：当前 deepseek-flash 工厂已默认关闭思考，51 项定向检查通过，无临时 override 的真实单题 completed（模型 4 次、搜索 1 次）。原 B 未完成场景和历史失败不改判，见 [R 报告](phase-r-report.md)。

**B 续测授权（2026-10-27）**：R 报告后用户“继续计划”，本轮只恢复原 Phase 6/T017 的 B02–B05，引用相同产品/模型条件下的 R B01 证据，不重跑首题。按 [续测协议](phase-b-resume-20261027-protocol.md)冻结、逐题首答/审阅、首次非通过停止，另存续测报告后暂停。没有新产品设计或技术选型，原技术上下文/宪章门槛仍适用。

**B 续测结果**：本轮剩余四题全部通过，模型 21 次、工具 7 次、provider 总 Token 40367，317 项保护指纹无差异。引用 R 的首题通过证据，当前五类场景覆盖完成，T017 勾选；原初次 B01 失败保持。见 [续测报告](phase-b-resume-20261027-report.md)，报告后暂停，等待用户验收。

## Summary

**当前 E 授权（2026-10-28）**：全量 gold-1.0 15 场景/19 轮，失败继续、最终逐题对照，见 [E 协议](phase-e-full-gold-20261028-protocol.md)。E=tasks Phase 10/T030–T032；前述 D 停止口径为历史事实，本轮不得据此跳过后题。

**E 已交付**：15 场景/19 轮均已运行，11通过/4部分正确未通过，模型79次、搜索20次、provider Token 115247；运行保护346项无差异。完整原答/正确答案和事实/附加错误/行为分开审阅，见 [对照](phase-e-answer-comparison-20261028.md)及 [E 报告](phase-e-full-gold-20261028-report.md)。未修产品，报告后暂停。
rag八文件恢复参考主图和六节点研究子图；基础模型、线程互斥、公开事件和知识库仅作外围适配。参考夹具用于独立对照，不添加第二套生产图。

## Technical Context
**Language/Version**: 既有Python3.12、React18/TypeScript。
**Primary Dependencies**: `langgraph 1.2.12`、`langchain-core 1.6.4`、`langchain-openai 1.6.5`、`langchain-ollama 1.1.0`、`tiktoken 0.14.0`；底层 `openai 3.19.2`、`ollama 0.6.2`、`httpx 0.28.1`。以上为本机发行包元数据，不是升级要求。
**Storage**: InMemorySaver，现有知识存储不迁移。
**Testing**: scripted模型、固定参考、临时Qdrant、隔离pytest、Vitest和构建。
**Target Platform**: Windows。
**Project Type**: FastAPI+React。
**Performance Goals**: 无未经实测的性能承诺，恢复实际图流。
**Constraints**: 无真实模型/正式数据访问；.env保持；不提交/重启；旧失败保留。
**Scale/Scope**: Agent核心、模型/交付适配、API、必要前端和测试。

## Constitution Check
设计层面复核未发现必须修改宪章的冲突。工程验收尚未完成，不能用本节代替 T014–T016。

| 宪章原则 | 设计依据与工程门槛 |
|---|---|
| 阶段边界 | A=Phase 1–5，B=Phase 6；A 报告后暂停，B 需验收及明确继续指示 |
| 单一职责 | rag 只放图/节点/状态/提示/工具适配；模型、交付、会话互斥在 core；知识基础设施保持 |
| 基于证据 | 保留参考资料约束提示和真实工具来源；不把来源交集当作答案语义核验 |
| 安全一致 | 认证、ready 数据校验、隐私投影和正式数据隔离保持；保护项核对纳入 T015 |
| 可观察可验证 | 请求标识贯穿事件；参考对照、会话、流式、隐私与必要前端覆盖落入 T013–T014 |

旧的具体额度/截止/准入算法由 016 规格替代，不等于放宽密钥、数据一致性或报告义务。研究与设计补全后再次按上表核对，设计门槛成立；运行门槛继续待证据闭合。

## Project Structure
rag/放参考graph/nodes/edges/state/prompts/schema/tools；core/放原生模型与交付/会话适配和legacy独立能力；knowledge/不变。
`backend/tests/fixtures/reference016/` 保存固定源、manifest 和许可证；`tests/fakes/reference_baseline.py` 仅在测试命名空间加载参考。模型/会话/观测分别为 `core/reference_model.py`、`reference_session.py`、`reference_observation.py`，公开交付为 `core/pipeline.py` 和 `api/chat.py`。本目录包含研究、数据、契约、验证、任务和迁移账本。

## Architecture
主图summarize_history→rewrite_query→interrupt或Send→aggregate_answers。
子图orchestrator→collect，或tools→should_compress_context→可选compress→orchestrator；研究超限fallback→collect。
兼容端点的 ChatOpenAI 包装显式设置入口 `method=function_calling`；Ollama 保留节点 `with_structured_output(QueryAnalysis)`，已安装 ChatOllama 默认 `json_schema`。两种 provider 的研究节点均 `bind_tools`，不注入旧 schema 提示；fake 只作工程验证。工具 content 为参考字符串，artifact 追溯真实来源。
参考token估算/压缩公式；新图不读取旧deadline/配额/准入/输出上限。
checkpoint 是唯一在线会话来源；清理 pending 和 cancel 不调用模型，new 随后正常运行新问题。模型补充失败保留可恢复待办，普通失败不误认澄清；实时事件只作观测，只有最终聚合进入答案区。
原独立接口的旧提示/类型冻结到legacy依赖，不经新主图。
非公开诊断沿用独立worker，不参与决策。

### 原限制与 016 行为

| 原约束 | 016 在线行为 | 验证归属 |
|---|---|---|
| 300 秒请求 / 120 秒单调用 | 不传旧 deadline/timeout；不承诺新的 600 秒或其他墙钟上限；服务/传输异常仍可能发生 | T009 参数检查；B 真实行为另验 |
| 8/12 总模型调用、5/4/3 分支额度 | 取消；usage 只统计，`model_call_limit=null` | T009/T011/T012 |
| 8 工具请求 / 10 研究迭代 | 保留参考计数；当前批次计入，先判断无工具，越界批次不执行 | T007/T014 边界对照 |
| 递归 50 | 保留图步数配置，不能解释为模型调用配额 | T010/T014 |
| 3072 输入准入 / 768 输出上限 | 正常入口不读取旧设置；实际服务上下文/输出能力不由此保证 | T008/T009 |
| 历史消息 4 | 回答前保留 3 条普通消息，其余合并进历史摘要；回答后为近期 4 条设计 | T006/T007 |
| 2000 / 0.9 | 工具执行后严格大于动态阈值才模型压缩；保留首问和检索标识 | T008/T014 |

Parent 工具无先搜索的程序前置条件；提示仍建议先搜索。子块搜索保留现有非空 query、limit 1–20、索引 ready 和 min_score 的外围适配。SDK 默认、原文估算和差异依据见 [research.md](research.md)。

### legacy 保留与隔离

| 范围 | 保留的实际模块 | 正常图边界 |
|---|---|---|
| 旧提示/schema/状态/缓存/摘要 | `core/legacy_prompts.py`、`legacy_schemas.py`、`legacy_state.py`、`legacy_cache.py`、`legacy_summary.py` | 只供独立旧消费方和历史采集器 |
| 独立分析/生成/治理/会话/证据 | `core/query_analysis.py`、`answering.py`、`model_call.py`、`model_provider.py`、`conversation.py`、`legacy_rag.py` | 不接新主图，不作为失败回退 |
| 旧 ModelAgentLoop/ContextAdmission/旧主图 | 不复制为第二套生产图 | 受替代断言须逐项记迁移；保留原快照和失败 |

T005 负责依赖归属与静态守护，T013 负责逐 nodeid 测试迁移；不能把旧子任务报告当成当前所有导入仍失败的证明。最终范围索引见 [test-migration.md](test-migration.md)。

## 阶段与任务映射
A对应tasks Phase1–5：冻结/规格/基线→红测→核心→交付→隔离回归/审查/A报告。B对应Phase6，A验收后另行授权真实模型。
每阶段报告后暂停，不自动执行B或重启服务。

## Validation
唯一完整后端验证入口为 [quickstart.md](quickstart.md) 中的 guard runner（四个明确测试目录，不扫描 tmp）。执行批次使用全新标签，原命令/退出码/日志不覆盖。定向、完整后端和前端分别报告。

T014 的工程门槛为：无新增失败、无 collection error、无网络/正式数据阻拦尝试，参考/会话/公开事件/隐私检查满足；仅两项冻结 legacy prompt 措辞失败可作为有记录的既有例外，仍必须报告 pytest 退出 1。24 项正式 PDF 跳过和 2 项真实 Dense 排除单列，不能算通过。其他原有失败若被新契约替代须在迁移账本解释，不能静默去掉。

迁移前 `before-full` 为 819 passed / 3 failed / 24 skipped / 2 deselected，含两项旧 prompt 和一项旧 deadline 失败。收尾前完整 `resume-full-20261026-final` 为 713 passed / 3 failed / 24 skipped / 2 deselected，含 pending 保留失败；其后定向 4 passed。历史批次不改写。

本轮 `a-close-full-20261027-01` 完整隔离为 **720 passed / 2 failed / 24 skipped / 2 deselected**，退出 1，仅剩允许单列的两项旧 prompt 失败。新增 pending 重复补充/ASGI 断开六项回归先失败、修复后相关 29 passed；增强节点访问的 parity 为 8 passed。前端重跑 40 passed、构建退出 0。两位独立审查者复核修复无残余发现；保护指纹无差异。工程结论为无新增失败，不能称全部测试通过或真实质量通过。

T015 已核对配置/knowledge/历史失败的原保护清单并解释迁移统计；T016 交付 `phase-a-report.md` 并更新导航。A 工程完成不等于用户验收；报告后暂停，等待用户验收。原规划复核报告与全部失败首答保持。

## Complexity Tracking
没有第二套生产Agent/旧图开关；不以八文件要求吞并基础设施；旧独立能力不接正常图。

## 2026-10-27 R：真实模型兼容修复（本轮获准）

目标：修复原 B01 的 HTTP 400，不改变参考图算法或题目。根据用户最新“继续”，单阶段 R 对应 T019–T023，复用本文件技术上下文；不创建新功能、分支或安装依赖。

设计：只在 `core/reference_model.py` 的原生 ChatOpenAI 构造处，对精确模型名 `deepseek-flash` 增加 `extra_body.thinking.type=disabled`，使入口、研究工具往返、摘要及聚合都继承同一非思考模式。其他云模型、本地模型与 legacy 路径不注入该字段。只修入口会让研究路径仍依赖当前 ChatOpenAI 不保留的 reasoning_content；本轮选择已真实验证的整链路方案，不引入新的提供商 SDK 或私有推理持久化。

先保存代码/文档/Git及保护指纹，再在实际产品 factory→LangChain→OpenAI SDK→本地假 HTTP 接缝建立 400 红测；服务替身仅模拟已确认的协议限制，不冒充真实质量。修复后验证结构化、原生工具往返和普通生成都携带参数，其他模型未被误改、失败不重试。运行参考图/会话/公开契约/隐私定向回归；只有新增失败或未解决疑虑才扩大回归。

真实复验：复用既有 `diagnose_real.py --graph`，不传 `--thinking-disabled`、不修改返回的模型、不追加运行时 override，直接调用修复后的产品 factory；只运行隔离 B01 一次。相同真实 provider/model/端点/密钥、温度/种子、原提示/schema，真实临时 Qdrant 工具，deterministic Dense/local BM25。正确答案/实际搜索/聚合/来源/usage 均须核对。失败保存并停止，不重试、改题或继续 B02–B05。

宪章复核：模型传输适配仍在 core，图、会话、知识库和前端契约不变；原始失败和私有内容保护不变；一阶段一报告。设计门槛通过，无新增技术选型或未解决技术澄清，无需额外研究代理。验收门槛待实际证据；报告路径 `phase-r-report.md`。**报告后暂停，等待用户验收。**
# 2026-10-28 C：框架审阅收尾（本轮获准）

用户在框架静态审阅发现 F1/F2 后明确“继续”，本轮仅修两处：移除 main.py 的闲置 ContextBuilder 导入/实例化，更新 docs/repository-guide.md 的当前模块地图、装配和调用图。对应 tasks Phase 8/T024–T026，不扩展模型/图/接口、依赖或真实评测。

研究与设计：F1/F2 已由源码及改造前快照定位，无新增技术未知项或选型。ContextBuilder 构造只保存两个引用且返回对象未被使用，因此只移除启动点，不删除类或独立旧消费方。指南以当前原生模型→checkpoint→参考主图/研究子图为在线事实，旧 ModelCallRunner/QueryAnalyzer/ConversationMemory 等按独立旧消费范围说明；不重写历史报告。复用既有状态模型和 Chat/SSE/transport 契约，没有新增实体或公开接口。

验收：先保存范围内文件和原始哈希；用标准库 AST 仅解析文件、确认 main 的语义树恰好少一个导入名和一条闲置赋值，既有图/会话/工具/模型和独立 ContextBuilder 不变；检查 Markdown UTF-8、链接和指南与源码的一致性，保存精确 diff。此为静态核对，不运行 pytest/npm、真实模型、服务或正式数据操作，不把历史测试算成本轮通过。

宪章复核：职责与参考行为保持，修复仅一个装配残留和错误导航；原失败、配置和用户数据保护保持，一阶段一报告。完成后保存 `phase-framework-cleanup-20261028-report.md`；**报告后暂停，等待用户验收。**

## 2026-10-28 D：真实 PDF/ONNX 首批测试（当前获准）

用户要求“开始真实测试”。D=tasks Phase 9/T027–T029，按 [D 协议](phase-d-real-pdf-20261028-protocol.md)执行 gold-1.0 的 Q1–Q4；此前 B 的合成资料/确定性 Dense 限制不适用于本次明确测试授权。实际模型/密钥、产品主图、提示/schema 和正式数据不改；不新增产品功能。

技术上下文沿用现有 Python/FastAPI/LangGraph、真实 fastembed ONNX 与 Qdrant/BM25。研究核对发现旧 capture_v4_formal.py 仍消费退役 Graph/会话/核验接口且限定 Ollama，不能作为当前参考图入口；仅在 output 下建立侧车，复用原 B 的 capture_one 公开事件记录，直接装配当前 AgentGraphService/RagPipeline。现有 gold-1.0 已审核，真实源 PDF hash 一致，正式清单含两份相同 PDF/16 个 Point，不清理重复项。无新依赖、接口或未解决的选型，无需研究子代理。

准备：保存文档/Git/423 项初始保护指纹，只读一致性快照 Qdrant，复制 PDF/Markdown 与模型资源；本地预加载 ONNX、原 BM25 词表，校验快照 ready、版本/点数及 PDF。若环境未就绪则如实阻断，不重建或下载替代模型。采集：四题串行、独立线程、原 history_fixture；每题首答落盘并审阅，通过后再进入下一题，非通过停止、无重试，保留 not_run。外部 900 秒 supervisor 与产品无截止策略区分；不运行 Judge 或模拟问答。

复用现有数据模型和聊天/传输契约；侧车仅增加 freeze/raw/events/review/summary 等测试产物，不扩充公开 API。真实用量、工具调用、来源、顺序和事实按原 gold 判据核对；保护指纹前后相同才闭合数据保护。宪章门槛：阶段单一、职责无迁移、真实证据可追溯、标准答案不注入模型、正式数据只读、密钥和私有提示不落盘。设计复核通过，实际质量以新报告为准。

停止点：`phase-d-real-pdf-20261028-report.md` 保存后暂停；不自动修失败题、运行 Q5–Q15、启动用户服务或浏览器。旧 A/B/R/C 报告和失败不改写。

## 2026-10-28 E：完整真实采集和标准答案对照

沿用 D 的现有依赖、真实 ONNX/BM25 和正常 AgentGraphService/RagPipeline，正式 PDF/索引只读克隆到新 E 目录。D helper 仅导入辅助函数，不修改旧采集器或复用旧回答；新侧车为每个场景创建独立进程/线程，场景内交互保留同一 checkpoint。每个场景外部 900 秒 watchdog，失败/采集异常均记录后继续下一场景，不把外部终止称为产品截止；不并行真实模型请求，不恢复旧 300/120 秒或总模型额度。

研究结论：15 场景包括 10 事实回答、4 两轮交互、1 无答案，实际共 19 轮；原 capture_one 硬编码 auto，不适合直接承接全部动作，因此只在 E 侧车复制公开事件记录逻辑并透传原 action。无新公开接口、产品实体、依赖或技术选型；无须研究代理。旧 uncertain 关系标签与当前契约的差异只作诊断，语义评判保持 pending/不检索等用户行为要求，参考正确答案和必答点不改。

验收：冻结后依序尝试全部原输入，无重试、无质量 gate；全部采集后逐题人工语义审阅（Codex，非用户签收），比较完整原答、参考答案、事实覆盖、数值、步骤、禁答和真实来源，分类型统计。生成机器可读 comparisons.json、完整逐题对照 Markdown 和独立 E 总报告；原 D/历史不改判。宪章复核：同一阶段、职责保持、正式数据隔离、私有信息保护、真实证据完整，不传标准答案给模型。报告后暂停，不自动修复。

