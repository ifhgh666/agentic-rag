# V2 技术研究与决策

## 研究范围

本阶段只完成设计研究，不安装依赖、不切换运行中的索引、不实现 Agent。研究聚焦
Qdrant 的本地持久化与混合检索、LangGraph 的线程检查点，以及参考项目的分层
检索/Agent Loop 结构。

## 决策 1：Qdrant 作为 V2 Child 索引

**Decision**：使用 Qdrant 存储 Child，集合同时配置命名 Dense 和 Sparse 向量；
Parent 继续放在文件型 Parent Store。V2-1 先迁移 Dense，V2-2 再启用 Sparse + Hybrid。

**Rationale**：Qdrant 官方文档明确支持同一点中的多个命名向量，并将 Dense 语义检索
和 Sparse 词法检索组合为 Hybrid Search；这正好覆盖型号、引脚、寄存器等精确术语与
自然语言语义的共同需求。

**Alternatives considered**：

- 继续使用 FAISS：可保留 V1，但不能直接表达 V2 的 Dense + Sparse Hybrid 集合。
- 每次问答扫描 Markdown：违反入库/问答严格分离，也无法稳定支持 Agent 重复检索。
- 引入远程 Qdrant Server：可扩展，但增加 Windows 本地开发服务依赖；V2 首版选择
  Qdrant Python client 的本地持久化，后续通过 `VectorDbManager` 契约切换。

参考：[Qdrant Hybrid Search](https://qdrant.tech/documentation/search/text-search/hybrid-search/)、
[Qdrant Hybrid Queries](https://qdrant.tech/documentation/search/hybrid-queries/)、
[Qdrant LangChain local/hybrid example](https://qdrant.tech/documentation/frameworks/langchain/)。

## 决策 2：Sparse 模型

**Decision**：V2-2 使用 Qdrant/FastEmbed 兼容的 BM25 sparse embedding，逻辑向量名为
`sparse`；具体依赖版本在 V2-2 开始前锁定并加入 `backend/requirements.txt`。

**Rationale**：配置指南已指定 `Qdrant/bm25`，官方示例展示了 `RetrievalMode.HYBRID`
需要 Dense embedding、Sparse embedding 和同一集合中的两类向量。先把接口放在
`VectorDbManager`，避免业务层绑定具体编码器。

**Alternatives considered**：自建 BM25 倒排索引可减少模型依赖，但会形成第二套检索
存储，无法满足 V2 的 Qdrant Hybrid 约束。

## 决策 3：LangGraph 图结构与工具循环

**Decision**：保留 Main Graph 和 Agent Subgraph 两层：Main Graph 处理历史摘要、查询
改写、澄清和最终评估；Subgraph 处理 Orchestrator、工具调用、上下文压缩和退出路由。

**Rationale**：参考项目的目标正是以 LangGraph 组织层级检索、记忆、查询澄清和自纠错；
将编排逻辑集中到 Subgraph 可以避免把所有节点堆到 FastAPI 或单一 Pipeline。

**Alternatives considered**：在现有 `RagPipeline` 中增加 if/else 循环实现成本较低，
但状态、预算、工具结果和未来记忆会快速耦合，无法满足 V2 的图状态验收。

参考：[参考项目 GitHub](https://github.com/GiovanniPasq/agentic-rag-for-dummies)。

## 决策 4：会话检查点

**Decision**：V2 使用 `InMemorySaver`，通过 `configurable.thread_id` 隔离同一进程内的
聊天会话；不承诺进程重启后的恢复。

**Rationale**：这是用户提供的 V2 范围，适合当前本地单机阶段；同时在计划中明确它是
开发/测试级方案，避免误认为生产级持久化。

**Alternatives considered**：SQLite/Postgres checkpointer 可以跨重启，但会引入新的
持久化部署和迁移范围，留给 V2.1/V3。

参考：[LangGraph Checkpoints](https://langchain-ai.github.io/langgraph/reference/checkpoints/)、
[LangGraph Memory](https://langchain-ai.github.io/langgraph/how-tos/cross-thread-persistence-functional/)。

## 决策 5：依赖和兼容策略

**Decision**：V2 增量保留现有 FastAPI、PyMuPDF、文件 Parent Store、答案评估、JWT、
SSE 和前端 API；新增依赖通过独立阶段加入。V2-1 前不删除 FAISS，待 Qdrant Dense
回归通过后再决定是否移除。

**Rationale**：每阶段都能运行和回滚，且符合项目宪章的阶段边界与数据一致性要求。

**Open risk**：Qwen3 Dense 模型下载、FastEmbed BM25 模型下载和 OpenAI-compatible
模型的 Tool Calling 能力受本机网络、代理和 Provider 影响；相应阶段必须提供确定性
Fake provider 测试和清晰的启动前检查。
