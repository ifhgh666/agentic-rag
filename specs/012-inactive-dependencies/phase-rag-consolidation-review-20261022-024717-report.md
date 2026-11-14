# backend/app/rag 文件收拢架构检查

2026-10-22。用户要求检查 rag 文件过多时可合并的部分，并参考指定 GitHub 及图片。本轮仅检查和提出候选，不修改实现，不生成实施计划/任务，不运行测试、模型或服务；既有运行服务保持不动。

使用用户指定 ask-matt 路由到 improve-codebase-architecture，并读取 codebase-design、HTML-REPORT 和项目 domain 文档；依技能由一个只读子代理独立复核。报告归档当前 012 目录，不改变功能指针或将候选算成 P3 原任务的一部分。

## 结论

当前 29 个 Python 文件、4964 行；截图八个职责文件已齐全。上游的 core/rag_system.py 和 db/vector_db_manager.py 另承载编排、编码、存储，不能将本地完整 rag 包与上游仅 rag_agent 子集直接按数量比较。

上游核对固定提交 `394c4f7519e41923d695af1efa75b6afec76c553`。原 tree 页面读取失败后，用 raw 内容与 GitHub 连接器的只读 contents/commit 查询完成核对；没有执行远程项目代码。

## 三个候选

| 候选 | 强度 | 问题与 evidence | 合并后的 locality / leverage / depth | 限制 |
|---|---|---|---|---|
| procedure_evidence → evidence | Strong | evidence.py:13 唯一生产导入；:183–184 调用恢复；procedure_evidence.py:39/72/87 为完整段落、目录校验、独立能力 | 相关 implementation 进入同一 module；保留原 interface 与 test seam；预计少一次理解跳转 | 处理 test_v3_7_procedure_evidence.py:8 导入；不能恢复旧证据策略；保留 forwarding 文件则数量不减 |
| sparse_embeddings → embeddings | Worth exploring | embeddings.py:20/42 与 sparse_embeddings.py:22/50 分别管理编码；index_store.py:192 跨取 Sparse | 同 module 放两个 adapter，加载/离线知识更相邻；主要提升 locality，不声称性能或 interface 缩减 | Dense ndarray 与 SparseVector 不能强行统一；vector_db_manager.py:12、两脚本和 Sparse 测试导入需迁移 |
| vector_db_manager → index_store | Worth exploring | index_store.py:56 唯一生产创建；:118–149 跨校验；:177–192 重建/编码；test_v3_1_index.py:31 直接关闭底层 client | 若将生命周期与清单不变量一起收拢，可提升 depth；内部 adapter seam 保留 | 仅拼 class 无收益；持久化、锁、旧迁移、资源关闭与独立底层测试风险最高，不做正式数据重建 |

deletion test：证据恢复合并会集中已有知识；编码主要减少组织跳转；索引只有减少调用者对内部实现的了解才有价值。合并文件并不自动创造 deep module。

首选候选 1。独立选它为 29→28；选 1+2 为 29→27；三组都选为 29→26。全部是静态候选数量推演，外部旧导入的兼容决策未做，尚未实施。

## 维持的结构与决定

- 保留截图对应 __init__/edges/graph/graph_state/nodes/prompts/schemas/tools；007 A3 与 test_rag_architecture.py:16–30 明确这些职责文件和单包归属，不重开双包组织。
- 不合并 model_call/model_provider/cost_control；保留 P1 ContextAdmission 和模型提供商 adapters，P2 预算/lease/deadline 与诊断交付职责不揉进节点。
- 不按 context_compression 的旧名判未使用：32 行中两个计量函数被 8 份生产文件使用；合并到 admission 会形成循环。
- 不直接合并 memory/summary：summary.py:12→query_analysis.py:17→memory 的链会形成循环；存储与模型摘要的 seam 仍有实际价值。
- 保留独立 query_planner/EvidenceSelector/procedure/grounded 调用契约。P3 解除的是主图无效关联，不是删除独立能力的授权。
- 本轮不诊断/修复之前真实冒烟的 citation issue_found，也不把架构合并说成质量问题已经解决。

## 参考与产物

- [上游 project](https://github.com/GiovanniPasq/agentic-rag-for-dummies/tree/394c4f7519e41923d695af1efa75b6afec76c553/project)、[Agent 目录](https://github.com/GiovanniPasq/agentic-rag-for-dummies/tree/394c4f7519e41923d695af1efa75b6afec76c553/project/rag_agent)、[运行编排](https://github.com/GiovanniPasq/agentic-rag-for-dummies/tree/394c4f7519e41923d695af1efa75b6afec76c553/project/core/rag_system.py)、[索引/编码](https://github.com/GiovanniPasq/agentic-rag-for-dummies/tree/394c4f7519e41923d695af1efa75b6afec76c553/project/db/vector_db_manager.py)。上游图组装和节点源码亦已读取。
- [007 单包决定](../007-centralize-prompts/phase-single-rag-package-20261018-report.md)、[012 既有兼容约束](contracts/compatibility.md)、[仓库导航](../../docs/repository-guide.md)。
- HTML 可视报告：`C:\Users\user\AppData\Local\Temp\architecture-review-20261022-024717.html`。每个候选都有 before/after、推荐强度、文件/行号、风险和测试影响。完整目录/源码 hash/命令记录位于 `C:\Users\user\AppData\Local\Temp\architecture-review-20261022-024717`。

实际检查：git status --short、git diff（含未跟踪文件另核对）、Python AST/引用导入静态扫描、主调用链和既有架构测试源码阅读，均未导入运行应用。静态扫描不能证明仓库外没有调用，不将既有历史测试成绩当成本轮执行成绩。GLOSSARY/ADR 资料按项目 domain 约定核对，未新增或修改。

仅新增本报告和临时 HTML/证据产物；产品与测试代码不改。没有定义新 interface，也没有发布 GitHub issue/PR。后续用户选候选后才讨论具体约束；需要实施计划时遵循项目 Spec Kit。

**报告后暂停，等待用户验收。**
