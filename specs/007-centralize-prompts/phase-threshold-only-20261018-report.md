# 动态阈值保留阶段报告（2026-10-18）

## 阶段目标与授权范围

用户进一步明确：证据上下文侧只保留 `base_token_threshold=2000`、`token_growth_factor=0.9` 的动态阈值计算，其他摘要、摘录、压缩结果和压缩事件全部删除。本阶段按该范围修改，不改检索算法、模型提供方、问答 API 的请求格式、正式知识库或业务查询流程。

## 实际改动

- 将 `backend/app/rag/context_compression.py` 收缩为两类基础能力：
  - `estimate_tokens()`：供输入窗口边界估算；
  - `dynamic_token_threshold()`：按 `base_token_threshold` 和 `token_growth_factor` 计算每轮阈值。
- 删除上下文压缩实现中的 `CompressionResult`、证据消息构造、摘要生成、截断、必要证据摘录和 `compress_context()`。
- 删除 Agent Loop 的压缩执行路径。每轮只记录动态阈值；真正超过模型物理输入窗口时直接返回既有 `context_budget_exceeded`，不生成摘要、不摘取证据、不调用压缩模型。
- 删除压缩状态字段：`context_summary`、`context_compressed`、`context_tokens_before`、`context_tokens_after`、`context_removed_items`；保留 `context_token_threshold` 作为阈值观测字段。
- 删除 `MAX_COMPRESSION_CALLS` 配置和模型预算节点；删除后端 `context_compression` 阶段事件及前端对应的类型、标签和展示分支。
- 保留普通会话历史摘要 `conversation_summary.py`，它与证据阈值是独立功能。
- 更新相关单元测试、脚本、README、当前状态、计划和提示契约说明；历史阶段报告及历史评测证据保持不改。

## 验证

后端定点回归（工作目录 `C:\path\agentic-rag\backend`）：

```powershell
python -m pytest -q --basetemp=..\output\prompt007\threshold-only-20261018\pytest-basetemp-final2 -p no:cacheprovider tests/unit/test_model_agent_loop.py tests/unit/test_context_compression.py tests/unit/test_prompt_consumers.py tests/unit/test_graph.py tests/unit/test_model_loop_budget.py tests/unit/test_v3_5_cost_control.py tests/unit/test_v4_query_analysis.py tests/unit/test_graph_state.py tests/unit/test_v4_eval_runner.py tests/unit/test_v4_formal_capture.py
```

结果：`99 passed`，另有 1 个既有 `test_context_prompt_limits_history_and_preserves_unconfirmed_conditions` 失败。该失败断言的是旧入口 Prompt 措辞（期待历史版本中的固定短语），与本阶段阈值/压缩删除无关，未修改入口 Prompt 以掩盖它。去除该既有失败项后，本阶段定点集合为 `46 passed`。

其他检查：

- 前端 `npm test -- --run`：退出码 `0`，8 个测试文件、26 个测试通过。
- Python 编译检查（Agent Loop、阈值模块、主图、状态、管线、预算和配置）：退出码 `0`。
- `git diff --check`：退出码 `0`；仅有工作区现存的 LF/CRLF 换行提示。
- 应用和测试代码已检索确认：不再引用 `compress_context`、`CompressionResult`、`should_compress_context`、`max_compression_calls` 或 `context_compression` 事件。

本轮首次 pytest 尝试因 Windows pytest 临时目录父目录不存在而产生 setup 错误；创建本轮工作区临时目录后重跑，测试进入正常执行并得到上述结果。该环境问题已保留在本轮记录中。

## 测试性质与限制

以上是工程测试，使用 scripted/fake provider 和确定性 Token 估算；没有启动后端、调用真实 DeepSeek/云端模型、读取正式 Qdrant 索引或运行正式题集。因此只能确认代码路径和界面事件契约已收缩，不能证明真实问答质量或长上下文问题的答案质量。

## 阶段结论与下一步

当前活动实现只保留动态 Token 阈值和物理窗口边界；所有证据压缩动作及其前后状态已删除。下一阶段若要调整超限后的处理方式或重新进行真实问答验收，需要用户另行明确授权。

报告后暂停，等待用户验收。
