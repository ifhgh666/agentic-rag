# 016 D：真实 PDF / ONNX 首批测试报告

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-28（America/Phoenix）。用户明确要求“开始真实测试”，本轮按 [D 协议](phase-d-real-pdf-20261028-protocol.md)执行已批准 gold-1.0 的 Q1–Q4 首批，任务为 Phase 9/T027–T029。

**结论：0 通过 / 1 失败 / 0 待定 / 3 未运行。Q1 的真实模型与检索链路完成，但答案漏掉已批准必答事实“合格的万用表”。按非通过即停止规则，没有运行 Q2–Q4、重试或修复。报告后暂停，等待用户验收。**

## 实际测试条件

- 模型：当前实际 `openai_compatible/deepseek-flash`，temperature=0、seed=42，使用产品原生工厂的默认非思考策略，无临时模型 override、业务重试或 provider 切换。端点和凭据不披露，云端模型别名不证明固定权重修订。
- 数据：原已批准 `gold-1.0` 的 Q1–Q4、原 history_fixture、必答事实和禁答项。题集 hash 为 `9049a61f…ab2b369`，源测试 PDF hash 为 `4f2bc2fc…365017`；标准答案只用于采集后的审阅，不传给被测模型。
- 知识：正式测试库的只读隔离快照，原有两份同内容 PDF、16 个 Qdrant Point 保持，索引清单版本 `5bddb72a…1ff4184`；SQLite 经 mode=ro 一致性备份。正式目录没有创建 Qdrant 客户端、迁移或重建。
- 检索：真实 fastembed 多语言 MiniLM ONNX，384 维；真实 Qdrant/BM25，原词表与 stemmer 配置，未使用 deterministic、fake/mock 或空词表。模型缓存复制到隔离目录，真实预检返回 7 条结果；Token 估算器为未修改的 `cl100k_base`。
- 入口：当前 `AgentGraphService → RagPipeline`，复用原 B 的公开事件 capture_one。每题独立线程；Q1 的原用户历史明确 PX-200/PDF 主题。没有给模型注入标准答案或先前平台回答。

冻结详情见 [manifest.json](../../output/reference016/phase-d/formal-pdf-20261028-01/manifest.json)和 [fixture.json](../../output/reference016/phase-d/formal-pdf-20261028-01/fixture.json)。

## 逐题结果与原答

| 题目 | 状态 | 实际情况 |
|---|---|---|
| Q1：设备上电前需要检查哪些内容？ | failed | 链路 completed，包含电压/频率范围、接地、负载、急停、指示灯、面板故障状态，遗漏“合格的万用表” |
| Q2：PX-200 的过流保护阈值是多少？ | not_run | 因 Q1 非通过停止 |
| Q3：过流保护后如何恢复？ | not_run | 因 Q1 非通过停止 |
| Q4：运行记录默认保留多久？ | not_run | 因 Q1 非通过停止 |

Q1 request_id=`[运行标识已移除]`，thread_id=`d-real-pdf-Q1`。入口按原历史恢复 PX-200，并生成一个自包含子问；pending 清空，最终聚合完成，无传输错误。

原始完整答复保存在 [Q1.raw.json](../../output/reference016/phase-d/formal-pdf-20261028-01/Q1.raw.json)，不覆盖或补写。其开头列出检查项目和 198–242 V、49–51 Hz，另引用第 6 章简化问答与第 1 章启动条件，但全文没有万用表。按原 gold 必答事实核对，7 项中 6 项覆盖、1 项遗漏；这不是新的总体准确率。来源匹配或 completed 不能覆盖此完整性失败。

**召回证据**：原记录已确认相关正文被召回，但最终答案仍遗漏必答要点。逐命中标识和检索原文已移出公开仓库。未采集私有研究摘要，不能确定遗漏首先发生于压缩、研究还是聚合环节，也不把推测写成根因。

逐事实判断见 [Q1.review.json](../../output/reference016/phase-d/formal-pdf-20261028-01/Q1.review.json)，原始节点/工具/检索/答案事件见 [Q1.events.jsonl](../../output/reference016/phase-d/formal-pdf-20261028-01/Q1.events.jsonl)，停止与未运行记录见 [summary.json](../../output/reference016/phase-d/formal-pdf-20261028-01/summary.json)。审阅者为 Codex，不冒称用户验收；新增失败编号 `D-Q1-MISSING-MULTIMETER`。

## 真实调用、用量和耗时

| 项目 | 实际记录 |
|---|---:|
| 模型 / 云路径调用 | 5 / 5 |
| rewrite_query | 1 |
| orchestrator | 2 |
| compress_context | 1 |
| aggregate_answers | 1 |
| search_child_chunks | 2 |
| retrieve_parent_chunks / Judge | 0 / 0 |
| 输入 / 输出 / 合计 Token | 8201 / 1326 / 9527，provider 实测 |
| Q1 管线采集耗时 | 14.547 秒 |
| 首个 answer 事件 | 13.243 秒 |
| 模型耗时累计 | 9.766 秒 |

