# 016 B 剩余场景真实续测报告

日期：2026-10-27（America/Phoenix）。用户在 [R 修复报告](phase-r-report.md)后明确“继续计划”，本轮恢复 Phase 6/T017 的 B02–B05。原输入/资料/判据与失败停止规则先按 Spec Kit 冻结到 [续测协议](phase-b-resume-20261027-protocol.md)，不修改产品实现，不重跑已通过首题。

**结论：本轮剩余四题 4 通过 / 0 失败 / 0 待定 / 0 未运行，待用户验收。与同产品/模型条件下 R 的 B01 通过证据合并，五类所需场景均有真实通过记录。T017 已完成，T001–T023 均已交付；这不是一次五题首次全通过，原 B01 首次失败保留。报告后暂停，等待用户验收。**

## 冻结范围与批次关系

- 真实身份沿用 `openai_compatible / deepseek-flash`、temperature=0、seed=42、原端点及密钥，正常产品工厂默认非思考；无临时 model_override 或 provider 切换。只保存端点哈希与凭据已配置标识；云端别名不证明固定权重修订。
- 续测前核对全部产品 Python 与 R 的 B01 真实运行时一致，引用该题 request_id `29fdc3e5-6942-4a76-94e2-e9a4b876d8a6` 的原始首答、review、事件及 manifest/before 和 R 报告哈希。B01 不再发请求；原首次失败不改判。
- 新批次为 `output/reference016/phase-b/remaining-20261027-01/`，独占创建。原 capture.py 不变；新增薄包装 resume_remaining.py 只过滤 B01、校验续测条件、设置子进程入口，模型和图仍使用产品实现。B02/B03 共用同一 clarify 线程及服务，B04/B05 独立线程。
- 原合成短资料 97 字符、长资料 11457 字符，各一条真实临时 Qdrant point。索引版本分别为 `5d2e93c1fcd49cd1a6eee9c73bbcba7db7fd46d68b476f64d2f5db592a2308fa` / `e9e9b7da627f97dee6242287956e1ce7acc203a41ffe8accd20fa2f094fca3de`；与原 B 冻结版本一致，短索引与 R B01 对应版本相同。源码、fixture、collector、wrapper、协议和旧证据先冻结后采集。

每题首答保存后由 Codex 阅读原问题、实际分析/状态、原始回答、工具/来源/用量并写独立 review，通过才继续。四题各运行一次，没有业务或 SDK 自动重试、Judge、改题/提示择优；本轮没有失败触发停止，watchdog 未触发。

## 逐题结果

| 题目 | 实际结果与语义核对 | 模型 / 工具 | 采集耗时 | provider Token |
|---|---|---:|---:|---:|
| B02：它的巡检周期是多久？ | passed：无历史代词对象不明，提出具体对象澄清；pending 保留原题，未检索或聚合。正常 completion=clarification | 1 / 0 | 2.401 s | 749 |
| B03：我说的是 ZX-731。 | passed：auto 恢复成 ZX-731 巡检周期原题，pending 清空；真实搜索后聚合为 72 小时，来源正确 | 4 / 1 | 3.826 s | 3166 |
| B04：请根据 NL-640 的完整维护规程，按顺序列出全部维护主流程步骤，并给出归档校验码。 | passed：两个自包含研究分支，实际 compress_context 模型调用 2 次；五步顺序与 A7-C9 正确，来源真实 | 8 / 3 | 6.621 s | 29011 |
| B05：请分别回答：ZX-731 的巡检周期是多少？ZX-731 的温度记录保存多久？ZX-731 的归档存储上限是多少？ | passed：三个自包含问题/有序分支，真实研究后聚合为 72 小时、45 天、8 GB，来源真实 | 8 / 3 | 4.029 s | 7441 |

B02 的澄清原文为英文，明确询问 inspection cycle 对应哪个 device/product/system；原参考规格不保证中文，语言不作为本题失败条件，但作为实际限制记录。B03 答案附带的 45 天、8 GB 也存在于该合成资料，无事实错误。

B04 最终五步依次为停止设备、断开测试电源、等待指示灯熄灭、检查并记录外壳状态、恢复测试电源；没有把编号 001–180 的补充巡检记录当成额外主流程步骤，归档码为 A7-C9。答案把文档未提供的生成规则/有效期/版本等明确为未知；无凭空补充数值或步骤。3 次实际工具调用均为 search_child_chunks，Parent 未调用，不能称 Parent 已经真实验收。

B05 三个子问题均保留 ZX-731，checkpoint 顺序为巡检/记录/容量，实际 3 次搜索、6 次 orchestrator 及 1 次最终聚合；答案按原请求顺序给出三事实，并说明合成资料不描述真实设备。四题均无 error；三道回答题完成后 next/pending 均为空，最终 Sources 与本次实际工具文件名匹配，页码为 null。

| case | request_id | 原始首答 | 独立审阅 |
|---|---|---|---|
| B02 | f478ab90-8ceb-4a64-93df-983d74f60b99 | [raw](../../output/reference016/phase-b/remaining-20261027-01/B02.raw.json) | [review](../../output/reference016/phase-b/remaining-20261027-01/B02.review.json) |
| B03 | 99f06d47-7fb3-46b0-8639-27769c36135c | [raw](../../output/reference016/phase-b/remaining-20261027-01/B03.raw.json) | [review](../../output/reference016/phase-b/remaining-20261027-01/B03.review.json) |
| B04 | dc27842c-6544-4b26-bf2a-8901f6457d18 | [raw](../../output/reference016/phase-b/remaining-20261027-01/B04.raw.json) | [review](../../output/reference016/phase-b/remaining-20261027-01/B04.review.json) |
| B05 | 2e46ffa7-71df-4b24-ba8e-27dd7fe95f09 | [raw](../../output/reference016/phase-b/remaining-20261027-01/B05.raw.json) | [review](../../output/reference016/phase-b/remaining-20261027-01/B05.review.json) |

