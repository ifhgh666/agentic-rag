# Data Model

无新增业务实体、字段或持久化迁移。ThreadState/ConversationTurn/MemorySnapshot/PreparedQuery 与 ConversationMemory 位于 graph_state。模型与工具纯输入/结果结构位于 schemas。CallContext 和预算/lease 的行为在 tools。各数据字段、校验、冻结及序列化保持。引用文本与来源记录形状保持；不恢复 procedure 主图路径。
