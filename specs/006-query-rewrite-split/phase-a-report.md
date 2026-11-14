# 006 阶段 A 报告：入口契约与完整单问

日期：2026-10-10  
授权范围：仅执行阶段 A（T001–T011）  
分支：`codex/model-driven-agent-loop`

## 阶段目标与停止点

本阶段完成问题补全/拆分入口的三字段契约、完整单问原文承载、原始请求与确认补充保存、精确缓存隔离、入口失败与预算边界，以及对应的隔离工程测试。阶段 A 不包含前端交互完善、拆分后的完整答案增强、真实 Ollama 入口验收或端到端历史失败题复验。

阶段报告保存后暂停，等待用户验收；不会自动进入阶段 B。

## 已完成任务

`tasks.md` 已仅勾选 T001–T011。主要产物如下：

- [固定案例夹具](../../backend/tests/fixtures/query_rewrite_v1_cases.json)：保存 RW01–RW24 的原题、上下文、动作、预期和验证类型。
- [阶段基线](implementation-baseline.md)：保存阶段开始时的工作区快照、005 未通过项、非敏感配置和正式知识库指纹。
- [严格入口模型](../../backend/app/rag/model_schema.py)：`QueryAnalysis` 只接受 `is_clear`、`questions`、`clarification_needed` 三个字段，禁止额外字段，限制最多三个问题并进行首尾 trim 与独立副本判重。
- [入口分析](../../backend/app/rag/query_analysis.py)：未缓存有效请求最多一次模型调用；缓存键包含原题精确哈希、上下文、动作、线程、索引、模型身份和 `query-rewrite-v1` 版本；入口不再以数字/型号不匹配硬拦截；无效输出不自动重试、不切换云端。
- [图与状态适配](../../backend/app/rag/graph.py)、[状态初始化](../../backend/app/rag/graph_state.py)：待办存在且动作为 `auto` 时零模型调用并提示明确动作；原题同时传入检索分支；普通历史保存真实原题和确认补充，不把模型查询文本伪装成用户原话。
- [记忆保存](../../backend/app/rag/conversation_memory.py)：增加真实原题/确认补充的组合方法，并保留失败回滚路径。
- [阶段测试](../../backend/tests/unit/test_query_rewrite_v1.py)及兼容迁移：覆盖三字段协议、单问保真承载、缓存隔离、零重试、预算/窗口/历史保护、待办动作、原题历史和错误数字承载。

## 实际验证命令与结果

所有命令均在 `C:\Users\ifhgz\Desktop\agentic-rag\backend` 工作目录执行，由 `output/run_query006_checks.py` 设置临时数据目录、`LLM_PROVIDER=fake`、确定性嵌入、离线 Sparse fallback 和独立 Qdrant 路径。正式 `.env`、正式索引和正式 PDF 未被修改。

### 入口协议与兼容单元检查

```text
D:/newsoft/python.exe -m pytest -q \
  tests/unit/test_query_rewrite_v1.py \
  tests/unit/test_v4_query_schema.py \
  tests/unit/test_v4_query_analysis.py \
  tests/unit/test_v3_3_query_analysis.py \
  tests/unit/test_conversation_memory.py \
  tests/unit/test_v4_thread_state.py \
  tests/unit/test_model_provider.py \
  tests/unit/test_v3_7_procedure_evidence.py \
  tests/unit/test_v4_conversation_summary.py
```

- 退出码：0
- 结果：119 passed
- 记录：[entry-check-01.log](../../output/query-rewrite-v1/phase-a-20261010/entry-check-01.log)、[entry-check-01.json](../../output/query-rewrite-v1/phase-a-20261010/entry-check-01.json)

### 阶段 A 图/API/截止时间针对性检查

最终重跑命令为：

```text
D:/newsoft/python.exe output/run_query006_checks.py graph-api-check-05 \
  --basetemp=C:/Users/ifhgz/Desktop/agentic-rag/output/query-rewrite-v1/phase-a-20261010/pytest-tmp-05 \
  -q tests/unit/test_query_rewrite_v1.py tests/unit/test_graph.py \
  tests/unit/test_model_loop_budget.py tests/unit/test_request_deadline.py \
  tests/unit/test_model_call_deadline.py tests/contract/test_chat_stream_api.py \
  tests/contract/test_chat_request_deadline.py tests/integration/test_question_answering.py \
  tests/integration/test_v4_clarification_flow.py \
  tests/integration/test_v4_verification_event.py \
  tests/integration/test_v4_formal_regression.py
```

- 退出码：0
- 结果：129 passed，1 个 pytest 缓存目录权限 warning；无测试失败
- 用时：31.28 秒（脚本记录总耗时 41.016 秒）
- 记录：[graph-api-check-05.log](../../output/query-rewrite-v1/phase-a-20261010/graph-api-check-05.log)、[graph-api-check-05.json](../../output/query-rewrite-v1/phase-a-20261010/graph-api-check-05.json)

Q12 的旧回归断言已迁移为新协议：第一次 `auto` 有入口模型调用并建立待办；已有待办时再次 `auto` 为零入口模型调用，保持待办并返回动作选择。该迁移验证了阶段 A 的显式动作边界。

## 保留的中间失败记录

阶段输出目录没有覆盖或删除中间记录：

- `graph-api-check-02`：128 passed、Q12 旧测试断言失败；原因是旧测试要求待办 + `auto` 再调用一次模型，与 006 新契约冲突。
- `graph-api-check-03`：退出码 2；首次迁移测试时产生缩进错误，随后修复，未作为代码质量结论。
- `graph-api-check-04`：23 passed、106 个 setup error；pytest 系统临时目录权限错误，未进入相应测试断言。
- `graph-api-check-05`：使用阶段输出目录作为 `--basetemp` 后 129 passed，作为最终结果。

此前的 `red-schema` 初步记录也保留在目录中；最终入口协议测试已在 `entry-check-01` 和 `graph-api-check-05` 通过。

## 真实模型与工程测试的边界

本阶段全部测试使用 fake/scripted provider、确定性嵌入、临时数据目录和离线检索。它们证明协议、状态、缓存、预算、回滚和事件映射的工程行为，不能证明真实模型会始终逐字保留问题、正确拆分共同条件或避免把 `400 ms` 改成 `40 ms`。

本阶段未运行：

- 真实 Ollama 入口模型验收和 6 个完整单问的逐字核对；
- 真实检索/回答质量验收以及 005 阶段 C 的两道失败题复验；
- 前端测试与构建；
- 30 题正式平台评测；
- 正式知识库重建、索引迁移或 `.env` 修改。

入口现在会保留原始问题并把它传入 Agent Loop，但数字错误仍可能作为格式正确的模型子问题继续向下游传播；这个质量风险只能在阶段 E 的首次真实入口验收中判定，本阶段不能声称已解决。根目录 [CURRENT_FAILURES.md](../../CURRENT_FAILURES.md) 未修改。

## 下一阶段范围

阶段 B（T012–T016）才处理上下文补全、显式继续/新题/取消动作的完整集成、待办隔离细节和前端三个动作按钮。进入阶段 B 需要用户验收本报告并明确继续。

**报告后暂停，等待用户验收。**
