# V2 最终验收清单

- [x] PDF 入库生成 Markdown、Parent 和 Child，问答阶段不重新解析 PDF
- [x] Qdrant 同时保存 Dense/Sparse Child 向量，Hybrid 检索可用
- [x] 首次 Agent 搜索、Parent 读取、多轮 Query 和重复调用去重
- [x] 动态 Token 阈值和逐条 `retrieval_result` 上下文压缩
- [x] `thread_id` 会话隔离、滚动摘要、追问和澄清分支
- [x] SSE/JSONL 具备 request/thread 关联和 Agent 可审计事件
- [x] 日志和前端不展示 API Key、Prompt 或模型私有 reasoning
- [x] React Process 面板展示节点、工具、检索、Parent、预算和压缩状态
- [x] 后端 `64 passed`，前端 `10 passed`，编译与生产构建通过

## V3 预留

- 大模型结构化 Query Rewrite
- 更可靠的历史摘要和澄清交互
- 持久化 Checkpointer
- 更完整的流式工具结果和多问题拆分
- Graph 节点执行期间的实时事件推送（当前为完成后的真实 trace 回放）
