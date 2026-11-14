# P1 规格整理阶段记录

日期：2026-10-21（America/Tijuana）。

## 目标、授权与停止点

用户明确认可本次 P1 使用 Matt 流程替代 Spec Kit；本轮按 `/to-spec` 整理已经确认的 Q1–Q3。本例外不改写全局 AGENTS 或宪章。初稿交付后用户明确认可测试 seam，本轮随后完成规格发布；不拆任务、不修改产品代码、不运行模型或工程测试。

## 当前交付

- `spec.md`：按 Matt 模板整理 Problem Statement、Solution、21 条 User Stories、Implementation Decisions、Testing Decisions、Out of Scope 与 Further Notes。
- GitHub 规格：[P1：动态证据预算与上下文装载 #1](https://github.com/ifhgh666/agentic-rag/issues/1)，状态 OPEN，标签 ready-for-agent。
- 本记录：记录初稿、测试 seam 确认、发布与回读核对结果。
- 本地目录用于审阅与阶段归档；未运行 Spec Kit 脚本，未切换 `.specify/feature.json`，未修改既有规格、历史失败、产品配置或用户数据。

## 实际核对与退出状态

| 操作 | 结果 |
|---|---|
| PowerShell `Get-Content -Encoding UTF8` | 成功读取根代理说明、README、项目宪章、tracker/labels/domain 约定、to-spec 技能、相关导航/评测规范及源码/测试片段 |
| `git remote -v` | 退出 0；origin 为 `https://github.com/ifhgh666/agentic-rag.git` |
| `gh repo view --json nameWithOwner,url` | 退出 0；目标仓库 `ifhgh666/agentic-rag` |
| `gh issue list --repo ifhgh666/agentic-rag --state all --limit 60 --json number,title,state,labels,url` | 退出 0；返回空列表，未发现既有规格 Issue |
| `gh label list --repo ifhgh666/agentic-rag --search ready-for-agent --json name` | 退出 0；确认 ready-for-agent 标签存在 |
| `git status --short`、`git diff --stat`、定向 `git diff` | 退出 0；核对既有大量修改和未跟踪文件，未还原或清理。Git 提示两处既有 pytest 临时目录不可读取 |
| `rg` 核对现有运行入口、工具参数与相关测试 | 找到 AgentGraphService.run、ModelAgentLoop.run、SSE 契约及容量/引用/截止测试先例；一个包含尚不存在 `.scratch` 的可选搜索退出 2，未创建该目录 |
| PowerShell UTF-8 文档重新读取与结构核对 | 退出 0；7 个必需章节齐全、21 条用户故事、无替换乱码字符、无代码片段；草稿明确标记未发布，当前功能指针仍指向 009 |
| `git status --short -- specs/010-context-admission` | 退出 0；仅显示本轮新增文档目录未跟踪；没有提交或推送 |
| 发布前再次读取 AGENTS、README、本地规格/阶段记录与 tracker/label 约定 | 成功；确认仅发布本规格，不进入拆任务或实施 |
| `gh repo view --repo ifhgh666/agentic-rag --json nameWithOwner,url` | 首次参数写法报 unknown flag: --repo；同一命令单元的后续只读命令仍成功，不能把单元末尾退出 0 当成此命令成功 |
| `gh repo view ifhgh666/agentic-rag --json nameWithOwner,url` | 修正为位置参数后退出 0，核实目标仓库一致 |
| `gh issue create --repo ifhgh666/agentic-rag --title 'P1：动态证据预算与上下文装载' --body-file <本地规格绝对路径> --label ready-for-agent` | 退出 0；创建 Issue #1，正文从 UTF-8 文件完整提交，没有提交或推送仓库代码 |
| `gh issue view 1 --repo ifhgh666/agentic-rag --json number,title,state,labels,body,url` | 退出 0；状态 OPEN，标签 ready-for-agent；将回读正文与本地定稿统一换行、忽略末尾换行后逐字符比较，一致，正文 5262 字符 |

## 初稿停点与确认结果

to-spec 明确要求在规格发布前向用户核对测试 seam。初稿建议以 AgentGraphService.run 为主，SSE 契约为必要补充，ModelAgentLoop.run 只承担聚焦覆盖；具体内容已写入规格。

初稿交付时测试 seam 尚未确认，故当时没有创建 GitHub Issue。用户随后回复“认可”，确认这些测试入口；已将本地规格更新为定稿并发布 Issue #1，随后核对正文、状态及标签。当前规格整理与发布阶段已完成，待用户验收；未发布子任务。

没有运行 pytest、前端测试、编译或真实模型；没有启动服务或访问正式 Qdrant。既有质量与工程失败未改判。

## 后续范围

用户验收并明确指示继续后，下一阶段可按 Matt `/to-tickets` 提出有依赖关系的任务切分，待用户认可切分后再发布任务。本轮不自动进入该阶段。ready-for-agent 是 tracker 的规格就绪标签，不等于本聊天获准实施。

报告后暂停，等待用户验收。
