# RAG 职责清晰化：方案阶段报告

2026-10-22。用户指出 014 形成千行文件，要求像参考 GitHub 项目一样清楚。本轮范围为只读核对、目标职责设计和必要 Spec Kit 产物，不实施、测试或启动服务。

## 结论

014 的八文件要求覆盖了整个 RAG 实现，使 tools.py=1840 行、nodes.py=1376 行；参考项目的八文件仅覆盖 Agent 核心，另有 core/db。新方案将八文件限定为真正的 Agent 职责，把模型适配/调用治理、索引/检索、会话存取、答案与请求交付放到明确位置。

推荐结构见 [plan.md](plan.md)：rag 八个核心文件，core 七个明确职责实现和轻量 __init__，现有 knowledge 增加三个实现位置；约 19 个相关源文件。没有恢复原 28 文件平铺，也不把所有代码迁进一个含混 helper。Agent 核心仍实际包含模型循环、节点、路由和工具准入。

静态正文估计：nodes 496、tools 263、graph 229、graph_state 199 行；加 import/说明后，nodes 预计约 500–650、tools 约 250–300。估算不是实施结果或严格行数承诺。A 主要改善职责和依赖，整体实现量仍接近当前；B 才逐项证明真正减码，不能把搬移记为削减。

## 产物

- [规格](spec.md)、[计划](plan.md)、[依据与候选](research.md)、[数据归属](data-model.md)、[契约](contracts/ownership.md)、[验证指南](quickstart.md)、[16/16 规格质量检查](checklists/requirements.md)。
- [161 项符号归属](symbol-ownership.md)及 [机器清单](../../output/clarity015/plan/proposed-symbol-map.json)。
- [正文估算](../../output/clarity015/plan/body-line-estimates.json)、[拟议依赖](../../output/clarity015/plan/proposed-dependencies.json)、[最终静态检查](../../output/clarity015/plan/plan-checks.json)。

职责修复涉及重新打开 007 A3/014 的全部实现归入 rag 决定，计划已明示；仍只有一个 Agent 图/节点包。旧报告保留。本方案尚待验收，当前实现与测试守护仍是 014 八文件状态。

## 真实检查与命令

工作目录：仓库根 C:/path/agentic-rag；Python 只用于文件/AST/哈希，没有导入运行应用。

| 实际命令/操作 | 退出状态 | 结果 |
|---|---|---|
| 完整读 AGENTS/README/宪章、相关流程/架构/技能与 014 规格/计划/任务/报告 | 0 | 确认范围、现状、旧独立能力和停止点 |
| git status --short / git diff、另核对未跟踪文件 | 0 | 已有大量工作保留，完整记录保存 output/clarity015/plan |
| Resolve-TemplateContent spec-template、Save-FeatureJson、setup-plan.ps1 -Json | 0 | 生成 015 模板与导航，未切换分支 |
| 静态 AST 符号清单、调用位置和正文估算 | 0 | 161 个符号均有拟议归属，源码基线 181 份 |
| 第一轮拟议依赖推导 | 1 | 发现 provider→model_call→provider 的 token 估算回边；见下文 |
| python output/clarity015/plan/write_design.py | 0 | spec/plan/research/contract/data/validation/checklist/符号表 |
| check-prerequisites.ps1 -Json -RequireSpec | 0 | 指向 015，相关设计产物齐全 |
| python output/clarity015/plan/check_plan.py | 0 | 161 符号、17 个有定义的目标模块、静态无环、181 源码未变、16/16、UTF-8/链接通过 |

初轮把 estimate_tokens 放 model_call，但 provider 的 token 回退也调用它，会造成拟议循环。保留 [原始失败](../../output/clarity015/plan/initial-dependency-failure.json)和初版清单；最终将 estimate_tokens/正则归 provider 的消息计量，RAG 的 dynamic_token_threshold 归工具准入，消除回边。只调整方案，未修改产品代码。该检查是静态推导，不等于新布局已通过真实导入/回归。

未创建 tasks.md 或勾选工程实施任务：本轮只设计；进入实施前按项目 speckit-tasks 补齐执行任务，默认只执行首个未完成阶段 A。现有 014 任务/报告和 CURRENT_FAILURES 不覆盖。

## 下一阶段与边界

A：职责迁移、必要的导入/patch/源码指纹适配、结构守护和隔离回归，保留全部算法与独立能力。B：A 验收后，再审查单节点子图壳、重复事件构造与 SDK 可复用点；只落地已证明等价的削减。未批准删除旧接口，不盲换模型/ONNX/依赖或照搬上游短实现。

本轮没有运行测试、模型、正式 PDF/索引操作、健康探测或服务重启；没有修改 app/tests/scripts/frontend 源码，未提交/推送/发布。014 的 817 passed / 2 failed / 24 skipped / 2 deselected 仅作历史基线，不当作本轮成绩；两项旧提示断言及真实质量失败保持。

本轮仅新增 015 设计产物、忽略的静态证据并更新 feature 导航。尚未实施新目录，也不宣称当前代码已经变精简。

**方案阶段完成、待用户验收。报告后暂停，等待用户验收。**