两次搜索合并后观察到 10 个唯一 Child，最终 Sources 匹配两份实际同内容文档。来源页码元数据为 null，如实保留，没有推断补页码。耗时是本题 Graph/pipeline 采集时间，不包括冻结、资源准备或审阅等待，也不是浏览器端时延。

## 资源准备失败与处理

首次 prepare 在 `verified_bm25_cache` 抛出 `LocalEntryNotFoundError`：默认临时 BM25 缓存不再包含所需资源。此时没有创建问答请求，LLM 调用为 0。原 [prepare-error.json](../../output/reference016/phase-d/formal-pdf-20261028-01/prepare-error.json)、[首次采集器快照](../../output/reference016/phase-d/formal-pdf-20261028-01/preflight-attempt1-collector.py)和 [首次准备记录](../../output/reference016/phase-d/formal-pdf-20261028-01/preflight-attempt1.json)保留。

随后仅补齐官方 Qdrant/bm25 的 936 字节 english.txt，SHA256 与历史正式批次 `019F104B…B6451` 完全一致；沿用原 stemmer，不替换为本地空词表。下载来源、时间和完整指纹见 [download.json](../../output/reference016/phase-d/resources/bm25/download.json)。恢复资源准备后真实 ONNX/BM25 预检通过，才开始唯一一次 Q1。资源下载不能称为完全离线，准备恢复也不是问答答案重试。

## 文件、命令与保护核对

工作目录均为 `C:\path\agentic-rag`；实际 Python 为 `D:\newsoft\python.exe`，Git 分支保持。主要新增为 output 下采集侧车/快照/原答和本报告；spec/plan/research/data-model/quickstart/tasks 补充 D 范围，README、CURRENT_STATUS 与功能失败清单更新当前结果。**产品 Python、模型配置和正式知识数据没有修改。**

| 实际命令 | 退出码 | 结果 |
|---|---:|---|
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 复用当前 016 计划，未创建新 feature |
| `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0 | 读取模板，追加单阶段 T027–T029 |
| `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0 | 资料齐备 |
| `python -X utf8 -`（准备前快照） | 0 | 保存 Git/文档和 423 项保护指纹 |
| `python -X utf8 output/reference016/phase-d/capture_real_pdf.py prepare`（首次） | 1 | BM25 缓存缺失，原失败保留，模型 0 次 |
| `python -X utf8 -`（原 BM25 资源下载/指纹验证） | 0 | 官方词表与历史 hash 相同 |
| `python -X utf8 output/reference016/phase-d/capture_real_pdf.py prepare`（恢复准备） | 0 | 16 Point/384 维/7 结果，模型 0 次 |
| `python -X utf8 output/reference016/phase-d/capture_real_pdf.py supervise` | 1 | Q1 质量失败后正常停止；不是超时或崩溃 |
| `python -X utf8 output/reference016/phase-d/capture_real_pdf.py audit` | 0 | 运行结束时 423 项保护无差异 |
| `python -X utf8 -`（最终静态收尾核对） | 0 | 冻结输入、计数、证据/旧失败文本和计划内文档差异一致 |

采集子进程命令/进程标识/退出状态见 [command.json](../../output/reference016/phase-d/formal-pdf-20261028-01/command.json)，进程已结束，900 秒 supervisor 未触发。原始输出见 [capture.log](../../output/reference016/phase-d/formal-pdf-20261028-01/capture.log)。项目 extensions.yml 不存在，无扩展 hooks；审阅清单的 3 个旧 A 工程标记保持只读，不冒称本轮重新通过 A。

保护证据：[protected-before.json](../../output/reference016/phase-d/formal-pdf-20261028-01/protected-before.json)、[运行后核对](../../output/reference016/phase-d/formal-pdf-20261028-01/protected-after.json)、[最终收尾核对](../../output/reference016/phase-d/formal-pdf-20261028-01/closure-verification.json)。运行前后 423 项完全一致；报告阶段其中仅功能 CURRENT_FAILURES.md 计划内增加 D 失败，422 项继续相同，旧 B/R 失败正文逐字保留。根目录旧失败、旧报告、配置和正式数据均保持。

## 限制与停止点

- 本轮是真实模型、真实 ONNX/BM25、既有测试 PDF 索引的 Graph/pipeline 测试；没有 fake/mock 问答、pytest/npm 或 Judge。此前工程通过不作为本轮成绩。
- 没有重跑上传/PDF 解析、HTTP/认证或浏览器；源 PDF 是项目测试文档，不外推到真实业务 PDF。Parent 和历史摘要模型本题未调用，不宣称已覆盖。
- Q2–Q4 因首题失败未运行；Q5–Q15 不在本阶段范围，没有追加请求。原合成 B 通过和历史其他失败不改判。
- T027–T029 有本批交付证据，仅表示按失败停止协议完成本阶段，不表示四题全测、质量通过或用户验收。

后续可单独开展 D-Q1 的遗漏定位与修复，区分压缩、研究和聚合各节点，再另批首答复验；本报告不执行该工作或恢复后续题目。**报告后暂停，等待用户验收。**
