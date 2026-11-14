# P3 规格阶段报告

日期：2026-10-22（Etc/GMT+8）。授权：P2 D 报告交付后，用户要求“继续”；按原架构路线推进 P3 失效依赖清理。本轮仅规格与静态证据，不实施清理。

**结论：P3 规格草案已完成，需求质量审阅 16/16 满足，可进入技术规划，待用户验收。未删除或修改生产/测试代码、未运行产品测试或真实模型。**

## 交付

- [spec.md](spec.md)：两个独立用户故事、边界场景、FR-001–FR-012 与 SC-001–SC-006。重点为主图失效装配整理和独立能力保留；不恢复旧语义逻辑，不扩大 P1/P2 约束。
- [scope-and-evidence.md](scope-and-evidence.md)：当前结构图、6 类候选的实际代码证据、影响/优先级、保留范围及静态证明限制。
- [requirements.md](checklists/requirements.md)：16 项需求质量逐项审阅；勾选表示规格质量，不表示清理或测试完成。
- `.specify/feature.json`：按项目内 speckit-specify 要求，从 011 指向 `specs/012-inactive-dependencies`，供后续定位；没有创建/切换 Git 分支，也不将指针当实施授权。

没有生成 plan.md 或 tasks.md。既有 011 规格、任务与 D 报告保持原状，P2 的 39/39 工程完成结论不重开；用户验收和真实质量结论仍分开。

## 主要发现与范围取舍

1. 子图 `build_agent_subgraph` 有 6 个参数在函数体中未读取：context_builder、retrieval_top_k、max_tool_calls、max_iterations、parent_threshold_chars、query_generator。图仍向它传入相应参数，容易误导实际依赖判断。检索、迭代与预算的同名配置仍在当前工具/循环中使用，不能连设置一起删。
2. 主图仍默认构造旧 QueryGenerator 和 rewrite cache，但子图不读取它；这说明无效装配，不证明发生额外模型调用。
3. EvidenceSelector 没有在当前图执行 select，但子图还读取它的 settings/request_cache。它目前是必要属性的载体，不能未经替代就直接删除。evidence.py 的 source_from_record 仍在当前模型循环和结果汇总中活动。
4. procedure 标志在图内固定/转发，但模型循环未读取；独立生成的两个同名相关参数也没有在该函数体使用。不过旧公开能力、测试和脚本仍使用这些字段/参数，不能从“主图不执行”推导出整模块或兼容入口可删。

规格默认保留独立改写、证据选择、procedure 辅助与答案生成能力及 P2 治理；具体参数、属性和配置兼容方式留给后续技术方案。静态引用清单与图内无读取证明是候选证据，不是批量删除授权，也没有测得性能提升。

## 流程、实际命令与状态

执行项目内 [speckit-specify](../../.agents/skills/speckit-specify/SKILL.md)，已完整读取根 AGENTS、README、宪章、流程、当前 P2 规格/任务/报告及相关调用链。当前编号策略为 sequential；扫描 specs 最大编号 011，创建唯一新目录 012。实施前后均无 `.specify/extensions.yml`，没有 before/after hooks；未调用子代理。

模板经 `.specify/scripts/powershell/resolve-template.ps1 spec-template -Json` 从实际覆盖解析栈取得，退出 0，保存 [resolved-spec-template.json](../../output/cleanup012/spec-20261022/resolved-spec-template.json)。规格按解析出的必备章节组织；不凭空假定模板覆盖来源。

所有命令 cwd 为 `C:/path/agentic-rag`。取证脚本 [cleanup012_spec_audit.py](../../output/cleanup012/spec-20261022/cleanup012_spec_audit.py) 在当前 Python 中执行，不导入 app、不构造 Settings、不读取 `.env`。

| 实际命令/检查 | 退出/状态 | 结果 |
|---|---|---|
| `python C:/Users/user/AppData/Local/Temp/cleanup012_spec_audit.py before` | 0 | 保存 200 个源码 hash、原指针、CURRENT_FAILURES 与 P2 D 报告副本，并记录 Git 状态/diff 和引用扫描 |
| 脚本内 `git status --short --untracked-files=all`、`git diff` | 各 0 | [状态](../../output/cleanup012/spec-20261022/git-status.log)、[原差异](../../output/cleanup012/spec-20261022/git-diff.log)；未清理任何既有 dirty/untracked 工作 |
| 脚本内 `rg -n <候选符号> backend/app backend/tests backend/scripts backend/.env.example` | 0 | 完整 argv/cwd/exit 见 [reference-scan.json](../../output/cleanup012/spec-20261022/reference-scan.json)，[输出](../../output/cleanup012/spec-20261022/reference-scan.log)保留定义、独立调用与装配证据 |
| `python C:/Users/user/AppData/Local/Temp/cleanup012_spec_audit.py verify` | 0 | AST 核对 6 个子图参数及 2 个生成兼容参数；200 个源码 hash、真实失败清单和 P2 报告原字节保持 |
| 文档结构/UTF-8/本地链接校验 | 0 | 12 项 FR、6 项 SC、16/16 质量勾选，无未解决澄清标记；报告前已检查 24 个链接路径，最终结果另存 output |
| `git diff --check -- .specify/feature.json specs/012-inactive-dependencies` | 0 | 无差异格式错误；未跟踪新文档另作结构和链接检查 |
| 产品测试、服务启动、真实模型、正式数据操作 | 未运行 | 模型调用 0；不把 P2 旧成绩算为本轮成绩 |

[static-parameter-audit.json](../../output/cleanup012/spec-20261022/static-parameter-audit.json)明确记录“函数体未读取”及局限；[preservation-check.json](../../output/cleanup012/spec-20261022/preservation-check.json)记录源码和原失败/报告保持。没有发布 ticket、提交、推送、合并或更新外部应用。

## 失败与限制

P2 完整回归的两项旧提示词措辞断言仍是既有失败；本轮未运行，不能记为通过或新增失败。CURRENT_FAILURES 的两道真实问答失败未复验、未改判。

静态分析不能证明仓库外没有调用，也不能决定公开接口或配置的最终删除方式；仍有兼容使用的条目默认保留。规格审阅只证明要求足够清楚，不证明实现、性能改善、真实模型语义或回答质量。

下一阶段范围：按项目内 speckit-plan 形成技术方案，落实逐项清理/保留/延期清单、兼容处理、行为验证与阶段停止点；本轮没有执行这一步。

**报告后暂停，等待用户验收。** 不自动制定计划、拆任务、修改代码、执行真实复验或提交/推送。
