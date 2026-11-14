# Data Model: 提示定义与调用边界

本功能不新增数据库、会话字段或产品API状态。

## PromptDefinition

每项有名称、职责、取得函数、正文、支持参数、消费者和来源/差异说明。函数输出为非空str，无网络、模型、文件或记忆副作用。固定指令集中，动态问题/历史/证据由原节点构建。

入口正文提示版本REWRITE_PROMPT_VERSION独立于三字段协议版本；语义改变时提示版本提升，加入缓存键并记录于B工程报告。其他等价提取不改变协议或语义版本。

## CallBinding

记录节点、函数、消息角色及原参数。摘要传既有max_chars；Loop传native/structured协议；修正传既有反馈，返回相同修正指令，不调用模型或增加次数。汇总instruction仍作为原payload字段；保留序列化格式。

## QueryAnalysis（保持）

严格bool is_clear、list[str] questions、str clarification_needed，禁止额外字段；最多三问，每问非空、≤2000字符且不重复。清楚时1–3问与空澄清；不清楚时空问题与非空澄清。只有现有结构/容量校验，无新增数字/空格语义校验。待办继续、新题、取消的状态转移均沿用006。

2026-10-13补充：description说明字段含义与结果状态，结构随请求发送，消费者读取ModelResult.structured_output。生成schema约束类型/必填/额外字段/最多三项；自定义validators继续检查非空、重复和字段联动，不自动变成生成语法，也不保证数字保真。content仍保留原始可展示文本和用量。缓存增加提示版本、json_schema模式和schema哈希，保守输入估算计入schema。

## PromptReview

规划稿→实际模块初版待用户检查→获准接入→工程检查和最终交付。真实阶段已取消。这里是开发交付状态，不加入产品状态机；原A、结构化补充及B均已工程交付，报告后暂停，等待用户验收。

## EngineeringDelivery

B工程交付保存prompt.py哈希、提示版本、实际消费点、缓存隔离与检查命令/结果。不修改采集manifest，旧summary/raw和质量状态保持；没有新的真实请求ID或模型质量结论。

## ModelSelection（补充M，复用现有配置）

OLLAMA_MODEL单一配置值由qwen3:4b-instruct改为granite4.1:8b，提供方继续ollama。Settings、缓存模型身份、会话和公共API结构保持；不新增模型选择状态或数据库实体。安装记录保存实际模型tag、digest、大小、量化和能力。

已有.env其余行只核对哈希，不保存敏感值。补充记录包括下载、配置生效、工程检查、首次合成模型结果和用量、服务运行状态、保护指纹；不修改旧数据、题集成绩或报告。

## EntranceTestRun（补充T，复用采集记录）

批次独立manifest保存题集完整指纹、配置、模型digest、prompt版本、schema指纹及相关源码指纹。每题有独立request_id/thread_id/model_call_id、attempt/raw、首答、运行失败原因、usage和实际耗时；有效结构另有审阅状态及依据。协议失败直接记failed，原文仍保存。

保存→审阅→继续下一题；错误继续不等于错误通过。允许passed/failed/uncertain/not_run，批次有失败时completed_with_failures并退出1；整体预算违规或用户中断为stopped。旧批次不修改，旧代词/省略质量与端到端未测状态保持。

## 2026-10-13 补充R：字段状态生成约束修复

QueryAnalysis的字段和运行时validator不变。生成schema增加两个完整对象分支：true/1–3问/澄清const空串，false/0问/澄清minLength=1；每分支三个必填字段、extra禁止、严格类型。重复/纯空白/裁剪后长度仍由既有后置校验检查；不保证语义保真。schema哈希改变自动隔离入口缓存，不修改prompt版本或fixture。

R交付：相关工程133项/后端完整585项通过，真实合成结构2/2有效、预期状态1/2通过（无历史代词误判保留）；旧17题不改判，未开展题集或端到端。见[修复报告](phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充T2：字段联动修复后的真实入口复测

EntranceTestRun沿用原记录实体，但独立新批次。phase=E是既有采集字段，不代表006阶段再次获准；当前授权为007 T2。状态/字段/首次协议不变，所有read-only指纹和原始结果独立保存。模型/程序协议有效与业务语义是否正确分开记录；reviewer标明Codex逐题检查（待用户验收）。

T2实际交付：14通过、3失败、0待定、0未运行，17/17条首答结构有效，零重试；采集/审阅工作完成不表示质量全通过。模型与产品配置/代码、旧首答/报告及正式数据保持。见[入口复测报告](phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充P：改写业务规则的顺序与通用示例

QueryAnalysis与API/动作/会话实体不改；PromptDefinition只升业务版本v4，现有cache key自动隔离v3。诊断数据是新的6题合成冻结fixture；原回归17题保持字节。每批沿用attempt/raw/review/summary，调用预算分别6/17，phase=E为采集器历史字段，本次授权为007 P。

P候选修改/验证/记录工作已交付，质量未通过：145项工程通过；真实诊断6题4通过/2失败/0待定/0未运行、原17题回归12通过/5失败/0待定/0未运行，各批独立计分。v4新增误澄清/历史混入退步，已仅撤回本轮候选，当前prompt字节恢复测试前v3；候选全文/原始失败保存，schema修复保持。T041勾选表示候选编写与试验完成，不表示最终采纳。旧失败不改判，见[候选报告](phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充L：轻量英文入口prompt候选

PromptDefinition入口版本由rewrite-prompt-v3升为rewrite-prompt-v5，QueryAnalysis三字段和生成schema不变。LightPromptRun为独立六题批次，沿用attempt/raw/review/summary实体；旧T2、P候选和正式fixture不覆盖。质量状态与结构协议单独记录。
