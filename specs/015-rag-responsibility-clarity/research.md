# Research: 目标清晰度与真实实现范围

## Decision 1：参考职责分布

参考固定提交 394c4f7519e41923d695af1efa75b6afec76c553，已读取实际源码：上游 rag_agent/tools.py 88 行、nodes.py 331 行、graph.py 62 行；core/rag_system.py 装配模型与知识能力，db/vector_db_manager.py 持有 Qdrant/embedding。八个文件只表达 Agent 核心。

- Rationale：本地 tools 1840/nodes 1376 的主要问题是把不同职责合并；直接将所有能力集中八文件没有减少复杂度。
- Alternatives：继续维持全部八文件、恢复原 28 个平铺文件、移到未命名 helper 包，均不能表达清楚的职责。
- Sources：[Agent tools](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/394c4f7519e41923d695af1efa75b6afec76c553/project/rag_agent/tools.py)、[nodes](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/394c4f7519e41923d695af1efa75b6afec76c553/project/rag_agent/nodes.py)、[core](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/394c4f7519e41923d695af1efa75b6afec76c553/project/core/rag_system.py)、[db](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/394c4f7519e41923d695af1efa75b6afec76c553/project/db/vector_db_manager.py)。

## Decision 2：保留能力，隔开正常路径与独立旧入口

main.py 当前总是提供 graph_service；graph.py 的两项按需兼容属性和旧 builder 不驱动主图。EvidenceSelector/旧 QueryGenerator 仍有单独测试和部分脚本用途，不能按主流程无引用删除。

- Rationale：012 明确保留独立能力，本次用户没有要求删除功能。
- Alternatives：直接删除旧接口能减少行数，但会改变已存在契约，不作为 A 方案。

## Decision 3：职责修复与真正减码分阶段

静态归属可在不改算法下验证；ModelAgentLoop 承担两协议/修复/预算/原文准入，与上游普通 ToolNode 并不等价。先完成 A，再证明 B 的具体削减。

- Rationale：避免在目录修复时同时换 SDK/策略/模型，导致无法归因。
- Alternatives：直接复制上游短实现可能丢失约束；没有真实代码/假调用证据时不采用。

## 当前可审查的减码候选

| 候选 | 证据 | 处置 |
|---|---|---|
| 单节点子图与多层调用壳 | graph.py:54–65 只注册一个 model_loop；nodes.py:1165–1168 又只创建 ModelAgentLoop 并运行 | B 评估正常路径直达真实 interface；保留独立 builder 契约 |
| 请求事件投影/标识装配 | RagPipeline.run 同时含 step/execution 闭包与图结果、直连分支交付 | B 检查可复用的纯投影；不能改变事件顺序或字段 |
| 旧独立证据/查询功能 | nodes.py:80–351 与 :1084–1161；主图不调用，但独立用途仍存在 | A 迁到明确的 legacy_rag，删除需另行范围决定 |
| LangGraph/模型 SDK 复用 | 上游利用 ToolNode/ChatOllama/QdrantVectorStore；本地额外的 P1/P2 和 ONNX 契约存在 | B 仅做受控可行性验证，不预设替换成功或升级依赖 |

没有将一次静态无引用视为冗余证明；本轮无新技术选型或真实模型测试。
