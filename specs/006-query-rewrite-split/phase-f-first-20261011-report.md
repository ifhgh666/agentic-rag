# 006 阶段 F 首次真实报告：Q16 入口失败后停止

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-11。范围：沿用用户已授权的 F（T033–T035），用户随后补充本机登录输入，解除原待测轮的认证输入阻塞。使用项目内 [speckit-implement](../../.agents/skills/speckit-implement/SKILL.md) 恢复同一阶段。原 [F 待测报告](phase-f-report.md) 不覆盖，E 的失败结论不变。

**首次批次只提交 Q16 一次：入口验收 failed，完整答案 not_verified；按顺序失败停止，C-UV 和比较题均 not_run。Q16 本次保留了 245 V / 400 ms，最终过压判断与恢复核心结论正确，但恢复子问丢共同条件，不能据此宣布 F 或 006 验收通过。报告后暂停，等待用户验收。**

## 实际请求与独立验收

| 题目 | 实际提交 | 入口 | 完整答案 | 端到端耗时 |
|---|---|---|---|---:|
| Q16 | 原题、新线程、首次一次 | failed | not_verified | 217.046 秒 |
| C-UV | 未提交 | 未评估 | 未评估 | 不适用 |
| COMPARE | 未提交 | 未评估 | 未评估 | 不适用 |

原 Q16：设备输入电压为 245 V，持续 400 ms，会触发什么保护？之后如何恢复？

请求 ID：`[运行标识已移除]`。线程：`rw-f-bffb155918084720b653ab37f0abeb33`。仅发送 `question/thread_id/action=new_question`；没有标准答案、历史或提示输入。首次 SSE 返回 `completed / model_answered`，这表示程序执行终态，不等于人工质量通过。

入口第一次可见输出：

```json
{
  "is_clear": true
}
```

第一问没有发生旧的 `400→40或` 失真。但第二问仍是依赖前文的省略问，没有设备场景、245 V / 400 ms 共同条件或条件性恢复关系，违反 FR-004/FR-006 与计划的相关子问承载要求，因此入口人工验收 **failed**。主图仍把原题传到下游，最终模型能够使用原题；这不能抵消子问自身缺失共同条件的入口失败。

最终答案正确比较 `245>242 V`、`400>300 ms`，判断过压保护；恢复核心内容为“电压恢复正常后等待 30 秒自动恢复”。人工核对依据为现有 [提取文档保护表](../../backend/data/documents/[运行标识已移除]/extracted.md) 第 105–108 行，未将表或预期结论发送给被测模型。文档的额定输入电压为 220 V，正常范围 198–242 V；答案另将 242 V 称作“额定值”，措辞不准确，不能把它当成额定电压事实。

公共核验卡为 `evidence_status=found / citation_status=issue_found`，数值与完整性仍是在线 `not_evaluated`。两份重复来源都为页码未知，完整答案人工状态为 **not_verified**，没有将正确数值结论或已有来源名称当成全部引用要求通过。当前引用核验器要求逐字引文和具体来源页码匹配；本轮只记录该问题，不修复引用或解析逻辑。答案还有未被询问的 A/B 比较说明，原文保留，没有删改为精简版本。

## 原始证据与用量

批次：`output/query-rewrite-v1/e2e-first-20261011-01/`，目录拒绝覆盖。

- [冻结清单](../../output/query-rewrite-v1/e2e-first-20261011-01/manifest.json)：固定三题、夹具/代码哈希、模型身份、非敏感预算与正式内容指纹。
- [首次请求](../../output/query-rewrite-v1/e2e-first-20261011-01/Q16.attempt.json)、[原始 SSE](../../output/query-rewrite-v1/e2e-first-20261011-01/Q16.sse.txt)、[完整原始答复和模型/工具输出](../../output/query-rewrite-v1/e2e-first-20261011-01/Q16.raw.json)。
- [分别验收及人工依据](../../output/query-rewrite-v1/e2e-first-20261011-01/Q16.review.json)、[实际批次汇总](../../output/query-rewrite-v1/e2e-first-20261011-01/summary.json)、[命令和退出记录](../../output/query-rewrite-v1/e2e-first-20261011-01/execution.json)。
- [SSE 文件完整性补充](../../output/query-rewrite-v1/e2e-first-20261011-01/sse-file-integrity.json)：采集器保存的是 `httpx` 解码文本，Windows 文本写入将96个LF变为CRLF，磁盘字节哈希与原捕获文本哈希不同；统一换行后的文本哈希与原记录一致。两种哈希分别保留，原SSE/raw文件没有重写，不能把它说成逐字节网络传输备份。
- 本机既有详细 trace 仅按准确请求 UUID 关联；原始文件哈希 `41b1b51b148c865d94b6c3db9193c2c0a2c448831f16a29ef2375fa46db578fd`。采集证据只复制许可的可见模型输出和工具字段，不复制完整提示词或私有推理，不新增调试 API。

| 项目 | 实际值 |
|---|---:|
| 入口模型调用 / 耗时 | 1 / 26.486 秒 |
| 全部模型调用 | 6：入口 1、分支循环 4、汇总 1 |
| 工具调用 | 2，均为模型选择的 `search_child_chunks` |
| 模型调用分支计数 | B1=2、B2=2 |
| 工具分支计数 | B1=1、B2=1 |
| 云端 / Judge / 自动重试 | 0 / 0 / 0 |
| 实测输入 / 输出 / 总 Token | 7485 / 890 / 8375，`usage_source=provider` |
| 缓存命中 | 0 |
| API 用量事件请求耗时 | 216.938 秒 |
| 客户端请求端到端耗时 | 217.046 秒 |
| 模型各次耗时之和 | 277.169 秒；分支并行存在重叠，不是请求墙钟耗时 |
| 整批含保存、读取和人工审阅耗时 | 290.523 秒；不作为单题模型等待耗时 |

