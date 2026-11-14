# 确定性证据压缩阶段报告（2026-10-18）

## 阶段目标与授权范围

用户根据代码截图明确要求删除模型驱动的压缩实现，保留 `backend/app/rag/context_compression.py` 这一套确定性压缩实现。本阶段只处理证据上下文压缩的实现、调用和对应工程检查，不修改 API、业务查询流程、检索策略、模型提供方或正式知识库数据。

## 实际改动

- 删除 `backend/app/rag/model_compression.py`，移除基于模型输出 `excerpts/gaps` 的证据压缩协议。
- 删除 `backend/tests/unit/test_v3_4_model_compression.py`，避免已删除模块继续被测试引用。
- 将 `backend/app/rag/agent_loop.py` 的 `_compress` 改为直接调用 `context_compression.compress_context()`：
  - 超出输入预算时进行确定性、可审计的原文摘取；
  - 不再发起压缩模型请求，不解析压缩 JSON，不额外消耗模型调用槽；
  - 保留原始证据注册表，引用校验仍使用完整原文；
  - 继续发出 `context_compression` 执行事件，标记 `decision_source=deterministic`，供前端过程面板和日志使用。
- 从 `backend/app/rag/prompt.py` 删除 `get_context_compression_prompt()` 与 `get_evidence_selection_prompt()`；当前固定提示函数保留 9 个。
- 从 `backend/app/rag/graph.py` 清理已删除模型压缩实现的旧导入。
- 更新 Agent Loop、提示消费测试及 `specs/007-centralize-prompts/`、`README.md`、`docs/CURRENT_STATUS.md` 中的实现说明。
- `conversation_summary.py` 保留不变：它负责普通会话历史溢出摘要，与证据压缩是两条独立路径。兼容配置和预算字段仍保留，但确定性证据压缩不会调用或消费模型压缩预算。

## 验证

工作目录：`C:\path\agentic-rag\backend`

定点后端回归命令：

```powershell
python -m pytest -q --basetemp=..\output\prompt007\deterministic-compression-20261018\pytest-basetemp-final -p no:cacheprovider tests/unit/test_model_agent_loop.py tests/unit/test_context_compression.py tests/unit/test_prompt_consumers.py tests/unit/test_graph.py tests/unit/test_model_loop_budget.py tests/unit/test_v3_5_cost_control.py
```

结果：退出码 `0`，`45 passed in 6.04s`。

附加检查：

- `python -m py_compile backend/app/rag/agent_loop.py backend/app/rag/graph.py backend/app/rag/prompt.py backend/app/rag/context_compression.py`：退出码 `0`。
- `git diff --check`：退出码 `0`；输出中的 LF/CRLF 提示是现有 Windows 工作区换行提示，不是校验失败。
- `rg` 检查应用和测试目录：不再存在 `model_compression`、`ModelContextCompressor`、`get_context_compression_prompt` 或 `get_evidence_selection_prompt` 的运行时引用。

## 测试性质与限制

本阶段验证是 scripted/fake provider 和确定性压缩的工程回归，不是真实 DeepSeek/云端模型、真实 Qdrant 检索或正式题集问答质量验收。此前真实模型压缩失败证据和首答仍保留，未被本阶段改判；本阶段也未启动或重启服务。

## 阶段结论与下一步

证据压缩的活动实现已经统一为 `context_compression.py` 的确定性路径，模型驱动压缩文件、提示和对应测试已删除；定点工程检查通过。下一阶段如需真实模型、知识库或端到端问答验收，需要用户另行明确授权。

报告后暂停，等待用户验收。
