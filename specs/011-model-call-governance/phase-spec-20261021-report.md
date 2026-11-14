# P2 规格启动阶段报告

日期：2026-10-21（America/Tijuana）。状态：**规格草稿及需求质量检查完成，待用户验收；未实施。**

## 目标与授权

用户要求“开始p2”，承接此前已说明的架构改进 P2 范围确认与规划。本轮完成第一个规格阶段：核对 P1 完成后的代码，定义模型调用治理和诊断交付一致性的需求、默认取舍及验收条件。没有把该指令扩大为全量重构。

使用项目内 [speckit-specify](../../.agents/skills/speckit-specify/SKILL.md)，参考 Matt [codebase-design](C:/Users/ifhgz/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.1/skills/engineering/codebase-design/SKILL.md) 的职责与 seam 原则。P1 中批准的 Matt 替代流程仅作用于 P1，本轮遵循仓库默认 Spec Kit 流程。

## 完成产物

| 文件 | 内容 |
|---|---|
| [spec.md](spec.md) | 2 个独立用户故事、16 条需求、6 项可测结果、边界及假设 |
| [scope-and-evidence.md](scope-and-evidence.md) | 当前结构图及 E1–E5 的实际代码位置、影响、优先级与证明限制 |
| [checklists/requirements.md](checklists/requirements.md) | 16/16 项需求质量自检满足，非产品测试成绩 |
| [.specify/feature.json](../../.specify/feature.json) | 按 specify 流程由 009 导航至 specs/011-model-call-governance；仅作后续定位，不等于实施授权 |
| 本报告 | 当前阶段交付、限制与停止点 |

P2 的显式默认取舍：诊断尽力保存，故障不改写已经合法完成的问答；诊断慢写不阻塞主要答复。成功文件要完整，已有证据不得静默覆盖，公开告警不泄露私有输入。若期望“诊断成功才允许答复”的强制审计模式，应在技术规划前修改本稿，不默认增加该产品要求。

已保存启动前 [168 个源文件的 hash 清单](../../output/governance011/spec-20261021/before-source-manifest.json)、[Git 状态](../../output/governance011/spec-20261021/before-git-status.log)、[完整 Git diff](../../output/governance011/spec-20261021/before-git-diff.log)、[旧功能指针](../../output/governance011/spec-20261021/before-feature.json)和 [解析后的模板](../../output/governance011/spec-20261021/resolved-spec-template.md)。原工作区未提交、未跟踪内容均保留。

## 实际检查与运行边界

工作目录：C:/Users/ifhgz/Desktop/agentic-rag。

- 完整读取 AGENTS、README、宪章、开发流程、仓库导航、测试/评测规则及 P1 最新阶段结论；核对功能指针、失败清单和受影响调用链。
- git status --short、git diff/统计用于已有工作核对；完整 diff 由独立 Python 元数据脚本保存，退出 0。Git 有既有 LF/CRLF 提示及历史测试目录不可读提示，未清理或调整权限。
- 使用 rg 搜索调用、预算、诊断写入及调用者；宽范围 output 搜索遇到旧 pytest 目录的 Permission denied，未访问这些目录、未声称完整检查所有历史输出。当前问题证据以生产源文件为准。
- gh issue list --state all --limit 30 --json number,title,labels：退出 0；仅看到 P1 的 #1–#5，未创建、修改、关闭或评论任何 GitHub issue。
- .specify/scripts/powershell/resolve-template.ps1 -TemplateName spec-template -Json：退出 0，按模板解析栈返回当前核心模板；编号配置为 sequential，下一目录为 011。没有创建或切换分支。
- .specify/extensions.yml 不存在；无 before_specify / after_specify hooks 可执行。规范起草完成后再次核对。
- 文档 UTF-8、链接、编号及源码未变检查：`python output/governance011/spec-20261021/document-check.py`，退出 0；另存 [document-check.json](../../output/governance011/spec-20261021/document-check.json)。首次检查退出 1，因为检查器在创建自己的结果文件前检查该文件链接；已修正生成顺序，[首次失败记录](../../output/governance011/spec-20261021/document-check-initial.json)保留，不是产品测试失败。

没有运行 pytest、前端测试、类型检查、构建或模型，也没有导入应用、启动服务、打开正式索引、读取密钥配置、改 .env、升级依赖、提交、推送或发布。所有“验收场景”均为下一步实现应证明的目标，不是本轮已通过的运行结果。

## 现状与限制

核心证据 E1 为静态调用链：图及历史处理在前，同步诊断写入在后，后者异常可落入外层流水线失败。未做故障注入，不能声称真实线上已复现。其余证据也区分了当前在线路径与仍存在但未在主循环启用的旧接口；不以旧接口推断整个主图无保护。

P1 工程仍是已完成状态。前阶段的完整后端 646 通过、2 项既有失败、2 项排除不记作本轮成绩；旧真实模型失败、CURRENT_FAILURES.md、所有历史报告及 P1 规格/任务均保持。

## 下一阶段与停止点

本轮没有生成 plan.md 或 tasks.md。规格完成不等于已批准实现；下一阶段是用项目内 speckit-plan 形成技术方案，明确公共调用 interface、输入准备与计量契约、独立调用适配、诊断存储和慢写处理、兼容迁移及分阶段验证，再拆实施任务。

尚未发布 P2 GitHub 规格或 ticket，local Draft 仅供当前审阅，不宣称 tracker 已存在可执行任务。

**报告后暂停，等待用户验收。**
