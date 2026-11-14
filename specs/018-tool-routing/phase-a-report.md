# 018 阶段 A 聊天分流

日期为 2026-11-14。T001–T007 工程完成，等待用户验收。

## 已实现

- 后端图的首个模型调用判断是否需要知识库。普通对话通过未绑定检索工具的模型生成，纳入会话历史并通过原有 SSE 输出。
- 文档问题先改写并判断检索条件。信息不足时模型直接提出一条简短的补充问题，现有会话动作支持继续、取消或另起问题。
- [图入口](../../backend/app/rag/graph.py)、[模型节点](../../backend/app/rag/nodes.py)、[公共事件](../../backend/app/core/pipeline.py)及[前端进度](../../frontend/src/features/chat/controller.ts)沿用原有工具、接口和会话边界。
- 测试覆盖中文问候、索引不可用、上下文跟进、文档来源、短中文澄清、续答和分流失败。冻结参考文件仍按原哈希校验。

## 验证记录

| 工作目录 | 命令 | 退出与结果 |
|---|---|---|
| 根目录 | `pwsh -NoProfile -File .specify/scripts/powershell/setup-plan.ps1 -Json` | 0，定位 018 规格及计划 |
| 根目录 | `pwsh -NoProfile -File .specify/scripts/powershell/setup-tasks.ps1 -Json` | 0，定位 018 设计文档与任务模板 |
| 根目录 | `pwsh -NoProfile -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0，需求清单 5/5 |
| 根目录 | `python -X utf8 output/reference016/phase-a/run.py tool-routing-focused-20261113-02` 加实际定向参数 | 0，49 通过。见[命令](../../output/reference016/phase-a/tool-routing-focused-20261113-02.json)和[日志](../../output/reference016/phase-a/tool-routing-focused-20261113-02.log) |
| 根目录 | `python -X utf8 output/reference016/phase-a/run.py tool-routing-full-20261114-02` | 1，729 通过、2 既有断言失败、24 跳过、2 排除。见[日志](../../output/reference016/phase-a/tool-routing-full-20261114-02.log)和[隔离记录](../../output/reference016/phase-a/tool-routing-full-20261114-02-guard.json) |
| frontend | `npm.cmd test` | 0，16 文件、89 通过。[日志](../../output/tool-routing-018/frontend-test.log) |
| frontend | `npm.cmd run build` | 0，保留现有大包体警告。构建使用工作区临时目录。[日志](../../output/tool-routing-018/frontend-build.log) |
| 根目录 | `git -c core.safecrlf=false diff --check` | 0 |

首次[定向日志](../../output/reference016/phase-a/tool-routing-focused-20261113-01.log)和[全量日志](../../output/reference016/phase-a/tool-routing-full-20261113-01.log)保留了旧调用计数断言失败。加入分流后，新文档请求多一次模型决策，最终断言仍逐项核对各节点实际调用。完整回归剩余失败来自既有旧提示词断言，分别位于 `test_query_rewrite_v1.py` 和 `test_v4_query_analysis.py`。

本阶段使用脚本模型、模拟 SDK HTTP 响应及隔离索引。真实模型路由质量和正式题库未复测。当前运行服务仍使用上次启动时的后端版本，需重启后才会加载新流程。后续验收可按[验证指南](quickstart.md)核对普通问候、明确文档问题和澄清续答。

**报告后暂停，等待用户验收**。
