# 阶段 E：已补全问题题集首次真实测试报告

日期：2026-10-11。用户先要求将需要补充的测试问题写完整，随后明确指示“执行”。本轮仅执行这版17题的E入口采集，沿用模型、prompt和预算；不执行F、005后续阶段或30题评测。

**结论：7通过、1失败、9未运行；在RW08实质失败后停止。E尚未通过。** 完整写明设备、数值及条件的RW08仍被模型判为不清楚，模型反过来询问用户所求的恢复条件。RW07完整输入通过不能证明原代词补全失败已修复。T031/T034和005 T018保持未完成。

## 冻结与首次采集范围

题集为[已补全17题](../../backend/tests/fixtures/query_rewrite_v1_completed_cases.json)，版本 `query-rewrite-completed-v1-20261011`，冻结于2026-10-11，SHA-256为 `fa63b42fba32b0d156616b8de61f62553dff11a765572042f9fe9e4287e0c9e9`；产品入口协议仍为 `query-rewrite-v1`。RW07–RW10按[题集调整报告](phase-e-completed-fixture-20261011-report.md)写完整，其余13题不变。原24组夹具、原E/F报告和全部首答保留，不搬用旧成绩。

新目录为 `output/query-rewrite-v1/e-completed-first-20261011-01/`，从RW01开始，未使用 `--resume-from`。顺序固定RW01–RW16、RW18，最多17次入口模型调用。每题只调用一次、使用独立合成请求和线程；保存 `.attempt.json`、首次 `.raw.json` 后，由编码代理人工审阅写入 `.review.json`，只有通过才提交下一题。普通空格变化依[用户验收澄清](phase-e-whitespace-acceptance-20261011.md)接受；语义、数字、型号、否定和条件仍需保留。

