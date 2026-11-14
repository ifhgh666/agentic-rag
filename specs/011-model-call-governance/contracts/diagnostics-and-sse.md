# 诊断保存及问答交付契约

状态：A 已实施，D 已完成与全部调用链的隔离组合验证。对照 [spec.md](../spec.md) FR-010–FR-016；实际结果及限制见 [D 报告](../phase-d-report.md)。

## interface 与装配

`DiagnosticRecorder.submit(snapshot_source) -> DiagnosticReceipt`：只接受限定字段及普通内建值，先有界复制，再非阻塞入队。

`DiagnosticRecorder.status(job_id) -> DiagnosticStatus | None`：内部存储/测试 seam，返回有界保留的安全状态；不新增 HTTP 用户入口。

`DiagnosticRecorder.close(timeout=1.0)`：停止接收，待办标为 skipped，至多等待该时长；幂等。生命周期由 FastAPI lifespan 管理，构造对象不启动线程、不访问文件系统。

生产由 Services 装配一个 recorder 并注入 RagPipeline。直接构造 pipeline 的工程/脚本调用若需要诊断，显式管理 recorder 生命周期；没有 recorder 时 safe skipped，而不是回退同步写盘。测试可注入相同 interface 的内存或受控存储 adapter。

## 有界快照与状态

快照只包括现有私有诊断字段：request_id、thread_id、original_question、model_trace、execution_trace、retrieval_batches、evidence_registry、status、stop_reason、usage。调用新增 attempts 只为安全 metadata；不增加私有推理、密钥、认证参数或其他原始正文。记录内已存在的原输入/首答保留原用途，真实密钥和私有推理字段仍不得进入新快照。

只复制 str/int/float/bool/null 和受限 list/dict；按精确内建类型检查，拒绝自定义子类，dict key 必须为精确 str。容器复制后与原对象脱离，字符串可复用不可变值；不能调用任意对象的 __deepcopy__、__str__、覆写 items 或 __iter__。循环、非法类型、超过 64 层、2,000,000 字符或 100,000 节点时整体 skipped/failed，不截断正文后宣称 saved。复制时检查剩余请求期限；过期中止快照。

1 worker + 最多 8 待办；队列满、关闭或未启动时直接 skipped。状态表保留最近 256 项，键为唯一 job_id；request_id 仅关联问答，重复 request_id 的两个 job 状态不能互相覆盖。状态锁不包裹任何 I/O。

状态流为 `queued -> writing -> saved | failed`，或提交时 `skipped | failed`；关闭尚未开始的任务为 skipped。writing 中的 I/O 返回后若已关闭且尚未开始发布，转 `skipped(reason=closed)`。safe reason 为固定类别，例如 disabled、queue_full、snapshot_limit、invalid_snapshot、request_expired、closed、serialize_failed、write_failed、conflict、publish_failed。禁止异常正文和路径。

## 文件发布

最终文件沿用 `logs/loop_traces/<request_id>.json` 和原顶层 JSON 结构。request_id 由系统生成并按合法标识校验，不能用用户字符串拼出目录穿越。

worker 内完成序列化（UTF-8、拒绝非有限数值）、建目录和写入。临时文件位于同目录，含唯一 job_id，并以独占方式创建。完整写入、flush 和 close 之后才发布正式名字：

- Windows：os.rename，目标存在时失败，不用 os.replace。
- POSIX：os.link 将完整临时文件关联到不存在的最终名字；成功后解除本次临时链接。文件系统不支持时安全失败，不降级为覆盖复制。

不能先 exists 再覆盖写入。重复标识即使同时到达，也至多一份发布成功；已有文件字节保持。发布前失败只尽力清理本次临时文件；发布已成功后清理临时链接失败不能误报正式文件未保存，不删除已成功记录。不会自动扫描、修补或删除历史半成品和原失败证据。

这是完整新文件的可见性与不覆盖契约，不保证断电持久性或网络文件系统的特殊一致性；使用本地同目录文件系统。见 [research.md](../research.md) 的官方依据及取舍。

## SSE、历史和诊断状态

图运行及原会话保护继续决定问答 status / reason / answer / sources / usage。诊断故障不改变它们，不重试模型，不重跑图，不恢复成另一份历史。

主答复路径只调用 submit。可在原 complete 之前用现有 node 事件直接表达安全回执：

```json
{"node":"diagnostics","event":"node","details":{"diagnostic_id":"job-id","diagnostic_status":"queued","reason":"accepted"}}
```

实际事件仍带原 request_id、thread_id 和现有 envelope；这个例子只展示诊断相关字段。queued 不等于 saved，不能将它放入问答 success 原因或模型用量。可以通过 status(job_id) 得到后续 saved/failed，不在 SSE complete 之后更新。

构造安全 node 时不得调用会同步写共享 StructuredLogger 的 pipeline.execution helper。worker 不接收 logger、graph、memory、generator 或可回调它们的闭包。状态报告自身失败直接放弃，不能递归写日志，也不能抛回问答处理。原非诊断日志体系保持其既有能力，不在本任务承诺任意日志故障均被隔离。

所有原 analysis/answer/retrieval/verification/usage/complete 名称和含义保持；不新增 UI。现有前端 node 消费可展示安全 metadata；不认识新增 details 的消费者仍可忽略。

## 关闭及迟到行为

close 先停止接收，再将等待队列任务转 skipped；活动 worker 有关闭标志，完成当前阻塞后在下一发布前检查是否关闭，关闭后不再开始新发布。已进入发布系统调用时不能安全撤回，成功文件可以留下，但它绝不触发问答事件或历史操作。

专用 daemon 允许进程在有界关闭后退出；不能用普通 ThreadPoolExecutor.shutdown(wait=False) 声称进程一定能退出。活动 I/O 不可强杀，强制退出允许丢失未完成诊断或留下未发布临时文件；关闭不扫描删除旧目录。

## 故障验收矩阵

| 情形 | 诊断状态 | 问答交付要求 |
|---|---|---|
| 关闭/未启动 | skipped | 不建目录，原答复和单终态保持 |
| 正常 | queued，后 saved | complete 无需等文件；最终文件完整 |
| 序列化/目录/写入失败 | failed | 原答案/来源/原因/用量/历史保持 |
| 队列满或快照超限 | skipped | 立即继续，不裁剪和等待 |
| 同 request_id 冲突 | 至多一个 saved，其余 conflict | 原文件不变，两次问答仍按各自结果交付 |
| worker 卡住 | queued/writing | SSE 在释放阻塞前已有唯一终态；关闭限时返回 |
| 原问答超时，诊断也失败 | failed/skipped | 原 timeout，不追加成功，不污染历史 |
| 诊断告警再失败 | 状态可缺失 | 不递归、不改变问答 |

现有隐私测试由“complete 后立即读文件”改为经公共 status seam 和可控完成通知有界等待；这种等待只在测试中。不能为保留旧测试写法，把同步保存留在产品主路径。
