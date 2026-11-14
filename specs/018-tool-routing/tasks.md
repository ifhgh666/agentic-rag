# Tasks: 018 按工具需求分流聊天

**Input** [规格](spec.md)、[计划](plan.md)、[调研](research.md)、[状态](data-model.md)、[契约](contracts/chat-routing.md)、[验证指南](quickstart.md)

## 阶段 A

### 准备与基础

- [x] T001 生成 specs/018-tool-routing/ 的规格、需求清单、计划、状态、契约与验证指南。
- [x] T002 在 backend/app/rag/schemas.py、prompts.py、nodes.py、graph_state.py 和 graph.py 实现必填布尔工具决策。新消息先调用分流模型，普通回复和知识库共用现有历史整理。

### US1 普通对话

- [x] T003 [US1] 在 backend/app/rag/nodes.py 使用未绑定工具的模型生成直接答案，写入历史。backend/app/core/pipeline.py 和 reference_observation.py 复用答案流及实际用量，frontend/src/features/chat/ 展示对应节点。
- [x] T004 [US1] 在 backend/tests/contract/test_reference016_stream.py、backend/tests/integration/test_reference016_session.py 和 frontend/src/pages/Chat.test.tsx 验证中文问候、空来源、零检索/澄清、可继续发消息及分流错误恢复。

### US2 知识库

- [x] T005 [US2] 在 backend/app/rag/prompts.py 和 nodes.py 限定澄清条件并接受非空短中文问句。保留待办的继续、取消和新问题语义。
- [x] T006 [US2] 更新 backend/tests/fakes/reference_model.py 及现有图、API、会话测试中与新分流有关的调用约定，保留冻结参考文件和研究行为对照。

### 阶段验证

- [x] T007 运行隔离回归、前端测试与构建，记录 specs/018-tool-routing/phase-a-report.md，更新交接导航后暂停。

T001 → T002 → T003/T005 → T004/T006 → T007。同一文件的实现顺序执行。固定代码后的后端和前端检查可独立运行。
