# C阶段复验报告：第一题仍失败，后续测试暂停

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-09。功能：005-model-driven-agent-loop。分支：`codex/model-driven-agent-loop`。

用户以“继续”恢复C阶段T018。本轮提交第一道原题一次，仍在分析环节失败。按照阶段失败暂停规则，第二道题未提交，D阶段未启动。**C阶段尚未完全验收，T018仍未完成。** 此报告后暂停，等待用户验收与后续指令。

## 1. 本轮范围与准备

- 完整读取项目AGENTS、README、当前规格/计划/任务及历史失败记录，使用项目内[speckit-implement](../../.agents/skills/speckit-implement/SKILL.md)流程核对C阶段范围。前后实施钩子及检查清单目录均不存在。
- 本地前后端原先已停止，恢复网站供复验使用。后端PID为50436，前端PID为41188；Ollama进程沿用原服务。健康检查正常、索引就绪。恢复服务后的会话与缓存为空。
- 维持整次请求最大300秒、单次模型等待最多120秒；原生工具协议、单/多分支8/12次模型预算、上下文4096、输入预算3072、输出预留768均未提高。
- 模型为`qwen3:4b-instruct`。提交前Ollama没有已加载模型，本次是冷启动；加载后报告context_length=4096、size_vram=0。
- 采集脚本补充两个记录保护：拒绝覆盖已有输出；API外层到期未提供usage时仍保存真实事件，未知用量不写成零。这只改采集脚本，未修改生产RAG逻辑。

## 2. 第一题真实复验结果

[真实运行原文已移除]

正常登录后通过前端代理API提交，新独立会话，无标准答案、无历史注入、无后续澄清或自动重试。

| 项目 | 结果 |
|---|---|
| 题目标识 | Q16独立冒烟，不能替代正式30题会话成绩 |
| 请求ID | `[运行标识已移除]` |
| 实际模型调用ID | `model-67234c2547914fc182727d8e00e605c2` |
| 平台终态 | failed / constraint_mismatch / runtime_guard |
| 端到端耗时 | **32.644秒** |
| 模型调用耗时 | 32.573秒 |
| 模型 / 工具 / 云调用 | 1 / 0 / 0 |
| Token | 822输入、77输出，总计899；provider实测 |
| 最终答案 | 空，未进入检索 |
| 正式知识库 | 11个文件的前后指纹一致 |

模型返回的两个分析问题为：

```json
[
  "设备输入电压为 245 V，持续 40或 ms，会触发什么保护？",
  "如何恢复该保护触发后的状态？"
]
```

题设`400 ms`再次变成`40或 ms`，因此被约束校验拦截。平台提示：“无法可靠理解该问题，请换一种说法后重试。” 先前加强逐字复制数字的提示尚未解决这一真实失败，不能将其标为已修复。校验阻止错误题设继续执行，未放行数字错误或改用程序规则搜索。

原始记录：[本轮Q16采集](../../output/loop005-phase-c-recheck-20261009-Q16.json)。完整本地诊断路径及SHA-256写在local_trace字段中，指纹核对一致。原31.136秒的首次失败记录继续保留。

## 3. 第二题与超时验证状态

[真实运行原文已移除]

**本轮未运行。** 第一项顺序验证失败后，暂停后续题目，未生成新的C-UV采集文件。此前约32.7分钟的失败记录保留，不能修改成最新300秒配置下的结果。

本轮第一题在32.644秒结束，仅证明这一请求在上限内正常返回失败；它没有走到模型/请求截止，不能据此证明真实300秒到期截断或195 V/300 ms场景回答已通过。此前425项自动化回归验证工程行为，仍不能替代这些真实验收项。

## 4. 实际命令与交付

在backend目录运行，密码使用隐藏交互输入，不写入命令行或文件：

```powershell
D:/newsoft/python.exe -m scripts.smoke_phase_c_platform --help
D:/newsoft/python.exe -m py_compile scripts/smoke_phase_c_platform.py
D:/newsoft/python.exe -m scripts.smoke_phase_c_platform --case Q16 --output ../output/loop005-phase-c-recheck-20261009-Q16.json
```

脚本帮助与编译检查通过；真实复验命令退出码1，采集结果passed=false。本轮没有重跑全量自动化测试，最近425项通过记录属于[此前超时修改验证](timeout-300s-report.md)。

主要变更文件：`backend/scripts/smoke_phase_c_platform.py`、本报告、根目录CURRENT_FAILURES.md、tasks.md及AGENTS交接信息。未重建正式索引、下载模型、切云、提交或推送Git。

网站继续运行在[本地问答台](http://127.0.0.1:5173/#/chat)。[后端启动记录](../../output/loop005-phase-c-recheck-backend-errors-20261009.txt)、[前端启动记录](../../output/loop005-phase-c-recheck-frontend-startup-20261009.txt)。

## 5. 未通过项与停止点

- C-FAIL-001：原题已复验，数字失真仍发生，未解决。
- C-FAIL-002：本轮未复验；实际期限和正确场景答案仍待确认。
- T018仍保留未完成状态。后续范围为C阶段的分析数字失真处理及剩余真实验证，需用户验收后明确指示；不自动启动D或30题评分。

[AGENTS.md](../../AGENTS.md)要求阶段报告后暂停；[实施技能](../../.agents/skills/speckit-implement/SKILL.md)明确要求 **“Halt execution if any non-parallel task fails”**。第一项顺序验证失败，因此本次停止后续测试，交付报告后等待用户。
