# 修复后的真实入口复测T2报告

日期：2026-10-14（用户客户端Asia/Shanghai）。授权：用户在了解R修复及建议复测后明确要求‘开始测试’。仅执行007补充T2/T037–T039，复用完整输入17题，不运行端到端。Codex逐题审阅，待用户验收。

## 结论与剩余问题

真实入口：**14通过、3失败、0待定、0未运行**。17/17条首答结构有效。结构有效与业务通过分开计数，每题首次一次、错误后继续、未重试。旧2026-10-13的0/17及006的10/7均保持历史成绩，不能直接改判。

- RW13：结构有效，第一问保留PX-200/245 V/400 ms；第二问‘如果触发保护，如何恢复PX-200？’仅保留型号及条件式，遗漏共享245 V和400 ms，无法满足两个独立检索目标均保留场景的已批准规则。原始输出保留，继续下一题。
- RW14：结构有效，两型号过流阈值各自形成正确查询；但额外增加第三路‘哪个更高’比较检索。按照既有业务规则，比较应由两个已检索事实在最终汇总完成，不机械新增第三个比较检索分支，故业务未通过。
- RW15：结构有效，但四项独立需求被判清楚，只输出启动电压/过流阈值/维护周期前三问，静默遗漏记录保留期限；没有按既有容量规则请求选择本轮最多三项。因此是语义/需求保留失败，不是字段状态冲突。

## 固定范围与版本

顺序RW01–RW16、RW18，原四道补充输入继续使用已补齐变体；不证明跨消息代词/省略补全、原多对象澄清或待办补充能力。普通空格变化沿用用户许可，未新增运行时数字/空格语义检测。模型granite4.1:8b、temperature=0/seed=42、prompt=rewrite-prompt-v3、协议query-rewrite-v1、当前R生成schema冻结；fixture SHA256=fa63b42fba32b0d156616b8de61f62553dff11a765572042f9fe9e4287e0c9e9，schema SHA256=508c11a3e67c0e8ec6629358ffea5c93dfd63b4e32be7c70693d274d7248061a，模型digest=444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852。完整源码/配置/模型/题集快照见[manifest](../../output/prompt007/entrance-retest-20261014/run/manifest.json)与[preflight](../../output/prompt007/entrance-retest-20261014/preflight.json)。

采集器manifest的phase=E是历史字段，当前授权范围为007 T2；原C取消、005/006未完成质量任务保持。产品、采集器、题集、.env、模型与预算均未修改。wrapper只在内存指定新输出目录及实际命令标签，旧helper文件保持。每题新线程/请求、无缓存、入口1次、模型≤120秒/请求≤300秒，先存raw再审阅。期望结果不发送模型，RW18旧待办未混入新题。没有登录、工具、正式检索、Judge、云端或额外服务。

## 逐题首答与依据

| 题目 | 业务结论 | 结构有效 | Codex审阅依据 | 首答 |
|---|---|---|---|---|
| RW01 | passed | True | 首答清楚状态、单问原句及PN8733/启动电压目标保持；澄清为空，结构与业务规则均符合。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW01.raw.json) |
| RW02 | passed | True | 首答保留完整ZX-900报警阈值原问，清楚状态与空澄清一致；没有陌生型号纠错或索要阈值答案。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW02.raw.json) |
| RW03 | passed | True | Guide_V1.PDF、PX-200和启动电压目标保留，仅普通双空格合为单空格；沿用用户已明确接受的普通空格变化，不作为失败。清楚状态及空澄清有效。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW03.raw.json) |
| RW04 | passed | True | 完整单问原句保留，型号PX-200、16 A及‘不超过’/‘是否不得恢复’否定与条件均保持；清楚状态与空澄清有效。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW04.raw.json) |
| RW05 | passed | True | 原句完整保留，PX-200、195.5 V小数、300 ms及欠压/是否触发前提保持；未索要保护阈值答案，澄清为空。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW05.raw.json) |
| RW06 | passed | True | 完整过压单问原句保留，PX-200/245 V/400 ms和是否触发前提均保持；清楚状态、空澄清有效，不把未知保护阈值当作缺少输入。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW06.raw.json) |
| RW07 | passed | True | 已补全的PN8733恢复条件问题原句保持、清楚且澄清为空；没有因不知恢复答案反问用户。本题不用于证明原‘它’的代词补全能力。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW07.raw.json) |
| RW08 | passed | True | 完整恢复条件原句保持，PX-200/245 V/400 ms及‘如果触发’前提全部保留；没有断言已经触发，也没有索要应检索的恢复答案，澄清为空。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW08.raw.json) |
| RW09 | passed | True | 当前完整问题明确指定PN8733及启动电压，首答原句保持；未被历史中PX-200干扰或重新要求选择型号，澄清为空。原未指定对象/参数的歧义能力不在本题覆盖内。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW09.raw.json) |
| RW10 | passed | True | 已补全MN-42上电检查完整原句保留、清楚状态及空澄清有效；不要求实时补充型号，也不索要上电检查答案。此变体不证明原仅型号补充待办完成能力。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW10.raw.json) |
| RW11 | passed | True | 两项独立需求正确拆成过流阈值和运行记录期限两问，每问均保留PX-200型号；第二问省略‘的’不改变需求，属于获准复杂问题拆分的表达。无额外分支或事实、澄清为空。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW11.raw.json) |
| RW12 | passed | True | 三个独立需求正确拆为过流阈值、维护周期、运行记录期限三问，每问均含PX-200，没有遗漏或新增分支；‘是什么’转为‘是多少’在获准拆分中保留相同查询目标，澄清为空。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW12.raw.json) |
| RW13 | failed | True | 结构有效，第一问保留PX-200/245 V/400 ms；第二问‘如果触发保护，如何恢复PX-200？’仅保留型号及条件式，遗漏共享245 V和400 ms，无法满足两个独立检索目标均保留场景的已批准规则。原始输出保留，继续下一题。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW13.raw.json) |
| RW14 | failed | True | 结构有效，两型号过流阈值各自形成正确查询；但额外增加第三路‘哪个更高’比较检索。按照既有业务规则，比较应由两个已检索事实在最终汇总完成，不机械新增第三个比较检索分支，故业务未通过。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW14.raw.json) |
| RW15 | failed | True | 结构有效，但四项独立需求被判清楚，只输出启动电压/过流阈值/维护周期前三问，静默遗漏记录保留期限；没有按既有容量规则请求选择本轮最多三项。因此是语义/需求保留失败，不是字段状态冲突。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW15.raw.json) |
| RW16 | passed | True | 完整当前原句保持PX-200/245 V/400 ms/是否过压条件；历史40 ms未覆盖当前400 ms，没有混入旧参数或额外澄清，结构有效。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW16.raw.json) |
| RW18 | passed | True | 显式new_question动作下新问题原句保持、澄清为空；已核对模型实际输入的待澄清原题为‘无’，未发送旧‘过流保护后如何恢复？’，符合新题隔离规则。 | [首答](../../output/prompt007/entrance-retest-20261014/run/RW18.raw.json) |

