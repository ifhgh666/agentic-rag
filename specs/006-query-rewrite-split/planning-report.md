# 006 规划交付报告

日期：2026-10-10。状态：计划待审阅，实施未开始。

## 授权与本轮产物

用户要求依据《问题改写与拆分模块设计方案 V1》先生成计划，不执行。本轮使用项目内 speckit-specify、speckit-plan、speckit-tasks 生成文件；speckit-plan 要求的研究由两名只读研究代理完成，没有运行模型或业务测试。最终一致性复核使用 speckit-analyze，只读结论在本轮交付说明中报告。

| 文件 | 用途 |
|---|---|
| [source-design-v1.md](source-design-v1.md) | 用户原设计完整副本，按 SHA-256 核对一致 |
| [spec.md](spec.md) | 四个用户故事、18项功能要求、7项验收标准 |
| [checklists/requirements.md](checklists/requirements.md) | 规格完整性检查；不表示功能已通过 |
| [plan.md](plan.md) | 技术方案、模型/程序职责、A—F六阶段与停止点 |
| [research.md](research.md) | 当前调用链、三字段兼容与设计取舍依据 |
| [data-model.md](data-model.md) | 原题、子问题、待办、缓存与运行元数据 |
| [contracts/query-rewrite.md](contracts/query-rewrite.md) | 严格三字段、动作、失败与事件契约 |
| [acceptance-matrix.md](acceptance-matrix.md) | 24组工程/真实入口/端到端场景 |
| [quickstart.md](quickstart.md) | 后续各阶段拟执行命令，本轮未运行 |
| [tasks.md](tasks.md) | 35项实施任务，全部未勾选 |

## 计划中的重点变化

- 复用现有一次入口模型调用，完整单问保留原文；必要补全、独立需求拆分和清晰度判断在同一个节点内完成。
- 原题同时传给现有 Agent Loop 和最终汇总，普通历史保存真实用户输入，避免改写错误再次进入历史。
- 拟取消入口数字/型号来源不匹配的硬拦截；保留基础结构、预算、工具与引文检查。此取舍不保证模型不会改错，真实验收出现 400→40 仍失败。
- 三字段无法表达旧关系分类：有待办且未选动作时，先请用户明确继续补充或开始新题；不新增分类模型或程序文本猜测。
- 沿用零自动重试、300秒整次请求期限和当前本地模型。工程检查、真实入口与完整答案验收分别记录。

## 本轮实际命令与验证

工作目录均为仓库根目录；Python 使用 `D:/newsoft/python.exe`。表中生成器与校验器属于本轮文档工具，不是产品实现。

| 实际命令/操作 | 最终退出状态 | 说明 |
|---|---:|---|
| `git status --short`、`git diff`，另查未跟踪文件 | 0 | 读取既有修改，保存基线；未还原或清理 |
| 按 specify 技能解析规格模板、创建006目录并复制源文档 | 0 | 沿用现有 Git 分支，未新建分支 |
| `D:/newsoft/python.exe output/generate_query_rewrite_plan_20261010.py spec` | 0 | 生成规格和检查清单 |
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 实际执行计划初始化，再填写模板 |
| `D:/newsoft/python.exe output/generate_query_rewrite_plan_20261010.py design` | 0 | 生成计划、研究、数据模型、契约及验收材料 |
| `powershell.exe -NoProfile -File .specify/scripts/powershell/setup-tasks.ps1 -Json` | 0 | 实际解析任务模板，结果保存在 output |
| `D:/newsoft/python.exe output/generate_query_rewrite_plan_20261010.py tasks` | 0 | 生成35项任务 |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks` | 0 | 返回006绝对路径与所需文档；前置定位后恢复005导航 |
| `D:/newsoft/python.exe output/validate_query_rewrite_plan_20261010.py` | 0 | 文档 UTF-8、链接、任务格式/覆盖、源副本及既有文件保全检查 |

保留的工具问题：首次任务初始化外层命令误用了旧 `$LASTEXITCODE`，导致外层退出1；改为子进程调用后确认脚本退出0。首次文档校验的正则未正确匹配紧接中文的需求编号，产生4项假缺口；修复校验器后重跑退出0，保留[首次校验记录](../../output/query-rewrite-plan-20261010/validation-first-check.json)。这些不是模型或业务测试结果。

最后前置检查曾因运行时目录没有 `powershell.exe`、子进程的脚本签名策略分别退出1，尚未运行检查正文；改用明确路径和仅对子进程生效的参数后退出0。每次均在 finally 中恢复原导航，未修改系统执行策略。

最终文档检查详情：[validation.json](../../output/query-rewrite-plan-20261010/validation.json)。25项要求均有任务覆盖，35项全部未执行；24组验收场景连续编号。313份既有工作区文件与基线哈希一致；用户源文档副本哈希一致；原005功能指针恢复，Git 分支仍为 `codex/model-driven-agent-loop`。基线见 [baseline.json](../../output/query-rewrite-plan-20261010/baseline.json)。技能脚本临时定位006仅用于规划，不能作为实施授权。

没有运行 pytest、前端测试/构建、真实模型调用或问答评测；没有启动/重启服务，没有修改产品代码、正式知识库、索引或 `.env`。不宣称历史两题已修复。005 C真实验收未通过、T018未完成、D未启动的状态与失败记录保持原样。

## 后续范围与停止点

| 阶段 | 范围 | 阶段结束 |
|---|---|---|
| A | 严格入口契约、完整单问、原文历史和缓存 | 保存 phase-a-report.md 后暂停 |
| B | 上下文补全、澄清、明确动作与前端选择 | 保存 phase-b-report.md 后暂停 |
| C | 独立需求拆分、共同条件与原题完整汇总 | 保存 phase-c-report.md 后暂停 |
| D | 可观测性、接口兼容、安全和工程回归 | 保存 phase-d-report.md 后暂停 |
| E | 最多17次真实入口首次采集 | 首次顺序失败停止，保存报告后暂停 |
| F | 两道历史失败题及一题比较的正常API补测 | 首次顺序失败停止，保存报告后暂停 |

本轮到规划交付即结束。用户后续对整份计划说“执行”仅启动A；完成一个获准阶段后必须保存阶段报告并结束本轮，不自动进入下一阶段。

**报告后暂停，等待用户验收。**
