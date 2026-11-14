# 016 C：框架审阅收尾

日期：2026-10-28（America/Phoenix）。用户在 [框架审阅](phase-framework-review-20261028-report.md)列出 F1/F2 后明确“继续”，本轮仅修复这两处，按项目 Spec Kit 补充同一功能的 C 阶段（tasks Phase 8/T024–T026）。

**结论：两处收尾均已完成，待用户验收。产品代码只移除闲置 ContextBuilder 导入名和实例化语句，架构指南已对应当前调用链。仅做静态核对，没有运行测试、模型或服务。报告后暂停，等待用户验收。**

## 完成改动

- F2 已修复：[backend/app/main.py](../../backend/app/main.py) 不再导入 ContextBuilder，也不再创建未被使用的 context_builder。该类构造原本只保存两个引用；独立类和旧消费方完整保留，没有改变新图、模型或知识检索实现。
- F1 已修复：[docs/repository-guide.md](../../docs/repository-guide.md) 更新正常在线模块地图、装配、主图/研究子图、checkpoint 会话、工具和公开交付说明及 Mermaid 调用图。ModelCallRunner、旧 QueryAnalyzer/AnswerGenerator/ConversationMemory 等单列为独立旧能力；删除把旧共享预算/截止/核验链写成当前正常路径的说明。当前参考常量、DeepSeek 传输策略和来源匹配限制均按现有源码/契约描述。
- 维护 plan/tasks 的 C 授权、范围和状态，更新 docs/CURRENT_STATUS 导航。没有新模型、接口、配置项、依赖或框架功能；未修改旧审阅、阶段报告或失败记录。

## 静态核对与实际命令

工作目录：`C:\Users\ifhgz\Desktop\agentic-rag`，既有分支保持。项目 `.specify/extensions.yml` 不存在，没有前后 hooks；requirements 清单的三项旧 A 工程标记保持只读，当前继续授权覆盖 F1/F2 收尾。状态和接口复用既有契约，无新实体或技术选型，因此没有扩展研究或测试阶段。

| 实际命令 | 退出码 | 结果 |
|---|---:|---|
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 复用 016，补充单阶段 C 范围 |
| `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0 | 读取任务模板，追加 T024–T026，不重排旧任务 |
| `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0 | 当前功能资料完整 |
| `D:\newsoft\python.exe output/reference016/snapshot_cleanup.py` | 0 | 保存改前文件/Git与 69 项保护哈希，凭据只取 hash |
| `D:\newsoft\python.exe output/reference016/verify_cleanup.py` | 0 | AST、精确差异、UTF-8、6 个指南相对链接与保护项核对通过；只用标准库解析文件，未导入应用 |
| `git diff --check -- backend/app/main.py docs/repository-guide.md` | 0 | 无空白格式问题 |
| `rg -n 'ContextBuilder|context_builder' backend/app/main.py backend/app/knowledge/retrieval.py` | 0 | main 已无引用，独立类仍在 retrieval.py |

AST 核对结果：从改前 main 语义树移除一个 ContextBuilder 导入别名及一个闲置赋值后，与当前 main 的语义树完全一致，没有其他 AST 变化。69 项原保护文件中只发生计划内 main.py 变化，其余 68 项不变，包含其他产品源码、独立 ContextBuilder、模型配置及原报告/失败记录。正式知识库未读写或重建。

证据：[static-verification.json](../../output/reference016/framework-cleanup-20261028-01/static-verification.json)、[精确差异](../../output/reference016/framework-cleanup-20261028-01/cleanup.patch)、[改前哈希](../../output/reference016/framework-cleanup-20261028-01/before-hashes.json)，同目录 before-files 为改前文件。

这些结果仅为静态范围与文档核对，不称为新的运行测试通过。没有新增测试文件，没有执行 pytest/npm/真实模型/Judge，没有应用导入、服务启动/重启、正式数据操作、提交或推送。A/B/R 的历史通过/失败保持原记录，未作为本轮重新运行的结果。

## 状态与停止点

F1/F2 均关闭，T024–T026 完成本次工程交付，原 T001–T023 状态保持，待用户验收。原审阅报告中的“尚未修复”保留其当时事实，本报告记录后续修复结果。当前范围没有未完成收尾项，也没有自动新增的下一阶段。

**报告后暂停，等待用户验收。**