终态在 300 秒以内产生；最长单次可见模型等待 106.053 秒，未超 120 秒。此正常请求没有触及 300 秒，**不能证明真实到期截断已实测**。SSE 沿用完成后轨迹回放，不是逐节点实时推送。

## 本轮文件与保护检查

本轮不修改生产代码、采集工具、测试、前端、模型提示或配置，不新增模型/工具/Judge 调用。只保存真实首次证据、更新 README/CURRENT_STATUS 与 006 当前进度导航、追加失败事实，并新增本报告。

`CURRENT_FAILURES.md` 仅在原文件末尾追加 006 F 新事实，原始字节前缀、005 旧失败和耗时均保留。[追加前大小与哈希](../../output/query-rewrite-v1/e2e-first-20261011-01/failure-append-baseline.json)可核对追加性质；005 T018 不自动完成。

核对 [恢复保护基线](../../output/query-rewrite-v1/e2e-first-20261011-01/resume-audit-baseline.json)与[最终审计](../../output/query-rewrite-v1/e2e-first-20261011-01/artifact-audit.json)：生产代码、夹具、采集工具/测试和所有既有阶段报告保持原哈希；失败清单原前缀保留；`.env` 不变。正式内容 11 项指纹（包括 6 项 index/Qdrant 文件）与首次 manifest 前后相同，未重建、迁移、增删 PDF 或修改索引。

原 F 准备轮的 **39 项 HTTP stub/fake 工程测试通过**仍是历史工程结果；本次无代码变更，不重复全量工程回归，也不将这些测试作为真实问答质量。原红/绿失败记录和 A–E/F 待测报告均保留。

## 实际命令、认证与退出状态

| 工作目录 | 实际命令/操作 | 退出状态与结果 |
|---|---|---|
| 仓库根 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；当前006；需求检查清单16/16；extensions.yml不存在，无前后钩子 |
| 仓库根 | 读取正常代理 `/api/health` 与进程归属 | 0；5173健康200、`index_ready=true`，沿用已有后端/前端 |
| backend | 下列正常 API 首次采集命令 | **1**；Q16人工入口failed后按协议停止，另两题未提交 |
| 本机认证 | getpass隐藏stdin → 正常 `/api/auth/login` → 结束正常 `/api/auth/logout` | 登录200、注销204；响应/凭据没有写入参数、文件或报告 |
| 仓库根 | `D:/newsoft/python.exe output/check_query006_phase_f_first.py` | 0；只读哈希、原始状态、UTF-8和本地链接核对，详见最终审计 |
| 仓库根 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

```powershell
# cwd=C:\path\agentic-rag\backend
# 仅指定输出编码，不修改模型配置
$env:PYTHONIOENCODING='utf-8'
D:/newsoft/python.exe -m scripts.capture_query_rewrite_e2e --url http://127.0.0.1:5173 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/e2e-first-20261011-01 --stop-on-failure
```

真实模型保持 Ollama `qwen3:4b-instruct`、temperature0、seed42，digest 与 E 相同；单/多总模型8/12、入口1、工具16，整请求300秒、单模型120秒，窗口4096/输入3072/输出768/安全余量256。Dense仍为fastembed，实际 `sparse_offline_fallback=false`，不声称首次检索完全断网。

认证输入通过本机getpass隐藏stdin使用，没有命令行明文凭据、写入.env、重设密码或绕过认证。采集终端会话54182已退出1；服务启动日志记录仅一次聊天POST，后续只有正常注销。后端PID52988、前端PID57652保持可用，没有重启原服务、清空会话或后台续测。

辅助读取曾因误用基线字段名出现一次KeyError，随后读取实际键成功；一次终端中文输出因编码显示异常，显式UTF-8后重读确认原始JSON正文正确。这些只读辅助问题没有改动真实答复、重试问题或修改知识库。

首次哈希审计Python退出1：将捕获文本哈希误当作磁盘字节哈希，发现上述Windows换行差异；同一Shell后续只读命令完成使最终Shell状态为0，不能据此称该次审计通过。[失败记录](../../output/query-rewrite-v1/e2e-first-20261011-01/artifact-audit-attempt-01.json)保留；随后分别核对文件字节和统一换行文本，通过最终审计。采集工具源码仍保持首次manifest的版本，未在失败后修工具重跑。

只读审计工具的首次运行也退出1：将保护基线中描述人类任务授权的 `authorization` 字段误判为HTTP认证头。[记录](../../output/query-rewrite-v1/e2e-first-20261011-01/artifact-audit-attempt-02.json)保留；仅为该固定非敏感授权文字增加精确豁免，Token/密钥/完整提示字段仍禁止，未修改原始采集证据。

## 限制、任务与下一步

- T033 完成；T034 保持未勾选（1题首次入口失败，2题未运行）；T035交付本真实报告。006真实质量未通过，E T031及005 T018不自动完成。
- C-UV 的欠压推导、比较题和后续入口案例未评估。Q16没有复现旧数字失真，但只是一道题一次结果，不能声称模型始终保真或历史失败已经全部解决。
- 已知正式PDF含推荐问答，本批次不作为无泄漏检索质量总评分；没有标准答案输入，也没有新增知识库。
- 下一步可在明确授权后诊断/修复共同条件与恢复依赖、引用问题，使用新目录另批次复验；不能覆盖本首答、自动续跑后两题、改预算/模型、恢复005 D或30题评测。

**报告后暂停，等待用户验收。**
