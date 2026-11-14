# P3 技术规划阶段报告

日期：2026-10-22（Etc/GMT+8）。授权：规格报告交付后用户要求“继续”；本轮仅技术规划，不拆任务或实施。

**结论：P3 技术方案与设计产物已完成、待用户验收。规划前后宪章门满足，无未决澄清；200 个源码文件原 hash 保持。未运行产品测试、真实模型或应用，尚无清理实施成绩。**

## 交付与主要决策

- [plan.md](plan.md)：目标结构、逐项清理/保留/延期清单、兼容取舍、需求映射和 A/B 阶段停止点。
- [research.md](research.md)：七项设计决策、理由与备选方案；整合两个只读研究代理及主代理的代码核对。
- [data-model.md](data-model.md)：五项实际依赖、兼容属性状态、procedure 及旧配置边界；不新增业务数据库或运行期通用模型。
- [contracts/compatibility.md](contracts/compatibility.md)：原 builder、Graph 构造/属性、独立接口、旧字段/配置及问答/SSE 的明确兼容契约。
- [quickstart.md](quickstart.md)：未来 A/B 的隔离前提、场景、现有测试入口、完整回归命令与原失败保留规则；所有新验证均标记尚未运行。
- [spec.md](spec.md)：只更新规划交付状态与阶段说明，需求和成功标准不变；原规格阶段报告、scope 和质量清单保持字节不变。

方案选择：正常主图显式传 settings/tools/generator/budget/request_cache；停止默认构造旧 QueryGenerator、rewrite cache、EvidenceSelector。旧 build_agent_subgraph 原签名保留，同文件适配到唯一精简 builder；不增加新生产模块。两个 Graph 兼容属性仅在显式访问时创建并缓存，保留 setter、None、显式注入的原绑定以及并发首次读取身份。

正常图 procedure 写入/转发拟移除，TypedDict 可选声明、AnalysisOutcome 字段、独立生成参数、独立证据处理和 Parent 旧配置解析保留。低收益公开常量及预存未用导入延期，不把局部装配清理变成批量删除。

兼容范围也有明确限制：修改旧 selector 内部 cache 等属性不再间接配置当前图；旧 builder 的依赖在构建时解析，不提供属性重新绑定的热更新协议。这是本次解除的隐式关联，不能声称未知外部内部状态突变都完全兼容。

## 后续实施阶段设计

| 阶段 | 范围 | 独立验收与停止点 |
|---|---|---|
| A / Phase 1 | 主图实际依赖、旧 builder 适配、构造注入与按需兼容属性 | 默认旧构造 0、兼容身份/赋值/并发、旧调用和单/多分支闭环；phase-a-report 后暂停 |
| B / Phase 2 | procedure 无效传递、旧参数/字段/配置说明、独立能力与最终组合 | 独立契约、P1/P2/SSE/隐私/期限、完整隔离后端及前端检查；phase-b-report 后暂停 |

这是技术阶段设计；tasks.md 尚未生成，A/B 均未实施。下一步是按 speckit-tasks 拆成可执行任务，不自动开始 A。

## 流程和实际检查

按项目内 [speckit-plan](../../.agents/skills/speckit-plan/SKILL.md)执行。技能明确“Command ends after Phase 1 design.”，因此本轮完成研究及设计产物后结束；项目 AGENTS 另要求阶段报告后暂停，不跨阶段执行。

根 AGENTS、README、宪章、当前规格/证据/报告及相关调用链已核对；requirements 质量门为 16/16，未改原勾选。技能要求的两个研究任务均为只读，没有修改文件、运行模型或测试；未创建新的用户聊天或对外发送消息。

工作目录统一为 `C:/Users/ifhgz/Desktop/agentic-rag`。实际命令与状态：

| 检查 | 退出/状态 | 证据 |
|---|---|---|
| `python C:/Users/ifhgz/AppData/Local/Temp/cleanup012_plan_audit.py before` | 0 | 保存 200 个源码 hash、原 Git 状态/diff、引用扫描与原失败/P2 报告；[before-manifest.json](../../output/cleanup012/plan-20261022/before-manifest.json)、[git-status.log](../../output/cleanup012/plan-20261022/git-status.log)、[git-diff.log](../../output/cleanup012/plan-20261022/git-diff.log) |
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 从实际模板覆盖栈复制新 plan；[setup-plan.json](../../output/cleanup012/plan-20261022/setup-plan.json)、[原解析模板](../../output/cleanup012/plan-20261022/resolved-plan-template.md) |
| `git branch --show-current` | 0 | 实际为 codex/model-driven-agent-loop，没有切换；setup JSON 的 BRANCH=012-inactive-dependencies 是该脚本按功能上下文解析的标识，不是 Git 分支事实 |
| `python C:/Users/ifhgz/AppData/Local/Temp/cleanup012_plan_audit.py verify` | 0 | 静态参数审计、200 个源码及原失败/P2 报告 hash 均保持；[preservation-check.json](../../output/cleanup012/plan-20261022/preservation-check.json) |
| 设计文档结构/UTF-8/链接/保留检查 | 0 | 必备设计文件齐全，无未决占位，报告前 17 个本地链接路径有效；原 scope/checklist/规格报告/功能指针不变；[design-check.json](../../output/cleanup012/plan-20261022/design-check.json) |
| `git diff --check -- specs/012-inactive-dependencies` | 0 | 无差异格式错误，未跟踪文档另校验结构/链接 |
| 产品测试/应用/真实模型/正式数据操作 | 未运行 | 模型调用 0；没有工程清理通过数，不重用 P2 旧成绩 |

首次填充模板时，精确替换补丁末行上下文不匹配，补丁在写入前被拒绝；先保存原模板，再完成新规划文件。仅影响本轮新文档，记录见 [plan-write-initial.json](../../output/cleanup012/plan-20261022/plan-write-initial.json)，不算产品红测。

实施前后 `.specify/extensions.yml` 均不存在，无 before/after hooks；没有子目录额外 AGENTS。`.specify/feature.json` 仍指向 012。没有改生产/测试代码、依赖、`.env`、正式知识库或索引，未清理既有 dirty/untracked 工作，未提交、推送、合并、发布或写 GitHub。

## 限制与停止点

设计验证只证明方案与当前证据一致，不证明实现、性能改善或真实模型质量。按需属性、旧入口和 procedure 兼容都需后续真实运行隔离工程用例证明，不能以文档和静态无引用代替。

P2 D 的 797 passed / 2 failed / 2 deselected 是历史记录；两项旧提示词措辞失败和 CURRENT_FAILURES 的真实问答失败本轮未复验、未改判。未测维度仍未测。

**报告后暂停，等待用户验收。** 下一步仅在用户指示后进入任务拆分；不自动实施 A、执行真实复验或提交/推送。
