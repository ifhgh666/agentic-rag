# 会话状态

`ToolRouting.needs_knowledge` 为必填布尔值。每个新问题的模型决定写入同轮 checkpoint。普通回答直接更新会话消息并完成。需要文档时，现有 QueryAnalysis 产生可检索问题或单个待补充问题。补充在已确定的知识库路径上重新分析。取消沿用当前待办清理语义。
