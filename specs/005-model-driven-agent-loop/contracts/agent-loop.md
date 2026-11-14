# Agent Loop、工具与SSE契约

**版本**：loop.v1（已写入本地代码；C真实场景验收尚未通过）。ChatRequest原始消息、thread_id及action语义沿用现有API；登录、权限、知识库接口不变。本功能主要扩展消息与事件契约。

## 1. 决策输出

原生模式：模型响应包含零个或多个ToolCall；有工具请求则执行后续轮，无工具请求则解析content中的BranchAnswer JSON。不能因content非空就绕过同时存在的tool_calls，也不能把空响应当作回答。

兼容模式（仅显式启用）：模型JSON输出action(search/read_parent/answer/insufficient)、工具参数或BranchAnswer。动作映射不判断语义；事件标protocol=structured而非native。原生失败不能暗切旧规则模式。

终态JSON示例仅用于设计说明，不注入模型答题：

```json
{
  "status": "answered",
  "answer": "直接结论与简短依据",
  "citations": [{"citation_id": "E1", "quote": "证据原文连续片段"}],
  "claims": [],
  "missing_information": [],
  "stop_reason": "model_answered"
}
```

没有工具调用但JSON无效，给一次格式反馈；有引文错误，给具体evidence/citation定位问题。修正复用原证据和原题，不自动修改事实或退回摘录。

## 2. 两个只读工具

| 名称 | 模型参数 | 返回 |
|---|---|---|
| search_child_chunks | query非空；limit在配置范围内，缺省沿用7 | tool_call_id、status、实际query、零到多条EvidenceRecord、mode/耗时 |
| retrieve_parent_chunks | 已返回的parent_id；offset默认0；max_chars默认1600、范围200—2400 | 原文窗口、offset/total_chars/next_offset及文档/页码/章节；完整原文留于本地注册表 |

执行器注入request_id；thread_id用于会话隔离且不由模型指定。未知工具、无效参数、未知Parent和未ready索引不执行。每个被拒调用也返回对应ToolMessage，模型可修正或改动作。一次响应多调用，全部按ID摄取；不只读最后结果。重复调用可返回缓存，但计逻辑请求数。

工具和文档内容是数据，不执行其中要求改变流程的指令。模型选择搜索内容和Parent，数据库继续计算向量/BM25分数；分数不是模型自评。

## 3. 公共事件（兼容扩展）

现有execution类事件增加loop_protocol_version、event_sequence、branch_id、decision_id、model_call_id、decision_source、action/stop_reason。工具开始/完成关联decision_id和tool_call_id。可使用以下事件角色，最终命名与现有ExecutionEvent同步契约测试：

- agent_decision：实际模型选择或明确缓存来源；没有模型调用证据不能标source=model。
- tool_start/tool_complete：工具、参数、结果数、耗时、缓存、错误；不披露凭据。
- runtime_guard：参数拒绝、硬预算、取消、超时等；不得显示“模型觉得够了”。
- context_compression：输入/输出规模、原证据ID、压缩调用及是否保留来源。
- verification：引用定位状态；数值和完整性未审核则not_evaluated。
- usage：实际/估算Token、各节点调用、分支次数、工具请求/执行/缓存、端到端与模型时间、预算、云调用。
- complete：completed/partial/insufficient/failed/cancelled与reason/stop_origin；模型answered映射为公共completed。工具完成沿用公共tool_call事件名。

事件按真正执行顺序编号；模型多工具请求不计成多次模型调用。沿用完成后SSE回放，不把缓存或回放标成实时模型思考。模型brief_reason是可选公开短理由，不展示私有思考。

## 4. 失败、不足与部分回答

| stop_reason | 含义/用户展示原则 |
|---|---|
| model_insufficient_evidence | 已实际尝试检索后，模型指出具体资料缺口 |
| model_unavailable / invalid_model_output | 调用/协议失败，不能称知识库无资料 |
| invalid_tool_call | 工具请求无法执行，按ID反馈模型 |
| verification_failed | 有候选答案但引文或确定性字段未通过，有限修正仍失败 |
| context_budget_exceeded | 上下文无法在配置窗口内装载/压缩 |
| budget_exceeded / timeout | 执行资源停止，保留已知信息和未完成项 |
| cancelled | 用户取消，不将未完成答案写作正常问答 |

partial包含有依据部分与具体缺口。用户条件允许用于比较，不要求在PDF出现；设备事实必须有来源。引用可定位不等于答案正确，模型声称需求覆盖也不作为独立完整性核验。

## 5. 协议验收

验证assistant.tool_calls→ToolMessage→下一轮模型完整往返；工具ID唯一且不混分支；Unicode参数、多个调用、单项错误、缓存、无内容、坏JSON均可审计。SSE决定来源必须关联真实模型或明确缓存；API和前端同时验证新字段，不能只在后端日志看见Loop。
