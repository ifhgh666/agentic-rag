# Research: 集中提示词

日期：2026-10-12。未知项为零，研究仅通过本地代码与上游源码核对，无模型调用。

## 决策：独立模块和纯函数

采用用户指定的prompt.py及按职责取得文本的函数。上游也用函数区分各节点，参考其组织方式；不增加注册器、数据库或读取模板文件的运行依赖。参数仅限既有摘要上限、协议选择及修正反馈。[上游函数组织](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/rag_agent/prompts.py)

## 决策：收窄入口澄清边界

保留用户的完整单问原文、必要指代补全和最多三问。上游强调只用最少历史、无法确定所指时澄清；本项目额外保留容量选择例外及完整原句要求。避免把未知答案当缺少输入。没有把全部原文当逐句英文翻译，也不复制上游所有改写权限。

## 决策：其他提示等价提取

本地系统提示位于query_analysis、conversation_summary、agent_loop、generator、model_compression、query_planner。Loop压缩是keep/gaps，旧证据压缩为excerpts/gaps，两者必须独立。摘要有summary_max_chars动态上限；Loop有structured附文；generator和Loop各有原有修正消息；汇总payload有固定instruction，均登记迁移。

原规划不改结构化调用。2026-10-13用户要求入口绑定，现按下述补充决策实施；其他提示不扩大迁移。

## 决策：协议版本与提示版本分离

保留query-rewrite-v1协议，单独REWRITE_PROMPT_VERSION隔离缓存；B工程报告记录prompt.py指纹，不改旧题集。用户取消真实测试后，不修改采集器，也不生成新的真实首答。

## 决策：审阅模块后接入

用户明确要求最终检查函数，A交付真实函数全文和来源映射，B再接入；规划另附草稿。不因修改计划就运行A/B，阶段C已取消。

## 决策：保留模型与历史质量状态

006已有完整输入17题10通过/7失败，这些历史事实不能因模块化而改为通过。模型与预算保持，上游推荐不是切换授权；本计划只A/B，不评估新prompt的真实模型质量。

## 2026-10-13补充决策：独立schema直接绑定入口

用户要求schema独立定义、调用直接使用，prompt不重复格式。已核对[上游schemas](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/rag_agent/schemas.py)、[入口绑定](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/rag_agent/nodes.py)及[改写业务提示](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/rag_agent/prompts.py)。上游with_structured_output(QueryAnalysis)与该方向一致；其最多三问只在prompt，本项目保留已有schema上限。