原问题、上下文、首答、outcome、request/thread/model_call_id、用量与时长见每题attempt/raw，业务判断见review文件。原文未修正；[完整分析](../../output/prompt007/entrance-retest-20261014/review-analysis.json)记录原始文件SHA与逐题依据，不冒充用户人工验收。

## 实际执行与耗时

工作目录均为仓库根目录：

| 命令 | 退出状态 | 结果 |
|---|---|---|
| setup-plan.ps1 -Json / setup-tasks.ps1 -Json / check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks | 0 | 定位007，已有计划未覆盖；Spec Kit按批准T2补充设计/契约/任务，16/16规格门禁只读通过；extensions.yml不存在，前后hooks无可执行项 |
| D:/newsoft/python.exe -B output/retest_prompt007_entrance_20261014.py prepare | 0 | 新目录基线、模型身份、配置/生产代码/题集一致性通过，零模型调用 |
| D:/newsoft/python.exe -B output/retest_prompt007_entrance_20261014.py design | 0 | 只补当前设计，未改产品 |
| D:/newsoft/python.exe -B output/retest_prompt007_entrance_20261014.py capture | 1 | completed_with_failures；14通过、3失败、0待定、0未运行，见[命令记录](../../output/prompt007/entrance-retest-20261014/capture-command.json)及[summary](../../output/prompt007/entrance-retest-20261014/run/summary.json) |
| D:/newsoft/python.exe -B output/report_prompt007_retest_20261014.py | 0 | 只读分析、版本/输入/保护/UTF-8审计及报告生成，无模型调用 |
| git diff --check | 0 | 无新增空白错误 |

模型调用17，工具/检索/云端/Judge/缓存/重试均0；输入13872 tokens、输出960 tokens，用量来源['provider']。单题端到端累计229.397秒、最长48.073秒；完整批次877.466秒，包含等待Codex审阅；命令外层881.437秒，不能当作纯模型耗时。具体时戳/用量边界见[metrics](../../output/prompt007/entrance-retest-20261014/metrics.json)。

本轮未重跑pytest：当前源码与R已验证版本一致，585项工程通过作为此前证据引用，不写成2026-10-14新测。此次成绩来自真实本机Ollama首答及Codex审阅，无法证明真实检索/答案/引用或原补全能力通过。当前未运行模型Judge。Win32_Process只读进程查询返回拒绝访问，未升级权限或终止进程；随后检查输出目录无本批记录，Get-Process未显示遗留测试Python进程。

## 文件保护、任务与停止点

6643项基线文件中，仅9项获准设计/导航文件变更，6634项保持；17项正式数据保持，旧报告/首答/.env/产品/采集器/题集指纹一致，分支未变。见[保护审计](../../output/prompt007/entrance-retest-20261014/audit.json)。未安装依赖、下载模型、启动或重启服务、改索引/会话、构建前端、提交/推送；没有多代理工作。

007任务T037–T039采集与记录工作完成，不等于业务验收通过。下一阶段按用户另行授权处理本批未通过项或端到端测试；此次报告不授权继续。005 T018、006 T031/T034及R的无历史代词误判状态不由本批变更。

**报告后暂停，等待用户验收。**
