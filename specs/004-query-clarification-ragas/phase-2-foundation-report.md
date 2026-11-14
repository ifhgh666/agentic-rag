# 阶段 2 验收报告：问题分析与线程状态基础契约

**日期**：2026-09-30  
**范围**：只执行 [任务清单](tasks.md) 的 T007、T008；阶段 3 及以后未实施。  
**结论**：阶段 2 共用基础完成，测试通过；此处暂停，等待用户确认下一阶段。

## 交付内容

1. 在 `backend/app/rag/model_schema.py` 新增 `QueryDecision`，约束 `relation` 只能是 `new_question/clarification/uncertain`；清楚的问题必须有 1～3 条去重且非空的检索问题，不能同时要求澄清；不清楚的问题不得带检索问题，必须给出具体澄清文本。保留旧 `QueryAnalysis`，本阶段**不**接管线上模型调用。
2. 在 `backend/app/rag/graph_state.py` 新增 `ConversationTurn` 与 `ThreadState` 契约：只接受普通用户/助手消息，拒绝工具或带内部标记的消息；`thread_id` 不得为空白，`state_version` 非负，`phase` 仅允许空闲、待澄清、回答中；`pending_query` 与补充信息只能在待澄清阶段出现。`advance(expected_version=...)` 构造递增版本并拒绝过期版本，但实际存储层的并发原子更新仍留到 T014。
3. 在 `backend/app/rag/conversation_memory.py` 新增 `thread_state()` **只读投影**，从当前进程内记忆构造上述契约并过滤工具/内部消息；现有追加、设置待办、清除待办会维护递增 `state_version`。旧 `prepare()`、检索图和用户可见问答路径保持原样。
4. 新增 `backend/tests/unit/test_v4_query_schema.py`、`backend/tests/unit/test_v4_thread_state.py`，覆盖有效与非法输出、状态边界、消息过滤和版本推进。

## 先测试、后实现的验证记录

| 步骤 | 命令/结果 |
|---|---|
| 红灯 | `python -m pytest -q tests/unit/test_v4_query_schema.py tests/unit/test_v4_thread_state.py`：两个新类不存在，收集时出现 2 个预期 ImportError |
| T007 绿灯 | `python -m pytest -q tests/unit/test_v4_query_schema.py`：**10 passed** |
| T008 绿灯 | `python -m pytest -q tests/unit/test_v4_thread_state.py tests/unit/test_v4_query_schema.py tests/unit/test_conversation_memory.py tests/unit/test_graph_state.py`：**20 passed**；中途发现并修正全空格 `thread_id` 的验证漏洞 |
| 全量后端回归 | 从 `backend` 目录运行 `python -m pytest -q`：**132 passed, 3 xfailed in 46.22s** |
| 语法与补丁 | `python -m compileall -q` 对改动模块与新测试通过；`git diff --check` 无空白错误。Git 仅提示现有 Windows 换行符处理警告 |

三项 `xfailed` 是[阶段 A 已固定的现存缺陷](../../backend/tests/unit/test_phase_a_known_gaps.py)，**不是**本阶段修好的问题。未运行前端测试，因为本阶段未改前端；未调用 Ollama、RAGAS 或云端模型，未修改正式 PDF、向量索引或标准答案草案。

## 一致性复核与未完成事项

- 实施前用 Spec Kit 的只读分析核对 `spec.md/plan.md/tasks.md`：FR-001～FR-011 和 SC-001～SC-006 均有后续任务映射，阶段 2 与宪章的“先契约和测试、一次一阶段”原则一致。无阻断性冲突。
- 后续需细化 FR-005 的“摘要触发阈值与实体保真”测试，当前任务 T014 只明确了摘要分离；这是阶段 B 的中等风险，本阶段不改任务范围。
- **重要边界**：`ThreadState` 是经过验证的目标模型和旧内存的只读视图，不代表运行图已切换到单一权威线程状态。现有 `MainState.pending_query` 和 `ConversationMemory._threads` 的整合、并发写入保障安排在 T014。旧正则语义分流与待办字符串拼接仍会发生，计划阶段 B 才修复。
- 下一阶段从 T009 开始构建模型优先的问题理解及其测试；阶段 3 未经用户确认不自动执行。RAGAS 题集与 Judge 更靠后，仍未开始。

**任务状态**：T007/T008 已完成并勾选；T009～T029 保持未完成。
