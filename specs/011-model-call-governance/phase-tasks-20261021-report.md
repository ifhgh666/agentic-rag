# P2 任务拆分阶段报告

日期：2026-10-21（America/Tijuana）。状态：**任务拆分完成，全部工程任务待实施。**

## 范围与执行结果

上轮明确的下一步是任务拆分，用户随后要求“执行”。本轮按该下一步执行项目内 [speckit-tasks](../../.agents/skills/speckit-tasks/SKILL.md)，生成可执行清单，没有将此轮扩展为产品重构。

完成 [tasks.md](tasks.md)，共 39 项，全为未勾选：

| Phase | 阶段/故事 | 数量 | 目标 |
|---|---|---|---|
| 1 | A / US2 | 10 | 诊断故障隔离，可独立交付的 MVP |
| 2 | B / US1 核心 | 14 | runner、真实 adapter guard、loop/汇总/修复 |
| 3 | C / US1 全部用途 | 9 | 分析、普通生成、旧改写、摘要及独立上下文 |
| 4 | D / 跨故事 | 6 | 组合交付、完整隔离回归与收尾 |

US2 10 项、US1 23 项、跨故事 6 项；4 项标为 [P]，仅表示阶段内不同文件的技术并行机会，不构成自动多代理、跨阶段或并发全套测试授权。没有启动子代理。

任务包含测试 seam、行为证据、实现文件、原字段约束、前置关系、用量/隐私检查和阶段报告。按照已交付计划保留 Phase 1=A 等映射；模板初始化和基础准备并入对应阶段，不另建横向工程阶段或改变故事编号。

只更新 [spec.md](spec.md)、[plan.md](plan.md)及[需求清单](checklists/requirements.md)的阶段状态/导航，不改业务需求、技术契约或旧阶段报告。功能指针保持 011；产品代码、测试源码、依赖、.env 和正式数据未变。

## 依赖与验收方式

默认交付顺序 A→B→C→D。A、B 技术上分别有独立演示价值；C 技术上依赖 B，D 依赖 A/C。每阶段必须完成相应实际验证并保存报告后停止。后续笼统执行本计划仅进入首个尚未完成的 A（T001–T010）。

US2 的独立验收是诊断关闭/成功/失败/慢写的配对问答、单终态、历史一致及文件不覆盖。US1 的独立验收是各用途的容量/预算/期限/异常矩阵、格式回退重检及一次逻辑计费。MVP 为 A，不需要先完成全部调用治理或真实模型复验。

## 实际命令与文档检查

cwd：C:/Users/ifhgz/Desktop/agentic-rag。

- 完整读取根 AGENTS、README、宪章、开发流程和本功能 spec/plan/research/data-model/contracts/quickstart，核对最新阶段及失败记录。specs 内未发现额外 AGENTS/override；rg 无匹配返回 1，不表示执行失败或需要改权限。
- 用 Python 标准库保存 [168 个源文件 hash](../../output/governance011/tasks-20261021/before-source-manifest.json)、[完整 Git 状态](../../output/governance011/tasks-20261021/before-git-status.log)、[完整 Git diff](../../output/governance011/tasks-20261021/before-git-diff.log)、原文档及 [功能指针](../../output/governance011/tasks-20261021/before-feature.json)，退出 0。保留既有换行和旧测试目录权限提示，未清理用户改动。
- `.specify/scripts/powershell/setup-tasks.ps1 -Json`：退出 0，定位 011，返回 research/data-model/contracts/quickstart 与解析模板；原 JSON 保存于 [setup-tasks.json](../../output/governance011/tasks-20261021/setup-tasks.json)。没有运行建分支或发布脚本。
- `python output/governance011/tasks-20261021/document-check.py`：退出 0，任务格式、编号、阶段、标签、前置、需求覆盖、UTF-8、链接与源码未变检查见 [document-check.json](../../output/governance011/tasks-20261021/document-check.json)。这是文档结构检查，不是产品或回答质量测试。
- 生成前后 `.specify/extensions.yml` 均不存在，无 before_tasks / after_tasks hooks 可执行。

没有运行 pytest、前端测试、构建、类型检查、模型、应用或服务；没有读取实际密钥配置、访问正式文档/索引、修改依赖、提交、推送或写入 GitHub。新测试文件名只是任务指定的待创建位置。

## 保留失败与限制

39 项任务尚未运行，不能把分解/格式检查写成工程通过。P1 的旧结果、两项提示措辞失败、CURRENT_FAILURES.md 的真实问题及所有历史证据保持，未重测、未改判。

下一阶段是明确进入 A 的实施，按 speckit-implement 和 tasks T001–T010 完成诊断故障隔离；不能跳过保护直接跑完整套件，也不自动推进 B–D 或真实模型复验。

**报告后暂停，等待用户验收。**
