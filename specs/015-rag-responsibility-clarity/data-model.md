# Data Model

不增加字段、业务实体或持久化迁移。

- 图契约 AgentState/MainState/Evidence/GraphRunResult 留 rag.graph_state。
- 会话契约 ConversationTurn/ThreadState/MemorySnapshot/PreparedQuery 随存取实现归 core.conversation。
- QueryAnalysis/BranchAnswer/现有 Agent 模型 schema 与工具输入留 rag.schemas，生产 schema 内容保持。
- AnalysisOutcome 随 QueryAnalyzer 归 core.query_analysis；不是模型直接输出 schema。
- ModelResult/PreparedAttempt 随 provider，CallContext/CallSpec/调用记录/预算/lease 随 core.model_call。
- 来源与引用文本 shape 不变，source_from_record/格式化随 core.answering；旧恢复与筛选能力随 core.legacy_rag。
