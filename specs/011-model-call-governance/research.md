# P2 设计决策记录

日期：2026-10-21。输入：[规格](spec.md)、[当前代码证据](scope-and-evidence.md)及两个只读研究代理。没有运行应用、模型、测试或原型，没有新增依赖。

## R1：共同治理独立于模型循环

**Decision**：新增一个深的 model_call module，以 invoke(spec, context) 返回结果/安全失败和调用记录。调用者不需要构造 AgentState 或借用 loop._invoke。ContextAdmission 仍负责证据准入；物理计量的纯共同函数复用同一实现。

**Rationale**：generator 当前依赖 loop 私有 state，分析和摘要又复制治理。共同 interface 隐藏输入、额度、期限和 trace，业务仍拥有语义解析和有限修复，避免把全部流程塞进新的大循环。

**Alternatives considered**：继续借用 _invoke 留下私有耦合；仅将它改成 public 不消除伪 state；把所有语义也搬入 runner 违反职责；新增多个转发 module 无法隐藏知识。

## R2：真实发送前 guard，保留 complete-only adapter

**Decision**：内置 provider 在实际发送的纯准备结束后调用 before_attempt；首个获准 attempt 预占一次逻辑额度，允许的格式回退重检容量和剩余时间。旧 fake/scripted complete 经内部 adapter 获得相同入口保护，不要求全部测试对象增加方法。

**Rationale**：严格格式回退当前在 provider 内部加入 schema 指令；只包外层调用无法证明回退输入可装入。保留 complete interface 可复用现有两种真实 adapter、fake 和假传输，seam 有实际可替换者，不为假设创建插件框架。

**Alternatives considered**：要求所有 provider 新增 prepare/send 方法会扩大兼容迁移；外层按最坏回退预留会提前拒绝本可发送的 strict 输入；直接拆成两个逻辑调用改变已批准计费。本稿选择小的可选发送前能力，真实 adapter 必须支持。

## R3：租约、额度及绝对期限

**Decision**：调用有 active/closed guard，期限取原请求与单次上限的较早者。首次预占在预算锁内严格检查 request 是否仍活动。shared context 由图拥有，standalone operation 创建 owned context 并 finally 结束，修复共用该 scope。

**Rationale**：当前预算对找不到 request 可 permissive 返回 True，且 future 超时不等于线程停止；二者叠加可能让迟到格式回退再次获准。局部 guard 关闭与原子严格预占阻断新业务使用权，保留原预算策略。

**Alternatives considered**：每次修复/回退 start 新请求会扩大额度和期限；exists()+reserve 两步存在竞争；依赖 cancel 杀死运行中线程不可行。Python futures 文档说明正在执行的任务不会被 cancel_futures 取消。[官方 futures 文档](https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.Executor.shutdown)

## R4：保留 P1 计量并修正 trace 口径

**Decision**：native/plain 继续用 P1 messages/tools 估算包和现有算法；schema、准备后的回退约束纳入本次输入，不双算已嵌入消息的 schema。准入估算不被 token_details 的 messages-only 字段覆盖；拒绝记录与已发生 model_trace 分开。

**Rationale**：本功能统一治理，不借机改 tokenizer、容量或原阈值。当前 _invoke 的输入估算可被后续合并覆盖；结构约束在分析与提供商中又有不同处理。明确当前快照和逻辑次数可避免累计用量冒充空间容量。

**Alternatives considered**：按 HTTP 请求字节冒充模型精确 Token 不成立；把底层 attempts 再加入 model_trace 会重复计费；没有返回的用量不得伪造为零或完整实测。原实测值保留，底层不可得部分注明，usage_source 不能声称全部 provider。

## R5：诊断非阻塞移交与有界资源

**Decision**：请求线程只做受限字段和内建容器的有界复制、put_nowait；1 worker、8 待办、256 状态。快照限制见契约，超限整体 skipped。所有序列化和磁盘操作在 worker；它不接收图、历史、SSE 或同步 logger 回调。

**Rationale**：当前图已完成后同步 write_text 可改写公开结果。异步不是无限排队；复制有明确工作量上限，不调用用户对象的方法，不共享可变业务引用。queued 与 saved 分开，状态报告失败不递归。

**Alternatives considered**：try/except 包同步 write 只能隔离快速异常，不能隔离慢 I/O；把 GraphRunResult 原对象直接交给线程缺少隔离；磁盘告警走共享 logger 会再阻塞请求；引入外部消息队列超出本地应用需要。

## R6：完整且不覆盖的本地发布

**Decision**：同目录独占创建临时文件，完整写完并关闭后发布。Windows 用 os.rename；POSIX 用 os.link 后移除本次临时链接，失败不退化覆盖。已有文件无论标识碰撞还是并发到达都保持原字节。

**Rationale**：Python 文档明确 Windows rename 在目标存在时失败，而 Unix 文件 rename 可以替换目标；因此不能统一使用普通 rename 达到不覆盖，也不能 exists()+replace。使用同目录发布不等于保证断电持久性，不承诺跨文件系统或特殊网络文件系统。[官方 os.rename / os.link 文档](https://docs.python.org/3.11/library/os.html#os.rename)，[CPython Windows 实现](https://github.com/python/cpython/blob/3.11/Modules/posixmodule.c)

**Alternatives considered**：直接打开最终文件会留下半截记录；replace 会覆盖原证据；统一 hard link 在部分 Windows 文件系统不可用。选择平台对应的简单实现，不支持时安全 failed；不为诊断扩大存储依赖。

## R7：应用生命周期与有限关闭

**Decision**：诊断 worker 在 lifespan 启动，close 停止接收、丢弃待办并最多 join 1 秒。使用专用 daemon，活动阻塞无法强杀时允许退出丢失未完成诊断；正式文件只有完整后才可发布。

**Rationale**：普通 ThreadPoolExecutor 即使 shutdown(wait=False)，解释器仍可能等待未完成任务；daemon 可随进程停止，但资源清理不保证，所以要接受未发布临时文件遗留，不自动删旧证据。[官方 futures 文档](https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.Executor.shutdown)，[官方 threading 文档](https://docs.python.org/3.11/library/threading.html#thread-objects)

**Alternatives considered**：无限 wait 破坏关闭约束；强杀线程不可安全实现；单独进程写入引入额外生命周期和通信，当前不需要。本次不更改已有模型执行器的全局退出治理。

## 研究结论与门禁

技术选择均已明确，无未决需求澄清；真实可运行性仍需后续阶段用临时数据和假传输证明。官方资料只用于标准库语义核对，不涉及真实模型或正式知识库。没有把研究建议写成已通过的工程成绩。
