# 调用治理 interface 契约

状态：B/C 已实施，D 已完成隔离组合验证；本文件记录当前内部契约。对照 [spec.md](../spec.md) FR-001–FR-009、FR-016，实际结果与限制见 [D 报告](../phase-d-report.md)，不代表真实模型质量通过。

## 公共 seam 与所有权

`ModelCallRunner.invoke(call_spec, context) -> CallOutcome` 是业务调用者和聚焦测试共用的 interface，不接收 AgentState、不修改历史或 SSE。

| 输入 | 约定 |
|---|---|
| CallSpec | 现有 node 用途、iteration、messages、可选 tools、可选 response_schema；tools 与 response_schema 不同时启用 |
| CallContext | 活动请求租约、适用 branch_id、用于记录的身份；共享同一个 ModelCallBudget，不拷贝额度 |
| Runner 依赖 | Settings、实际 provider、时钟/等待执行 seam；生产复用现有执行器，测试可注入受控 adapter |

调用者不能传入“跳过检查”的标志。是否可选调用及槽规则由已有 node 用途映射：conversation_summary 为可选，final_synthesis 用原汇总槽，answer_repair 在分支内使用该分支额度、最终修复使用原辅助槽。保留原 preserve_answer_slot 等语义，不另设额度系统。

`CallOutcome` 为 completed / rejected / failed / skipped，包含可选 ModelResult、既有安全 reason、CallRecord。runner 不判断回答充分性或引用是否合法，也不产生新修复调用。

必要调用者将 outcome 映射到原有失败路径；可选摘要将拒绝/失败映射到 deferred，保留 backlog。原接口返回形状保持，例如 QueryAnalyzer 仍返回 AnalysisOutcome，AnswerGenerator 仍返回原 tuple。

## 请求生命周期

- Graph.run start/finish 的预算继续由图拥有；runner 借用，不再次 start/finish。上下文携带生命周期标识，失效租约不能被重新注册续命。
- 独立服务没有传入上下文时，由最外层服务操作创建唯一 request_id 和 owned context，预算构造复用 graph 的同一 Settings 策略，在 finally 结束；一次答案及其修复共用上下文，不为每次 invoke 新建额度。
- 已传入 request_id / context 却失效时拒绝，内部标记 context_inactive，对外沿用 timeout 或 budget_exceeded；不自动切换为独立请求。
- ModelAgentLoop.run 的独立调用保持已有“本次拥有预算”的能力，但收敛到相同 scope 工厂。正常生产图一直共用活动租约。
- `operation_context` 统一借用或创建规则：显式 context、request_id 或 lease 无效时拒绝，冲突身份不借用新代次；只有三者均未提供才创建 owned scope。借来的 scope 不结束请求；图通过 `owned_call_context` 管理自己的生命周期。
- 缓存仍在业务层先返回；命中不进入 invoke、不预占、不虚构调用记录。

## 每次实际发送与关闭竞争

调用开始固定 `call_deadline = min(request_deadline, invoke_started + llm_timeout_seconds)`。排队等待、provider 准备及允许的格式回退都计入这段等待。

内置 provider 的 complete 已提供明确的 `before_attempt(prepared) -> remaining_seconds` 可选关键字。PreparedAttempt 只描述本次模型输入：messages、tools、格式约束和 attempt 序号/模式；不含认证、URL、完整 HTTP 配置或可修改的请求状态。

每次发送的顺序：

1. provider 纯准备本次发送内容；不可先发请求再通知 guard。
2. guard 在本次调用的局部锁下确认 active、请求租约、绝对期限及当前完整输入。
3. 首个获准 attempt 在预算自己的同一锁内严格预占一次逻辑调用。reserve 已增加内部使用的 require_active 约束（默认兼容旧直接预算测试），同时核验 request 存在、期限有效、lease_id 与 context 一致；同一 request_id 重新 start 必须产生新代次，旧 context 仍拒绝。不能使用 exists() 后再 permissive reserve() 的竞争写法。
4. 首次成功预占后，本次 guard 标为 reserved；后续允许的格式 attempt 只重检，不再次预占。
5. 返回当前剩余等待；provider 以此限制本次传输，不沿用初始相对 timeout。
6. runner 等待同一绝对期限；结果返回后再次检查。任何退出路径先 close guard，再生成不可变 outcome。

guard 的 closed 与首次 reserve 必须串行协调，锁内不执行网络或文件 I/O。超时后迟到 worker 不得新取得发送许可、追加记录、访问 finish 后的预算或修改会话；不能依赖当前预算对“找不到 request”返回 True 的行为。关闭前已经获准、正进入 SDK 的 attempt 不能保证撤回，已开始的外部 I/O 也不能强制取消；它们继续受超时限制，迟到结果丢弃业务使用权。

