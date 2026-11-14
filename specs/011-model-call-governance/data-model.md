# P2 数据与状态模型

设计依据：[规格](spec.md)、[调用契约](contracts/model-call.md)、[诊断契约](contracts/diagnostics-and-sse.md)。A–D 工程已实现，以下记录当前内部类型和状态约束，不新增数据库或用户接口；结果见 [D 报告](phase-d-report.md)。

## CallContext：请求执行上下文

| 字段/关系 | 约束 |
|---|---|
| request_id / lease_id | 非空系统标识；lease 识别活动生命周期，过期不复活 |
| budget | 引用既有 ModelCallBudget，所有分支共享，不复制计数 |
| request_deadline | 原 monotonic 绝对期限；不得由后续 node 重置 |
| branch_id | 分支为 B1/B2/B3；最终汇总记录可为 final，但预算作用域是请求 |
| ownership | shared 或 owned；只有 owner finally finish |

生命周期：owned 创建并 start -> active -> finish；shared 只借用 active，不拥有关闭权。已结束上下文的调用必须拒绝。独立服务一次 operation 的修复调用引用同一 owned context。

## CallSpec / PreparedAttempt

CallSpec 持有 node、iteration、messages、tools、response_schema；node 对应原策略，不开放跳过检查开关。messages 在调用内快照化，tools 与 schema 互斥。

PreparedAttempt 持有 attempt_index、structured_mode、prepared messages/tools/格式约束；guard 据此计算当前输入估算。它表示真正准备发送的模型内容，不含认证、网络地址或 HTTP 头；不作为新增原始请求正文落盘。

一个逻辑调用对应 1–2 个允许的底层格式 attempts；普通 native 或 schema 成功均为一个，严格格式明确拒绝后才有第二个。不是通用重试列表。

## CallGuard：内部执行租约

状态字段：closed、reserved、deadline、输入估算及 attempt metadata；是否 active 由共享预算的 request/lease 核验。局部锁协调关闭与首次原子预占，不在锁内做外部 I/O。关闭后生成逻辑 model_call_id 和独立 CallRecord，同一调用的所有格式 attempts 共用该记录。

状态转换：created -> active -> reserved -> closed；输入/预算/期限拒绝可直接 closed。reserved 不回退；超时 closed 后不得新取得发送许可、预占或追加业务 trace。关闭前已获许可或 in-flight 的外部请求可以迟到，但没有业务提交权。预算原子预占还核验 lease_id，request_id 重用不能使旧租约复活。

## CallOutcome / CallRecord

| 字段 | 约束 |
|---|---|
| outcome | completed / rejected / failed / skipped；completed 仅表示提供商执行结果已返回，不表示答案正确 |
| result | completed 时为现有 ModelResult；结构非法仍保留原始 content，由业务验证 |
| reason | 既有安全类别：context_budget_exceeded / budget_exceeded / timeout / model_unavailable 等；无异常正文 |
| attempted | 首次发送准入成功为 true；此前拒绝为 false，不算已发生用量 |
| model_call_id / request_id / branch_id / node / iteration | 与既有事件和统计可关联；格式 attempts 共用逻辑 ID |
| timestamps / duration_ms | monotonic / perf_counter 计时；不假装墙钟时间精确测量 |
| input_tokens_estimate | 当前最后已发送输入的完整估算，不累计历次空间，不被 messages-only 覆盖 |
| input_tokens / output_tokens | 提供商确实返回的值；缺失为 null，不伪造 0 |
| usage_source / attempts | 逻辑调用的实测/估算口径；attempts 只记录安全 metadata，缺失底层用量明确不可得 |

原私有 input_messages、candidate_content、业务校验 metadata 继续在原本地诊断范围；runner 不持有会话、AgentState 或日志文件。outcome 返回后不再可被迟到线程更新。

累计统计只消费 attempted=true 的逻辑记录。旧记录缺少 attempted 时维持兼容。拒绝记录形成安全 runtime_guard/node，不伪装成 model_call。

## DiagnosticSnapshot

包含原诊断顶层字段，完整列表见诊断契约。内建容器受限复制，嵌套值不与业务状态共享可变引用；不调用 arbitrary 对象转换或复制回调。非法类型/循环/过大/过期时整体放弃，不做证据裁剪。

快照按精确内建类型复制，不接收自定义子类，避免覆写迭代/转换破坏工作量约束。诊断上限只影响是否记录，不改变 LLM 输入、工具返回、问答状态或调用额度。关闭时甚至不构造 snapshot，不建目录。

## DiagnosticReceipt / DiagnosticStatus

| 字段 | 约束 |
|---|---|
| job_id | 唯一任务身份，状态表主键 |
| request_id / thread_id | 与问答关联；重复 request_id 允许形成不同 job，不覆盖旧状态 |
| status | queued / writing / saved / failed / skipped |
| reason | 固定安全类别，不保存异常正文或私有文件路径 |
| update time | 安全状态观测，不修改模型耗时或总调用用量 |

receipt 只说明提交阶段可知状态；不能把 queued 宣称为 saved。writing 在关闭后、发布前可转 skipped/closed；已经进入发布系统调用则按真实发布结果记录，不能声称已撤回。状态表内存有界，淘汰后 status 返回 None，不声称记录被删除或保存成功。成功文件仍是本地完整证据，重启后内存状态不恢复为无限审计索引。

## 问答结果与诊断的关系

问答结果保留现有 GraphRunResult 和业务状态，不新增 diagnostic_failure 问答终态。诊断关联结果的副本，只能保存或放弃自己的文件。

诊断关闭/提交失败/worker 失败时，原答案、来源、reason、usage、已合法提交的历史保持。原 timeout、失败恢复和待澄清保护仍由现有图/API 主持；诊断 worker 不拥有这些操作。