本机Ollama `qwen3:4b-instruct`，4.0B/Q4_K_M，digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`；temperature=0、seed=42。窗口4096、输入3072、输出768、安全余量256；单次等待120秒、每题总期限300秒，入口预算1、工具预算0。没有缓存、重试、模型Judge、云端调用、模型下载或正式索引访问。模型身份通过本机 `/api/tags` 只读取得。

配置、代码哈希、原题和上下文见[manifest](../../output/query-rewrite-v1/e-completed-first-20261011-01/manifest.json)；独立题集版本和覆盖说明见[批次背景](../../output/query-rewrite-v1/engineering/phase-e-completed-run-20261011/batch-context.json)。输入只包含当前问题和冻结上下文，预期答案及人工标准在推理后用于审阅，不发送给模型。原始输出指现有provider移除私有推理后的首次可见正文，不是HTTP传输体。

## 实际逐题结果

| 案例 | 结果 | 入口耗时 | 输入/输出Token | 人工核对 |
|---|---|---:|---:|---|
| RW01 | passed | 15.507秒 | 498 / 37 | PN8733启动电压完整单问原文保留 |
| RW02 | passed | 4.221秒 | 499 / 38 | 陌生但明确的ZX-900未被纠错或要求澄清 |
| RW03 | passed | 4.767秒 | 505 / 43 | 仅文件名后的双空格变单空格，按用户标准接受 |
| RW04 | passed | 5.406秒 | 506 / 45 | 16 A、“不超过”和“不得恢复”均保留 |
| RW05 | passed | 6.295秒 | 518 / 57 | 195.5 V和300 ms共同条件原文保留，仍一问 |
| RW06 | passed | 5.631秒 | 515 / 54 | 245 V和400 ms共同条件原文保留，仍一问 |
| RW07 | passed | 5.140秒 | 520 / 37 | 已写完整的PN8733恢复条件单问保留，没有要求补充 |
| RW08 | failed | 8.690秒 | 562 / 78 | 完整条件恢复问题被误判不清楚，无检索问题，反问所求信息 |
| RW09–RW16、RW18 | not_run | 不适用 | 不适用 | 失败后未提交，共9题，无请求/模型调用ID |

每题请求ID、线程ID、调用ID及审阅文件名可在[summary](../../output/query-rewrite-v1/e-completed-first-20261011-01/summary.json)逐项追溯。以上只是入口问题处理，不是RAG答案正确性或引文验收。

## RW08失败证据与判断

当前完整问题：

> 如果 PX-200 在输入电压为 245 V、持续 400 ms 时触发保护，PX-200 的恢复条件是什么？

首次模型结果为 `is_clear=false`、`questions=[]`，澄清文字为：

> PX-200 的恢复条件是什么？如果输入电压为 245 V、持续 400 ms 时触发保护，恢复条件是否与电压、持续时间或设备状态相关？是否需要特定的重启、冷却或信号输入？

见[首次原始记录](../../output/query-rewrite-v1/e-completed-first-20261011-01/RW08.raw.json)和[人工审阅](../../output/query-rewrite-v1/e-completed-first-20261011-01/RW08.review.json)。请求ID `rw-e-fc8ff3e623674c5ba6a1792654ae73f2`，调用ID `model-172a4158bee24aee98f488a378114f51`。

设备、输入电压、持续时间、条件性和恢复需求已明确，保存的模型输入也包含这些内容。输出没有指出缺失的指代对象或必要用户信息，却让用户说明恢复与哪些条件相关、是否需要重启等；这些正是题目要求从资料中查询的信息。该行为与“完整问题直接检索”的预期不符。依据输出表现，可判断模型把所求信息当成了需要用户补充的信息；更深的内部成因未验证。

这是人工发现的清晰度/澄清质量失败。三字段协议正常，`failure_reason=null`；没有入口运行时语义检测将其拦下，也没有数字或空格失真。采集器在人工写入failed后以 `semantic_failure` 停止，这个批次停止理由不会加入产品运行时。

## 用量、时延和真实/工程区别

实际模型8次，工具/云端/Judge/自动重试均0；每个已运行案例恰好1次 `query_analysis`，无缓存命中。provider实测Token为输入4123、输出389、合计4512。入口请求耗时合计55.657秒，模型trace耗时合计55.649秒。

批次自manifest创建至停止为238.686秒，含逐题人工审阅与采集等待；外层执行命令246.356秒，另含导入与准备。二者均不是单次推理耗时。各已运行题在120秒模型等待及300秒请求上限内结束，没有真实到期压力测试，不能据此声称300秒截断行为通过。

本轮真实调用只使用Ollama入口，不执行检索、生成答案、平台登录或聊天API，也不写普通历史/待办。采集脚本和生产源码没有修改，未重跑fake/scripted回归、前端测试或构建；上一轮97项工程通过只作历史记录，不冒充本轮结果。新增本地检查仅审计JSON、用量、输入、UTF-8、链接和文件指纹，不是模型语义校验或质量分数。

## 实际命令与产物

| 工作目录 | 实际命令 | 退出状态与结果 |
|---|---|---|
| 仓库根 | `./.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；定位006；规格checklist为16/16，无extensions配置 |
| 仓库根 | `D:/newsoft/python.exe output/run_query006_e_completed_real.py` | 1；封装下列真实入口命令并记录退出状态；RW08失败后停止 |
| backend | `D:/newsoft/python.exe -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_completed_cases.json --output ../output/query-rewrite-v1/e-completed-first-20261011-01 --stop-on-failure` | 1；实际运行8题，7通过、1失败、9未运行 |
| 仓库根 | `D:/newsoft/python.exe output/read_query006_e_completed_raw.py RWxx` | RW01–RW08各执行一次均0；在每题审阅前独立读取已保存UTF-8输出，排除PTY折行显示干扰 |
| 仓库根 | `D:/newsoft/python.exe output/audit_query006_e_completed_real.py` | 0；记录、预算、输入/输出承载、历史保护与文档检查通过；不改变RW08质量失败结论 |
| 仓库根 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

精确子进程参数和工作目录见[invocation](../../output/query-rewrite-v1/engineering/phase-e-completed-run-20261011/invocation.json)，真实退出与外层耗时见[exit](../../output/query-rewrite-v1/engineering/phase-e-completed-run-20261011/exit.json)，保护基线见[baseline](../../output/query-rewrite-v1/engineering/phase-e-completed-run-20261011/baseline.json)，核对结果见[artifact-audit](../../output/query-rewrite-v1/engineering/phase-e-completed-run-20261011/artifact-audit.json)。

完成本报告、批次首答与审阅记录，并同步README、CURRENT_STATUS、spec/plan/tasks、quickstart和验收矩阵的当前事实。核对260个保护文件及17项正式数据/索引和已有备份，指纹均未变；生产源码、prompt、采集工具、旧/新冻结夹具、既有报告和原始证据、失败清单及`.env`均保留。25份文档的UTF-8和本地链接检查通过。没有提交、推送、服务重启或正式知识库修改。

新版仅观察完整输入处理，未验证原跨消息代词/省略补全、多对象澄清或只补充型号的待办续补。原RW07失败仍保留；本轮RW08失败是新版独立事实，不能将不同题集成绩合计成一套通过率。RW09之后的完整问题、拆分、比较、容量及当前历史条件优先场景均未运行。F原Q16失败与C-UV/比较题未运行状态不变。

下一步范围是用户明确指定的RW08诊断、prompt调整或另批次入口复验；本报告不自动开展这些工作。F仍为另阶段，须用户明确指示，不能凭新版RW07通过继续F或005。按根AGENTS单阶段规则，**报告后暂停，等待用户验收。**