## 旧 adapter 与格式回退兼容

- ChatProvider.complete(messages, tools=?, response_schema=?) 保留。普通 fake/scripted adapter 无 before_attempt 参数时，内部兼容 adapter 在真正调用 complete 前运行同一 guard，并以相同外层等待执行；不要求旧测试模型增加方法。
- 能力按明确的 complete 参数/已声明 adapter 能力判断，不依赖 Mock 动态 hasattr。内置真实 adapter 必须支持准备检查，不能降级绕过；自定义 complete-only adapter 的契约为一次发送、无隐藏内容变更或内部重试。
- Ollama 的 schema/tool 准备和兼容接口的 strict 请求均先通知 guard。现有 strict 被明确 response_format 类型拒绝时，兼容 adapter 才准备原允许的一次 json_object 回退，再过 guard。
- 超时、鉴权、其他传输失败、模型非法答复不触发格式回退。逻辑 model_call_id、预算计数及 call_deadline 始终相同；attempt 序号仅是底层尝试，不是新的模型决策或重试额度。
- complete_model 保留既有直接测试用途，成为传输等待/结构解析实现；生产业务统一经 runner。不能留下一个真实生产入口直调 complete 作为逃生路径。

## 输入计量及记录

共同纯计量位于 model_call module，ContextAdmission 的物理计量委托到同一函数；证据计量、拒绝反馈和已读登记原样归属 ContextAdmission。

- 没有 schema 的输入继续估算 `{"messages": messages, "tools": tools or []}`，沿用 estimate_tokens 和 P1 物理限额公式，不能因 SDK 的 HTTP 外壳改算而任意重写 P1 边界。
- schema/格式请求在同一规范化输入包中计入实际生效约束。回退时 schema 指令已进入 messages，不再额外加一次完整 schema。模型名称、HTTP 头等传输信息不是模型输入。
- PreparedAttempt 的计量表述需与真正送出内容在文本/工具/格式上对应；这是现有估算算法的规范化输入，不宣称 SDK 内部转换字节数等于精确 Token。
- 每个 attempt 检查自己的当前输入；不将过去 attempt 占用或证据预算额外累加到当前物理检查。
- CallRecord.input_tokens_estimate 保留最后一个实际获准发送的完整输入估算；若首次发送前被拒绝，估算只在拒绝 metadata 中使用，不进入已发生用量。不得被 token_details 的 messages-only 结果覆盖。
- model_calls、calls_by_node、calls_by_branch 每逻辑调用最多一次；发送后失败也计数。底层 attempts 在本地仅存安全模式、估算、状态和耗时，不重复加入 model_trace。
- 真实返回的 input_tokens / output_tokens 保持提供商原值；格式拒绝等没有返回用量时记不可得，不伪造 0。累计用量继续按逻辑调用的已知/估算口径呈现；若底层用量不完整，usage_source 不得声称完整实测。不要新增隐含的底层 Token 总量猜测。
- 原 input_messages / candidate_content 等私有字段按原权限和来源保留。准备检查不新增持久化完整 HTTP 请求或 schema 回退正文；attempts 只保存安全 metadata。

调用前 rejected/skipped 的 record 不作为已发生 model_call 回放或累加 Token；转成安全 runtime_guard/node 信息。已 attempted 的成功/失败各有一条 model_trace。summarize_usage 对新增 attempted 标志正确过滤，对旧无该字段记录保持兼容。

## 调用者映射与验收

| 调用者 | 迁移后仍由它负责 | 共同 interface 验证 |
|---|---|---|
| QueryAnalyzer | 缓存身份、入口 schema 内容、原问题与 fallback 业务 | 输入/schema、额度、期限、首答原文及结构状态 |
| ModelAgentLoop | 动作、工具、P1 准入、有限分支修复、轨迹关联 | tools 输入、分支槽、单次等待、失败 trace |
| AnswerGenerator | 汇总 payload、引用核验、原有限最终修复 | 不构造 loop/state 或调用 _invoke；汇总/修复槽保持 |
| ModelQueryGenerator | 原接口候选及去重，保持不在主循环启用 | 独立/共享请求、缓存、无直接不受限调用 |
| 普通生成 | 空上下文原行为、原返回 tuple | 独立上下文及实际执行记录 |
| summarize_conversation | backlog 选择、约束校验和版本提交 | 可选额度、不抢槽、迟到不提交，失败 deferred |

隔离测试覆盖旧 complete-only fake、strict 成功、回退后超限、格式拒绝后无剩余时间、回退一次逻辑计费、排队超时后禁止迟发、缺失租约不重建、独立修复共用额度、并行槽和 P1 图/SSE 行为。对应实际测试模块及执行方法见 [quickstart](../quickstart.md)；本文件不是产品使用接口或完整实现代码。