每题同目录 `.events.jsonl` 保存完整公开事件。压缩只核对真实节点调用及最终事实保留，不公开内部摘要或私有推理。

## 用量与时延口径

本轮共 21 次真实模型/云路径调用、7 次真实检索工具；provider 报告输入 38432、输出 1935、总计 40367 Token，所有 usage_source=provider，model_call_limit=null。四题逐题采集耗时合计 16.877 秒，不包括冻结、启动及 Codex 审阅等待，不当作整批进程墙钟。模型累计时长按调用相加，B04/B05 的并行研究会使其大于单题墙钟，不混用这两个口径。

与 R 的 B01 合并仅作场景覆盖索引：5 类场景均有通过证据；R 的 4 次模型/1 次工具及 3143 Token 不计入本轮新增用量。原 B01 首次失败的受理/Token 未知记录保持，不回填为零或合并成一轮首次成绩。原始汇总见 [summary](../../output/reference016/phase-b/remaining-20261027-01/summary.json)、[result-audit](../../output/reference016/phase-b/remaining-20261027-01/result-audit.json)。

## 实际命令与工程/真实区别

工作目录均为 `C:\Users\ifhgz\Desktop\agentic-rag`，隔离 runner 的 pytest 子进程为 `backend`。本轮沿用原 Git 分支，没有新建/切换分支。

| 实际命令 | 退出码 | 结果 |
|---|---:|---|
| `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0 | 当前 016 和所需产物完整 |
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 保留既有模板，补充同阶段续测协议/设计，不生成新功能 |
| `D:\newsoft\python.exe output/reference016/phase-a/run.py b-remaining-collector-20261027-01 ../output/reference016/phase-b/test_resume_remaining.py ../output/reference016/phase-b/test_capture.py` | 0 | 6 passed，2.55 秒；纯选题/旧证据校验、原采集器 fake/临时索引检查 |
| `D:\newsoft\python.exe output/reference016/phase-b/resume_remaining.py prepare` | 0 | 冻结身份/资料/源码/协议与 B01 证据，建立两个独立索引，无模型请求 |
| `D:\newsoft\python.exe output/reference016/phase-b/resume_remaining.py supervise` | 0 | 原图真实 B02–B05 首答依次完成并审阅；未超时，无重试 |
| `D:\newsoft\python.exe output/reference016/phase-b/resume_remaining.py audit` | 0 | 317 项保护指纹无差异 |
| `D:\newsoft\python.exe output/reference016/phase-b/audit_remaining.py` | 0 | 旧首题/报告证据哈希一致，核对四题状态/调用/用量 |

工程完整 argv/退出码和原始输出见 [collector JSON](../../output/reference016/phase-a/b-remaining-collector-20261027-01.json)及同名 `.log`，guard 的 blocked_attempts=[]，没有实际网络或正式内容打开尝试。工程通过不冒充真实质量。真实子进程的 argv/cwd/PID/退出码见 [command.json](../../output/reference016/phase-b/remaining-20261027-01/command.json)，采集与审阅停点见同目录 capture.log。外部 900 秒观察上限包含审阅等待，只约束自建采集进程；本次正常完成，没有改变产品截止/预算策略。

本轮没有产品或前端代码改动，不重复全量后端/前端；R 的 51 项定向和 A 的 720 passed/两项既有失败只是历史结果。两项旧 prompt 断言及 005/006 原真实题库失败不因此关闭。

## 保护、完成文件与限制

新增辅助脚本 resume_remaining.py、test_resume_remaining.py、audit_remaining.py 和独立 remaining 目录，复用原 capture.py；新增本协议/报告，维护 spec/plan/research/data-model/quickstart/tasks、README、CURRENT_STATUS 与 016 失败清单。requirements 清单的 16 项设计勾选和 3 项旧 A 工程标记保持只读，依据已完成 A/R 证据及当前明确继续授权执行。`.specify/extensions.yml` 不存在，没有前后 hooks 或新增研究代理任务。

[before](../../output/reference016/phase-b/remaining-20261027-01/boundary-before.json) / [after](../../output/reference016/phase-b/remaining-20261027-01/boundary-after.json) 的 317 项保护指纹无差异，包含产品 Python、backend/.env、正式数据/索引、A 报告和 A 顶层证据；旧 B01/R 首答/审阅/事件/manifest/before/R 报告额外通过 continuation 哈希核对。没有正式数据写入/重建、模型切换、依赖升级、服务启动/重启、提交或推送；原失败与 A/B/诊断/R 报告保持。

检索链使用真实 DocumentStore/IndexStore/Qdrant/Retriever，Dense 为 deterministic、Sparse 为 local BM25，Token 估算为参考字符回退；这能验证真实模型的图/工具/状态/压缩/聚合，不证明生产 ONNX 语义召回、PDF 上传解析、HTTP/浏览器/认证或正式知识库质量。Parent 没有实际调用，英文澄清也没有改写成中文再评分。

T017 现勾选，23 项既定工程/采集任务全部交付，待用户验收。当前计划没有自动新增下一阶段；正式 PDF/ONNX/浏览器及历史题库的后续验证需要用户另行确定范围，不能从本轮结果宣称已通过。

**报告后暂停，等待用户验收。**