已安装langchain-ollama 1.1.0支持json_schema及include_raw；源码将Pydantic.model_json_schema()传入Ollama.format。[Ollama官方文档](https://docs.ollama.com/capabilities/structured-outputs)说明format接收schema。[OpenAI Docs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)核对兼容response_format的json_schema/strict与maxItems参数；其他兼容服务是否支持仍取决于该服务，失败不自动降级。没有新OpenAI API key工具可用，本轮仅假传输/mock，不发云端请求。

采用include_raw保留首答与usage，结构化对象便于调用方直接读字段；窗口保守计入schema，版本/hash隔离缓存。拒绝仅加schema类但继续普通生成、仅format=json、把schema文本附回system提示或失败后重试。模型语义保真仍靠业务规则与后续另行授权的真实验收；本轮未知设计项为零，无需研究代理。

## 2026-10-13补充决策：用户指定同款模型

决定：选择granite4.1:8b并允许首次下载，保持本机Ollama、温度0、种子42及当前窗口/预算。[上游实际config.py](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/config.py)与README一致；[Ollama模型页](https://ollama.com/library/granite4.1:8b)列出约5.3GB、Q4_K_M、8.79B及工具能力。安装后的本机元数据是运行核验依据。

理由：用户明确要求替换当前4B并与上游一致，替代原A/B不切模型的范围约束。目标无需另选模型或研究代理。

考虑的替代：继续qwen3:4b-instruct不满足本轮要求；改用其他8B或云端也不属于授权。使用已运行Ollama的[流式pull API](https://docs.ollama.com/api/pull)记录下载，不因CLI不在PATH而另装运行时。模型准备后再修改配置，真实合成协议检查不能代替17题质量验收。

## 2026-10-13补充T决策：新版本独立首次批次

决定：用户“开始测试”后使用已补齐的17题，复用既有采集器和真实QueryAnalyzer；模型允许名单仅补已授权Granite8B，记录prompt/schema指纹、固定首次调用和失败继续规则。准备与执行无需新模型/下载、后端启动或用户实时澄清。

理由：与历史10/7题集一致且遵从已补齐输入的偏好；新prompt/schema/模型都已改变，必须另起批次，不能续用旧17题成绩。M的合成首答失败不冒充本批第一题，也不重试后选最好结果。

考虑的替代：恢复四道需要补充的原题、在测试中修改prompt/schema、放宽联动校验、换模型或运行端到端均不属于本轮入口测试范围。未知项为零，无需研究代理；业务变化与模型变化同时存在，前后成绩只能说明整体版本差异，不能分离归因。

## 2026-10-13 补充R：字段状态生成约束修复

决定：通过json_schema_extra的完整anyOf对象分支把已有状态联动规则显式发送给Ollama；保留Pydantic对象与现有validators。理由：model_validator不会自动生成JSON Schema，原17次结果结构满足旧schema但状态冲突；仅修改description不能解决。替代方案：丢弃‘无／否’会改变首答并掩盖矛盾；if/then语法支持不确定；改为根Union会改变调用方的BaseModel字段接口。

参考：[Ollama结构化输出官方文档](https://docs.ollama.com/capabilities/structured-outputs)。真实服务支持程度用本机首次合成请求核对，兼容API只用mock传输检查，不声称云端验证通过。

R交付：相关工程133项/后端完整585项通过，真实合成结构2/2有效、预期状态1/2通过（无历史代词误判保留）；旧17题不改判，未开展题集或端到端。见[修复报告](phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充T2：字段联动修复后的真实入口复测

决定：相同完整输入题集、Granite8B、业务prompt和预算，仅采用R已交付schema复测；旧采集代码不修改。理由：可观察字段联动修复后的真实行为，避免测试中调规则、重试选优或混用旧成绩。替代：直接将旧14项问题部分判通过、恢复需要补充的原题、使用模型Judge或推进端到端均不属于本轮。未知项为零；源码/配置与R及旧T的不同由preflight显式核对。

T2实际交付：14通过、3失败、0待定、0未运行，17/17条首答结构有效，零重试；采集/审阅工作完成不表示质量全通过。模型与产品配置/代码、旧首答/报告及正式数据保持。见[入口复测报告](phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充P：改写业务规则的顺序与通用示例

决定：保持当前Granite/schema及三个字段，改写prompt按资料事实/容量/原句或指代/共享条件顺序组织，三个合成业务例子只展示处理行为。理由：T2三失败均是既有规则执行不当，优先隔离提示改动的效果。[IBM少量示例说明](https://www.ibm.com/think/topics/few-shot-prompting)仅支持方法，不保证本模型成功。

替代：加程序语义解析/硬编码型号或删多余问题、增加Judge/重试、直接切模型不属于本次建议和授权。先冻结新变体与rubric、示例采用其他型号/数值/目标，防止把失败题答案复制进提示或依结果改标准。真实6与17必须分开报告，未知项为零。

P候选修改/验证/记录工作已交付，质量未通过：145项工程通过；真实诊断6题4通过/2失败/0待定/0未运行、原17题回归12通过/5失败/0待定/0未运行，各批独立计分。v4新增误澄清/历史混入退步，已仅撤回本轮候选，当前prompt字节恢复测试前v3；候选全文/原始失败保存，schema修复保持。T041勾选表示候选编写与试验完成，不表示最终采纳。旧失败不改判，见[候选报告](phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充L：轻量英文入口prompt候选

决定：直接测试用户给出的短英文prompt，不在本轮再添加中文规则、示例或程序语义校验。理由是用户要验证减少规则重量后的模型表现，必须隔离变量。真实测试只覆盖共享条件、比较、容量三类已知失败及同类变体。替代：同时加入few-shot示例、重写字段schema或跑17题会混淆prompt长度与其他变量，不属于本轮。

## 2026-10-18 补充A2：canonical Agent包

决定：采用用户截图中的 `rag_agent` 八文件结构作为 canonical 实现，通用检索与模型服务仍留在 `rag`。生产入口与消费者直接导入 canonical 模块；旧路径以显式 re-export 保持兼容，不复制实现。`rag_agent/__init__.py` 不 eager import graph，避免 consumer 迁移后形成包初始化循环。

提示边界按“模型可见文本”收口：固定规则和动态消息格式均由 `rag_agent/prompts.py` 的纯函数生成，schema/tool 描述仍由 `schemas.py`/`tools.py` 负责其自身协议。采集器必须冻结 canonical 文件，不能继续对兼容壳取指纹。该整理不改变 prompt 语义、模型调用次数或质量结论。

## 2026-10-18 补充A3：删除双包与兼容层

决定：按用户最新明确要求，将A2的七个职责实现直接并入现有`app/rag`，新增`rag/edges.py`，使用复数`prompts.py`与`schemas.py`，删除`app/rag_agent`、单数旧别名及无生产调用的节点兼容函数。`rag/__init__.py`保持无eager import。

理由：项目内所有消费者都能同步迁移，不存在必须维护的外部发布包；保留双包和转发文件只会增加定位成本。检索、模型、生成、评估、预算、会话、索引与pipeline仍是实际运行依赖，因此留在同一个`rag`包内，不将它们误删或塞入Agent职责文件。

考虑的替代：继续保留A2兼容层已被用户明确否决；把19个核心服务迁到新的`rag_core`会制造第三个包并扩大本阶段；保留单数`prompt.py`/`model_schema.py`会继续存在同义入口。单包迁移只改变模块路径和删除无调用兼容代码，不改变prompt语义或运行协议。
