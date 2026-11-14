# 016 聊天契约

2026-10-27：细化既有 016 行为；工程状态见 [plan.md](../plan.md)，本契约不是运行通过声明。

## 请求与动作

保留认证后的 `POST /api/chat/stream`。正常响应为 `text/event-stream`，每条包含 `event` 和 JSON `data`，带 `request_id` / `thread_id`；响应头 `X-Request-ID` 与事件一致。

| 字段 | 请求约束 |
|---|---|
| question | string，最多 2000 字符，去首尾空白；除 cancel 外不得为空 |
| thread_id | 可选 string，1–128 字符且不能仅空白；cancel 必须显式提供 |
| conversation_id | 可选旧别名；普通请求按 thread_id 优先、否则该字段、否则生成新线程 |
| action | auto（默认）/continue_clarification/new_question/cancel；不接受额外字段 |

请求校验失败在建立 SSE 前返回 HTTP 422；因此 cancel 未提供 thread_id 是 HTTP 422，不是图内 THREAD_NOT_FOUND。认证失败沿用原认证契约。

| 动作/状态 | 会话效果 | 模型调用 |
|---|---|---|
| auto，无 pending | 正常新一轮 | 按图调用 |
| auto 或 continue，有 pending | 追加当前补充并恢复暂停图 | 按图调用 |
| continue，无 pending | NO_PENDING_QUERY，状态不伪造待办 | 无 |
| new_question | 清除未完成待办尾部、保留已完成历史和摘要，再处理本条新题 | 清理无调用，新题正常调用 |
| cancel，线程存在 | 清 pending 并结束暂停，不生成答案 | 整个动作无调用 |
| cancel，显式 thread_id 未存在 | THREAD_NOT_FOUND | 无 |
| 同线程正在执行 | THREAD_BUSY；跨线程独立 | 拒绝的新请求无调用 |

入口传输失败时，已有 pending 保留并释放线程锁；普通研究/聚合失败不能生成澄清待办。new 已清除的旧 pending 不因新题失败恢复。异常处理不承诺恢复到每次节点调用前的全部状态。

## 模型入口与工具

参考 `QueryAnalysis` 的必填字段为 `is_clear: bool`、`questions: list[str]`、`clarification_needed: str`。保留 Pydantic 默认解析、空列表和空字符串，不增加 strict、禁止额外字段或旧联动校验；“最多三问”来自提示，前端不能借展示校验新增硬上限。

清楚且 questions 非空进入研究；否则进入澄清。澄清文字空白或长度不足时沿用参考默认文字，不代词兜底或业务重试。兼容端点入口显式 function_calling，本地沿用已安装 ChatOllama 默认 json_schema；研究均原生 bind_tools。

| 工具 | 模型可见 content | 外围校验及 artifact |
|---|---|---|
| search_child_chunks(query, limit=7) | 每项 Parent ID / File Name / Content，按既定分隔符合并 | query 非空、limit 1–20、索引 ready、既有 min_score；artifact 保存本次 results |
| retrieve_parent_chunks(parent_id) | 完整已存 Parent 文本，允许去正文首尾空白 | UUID、存在且文档 ready；artifact 保留完整 parent.text、document_id、页码、章节等 |

Parent 没有本请求先搜索的程序前置条件，没有 request_id/offset/max_chars 参数，不分页、不截断。工具提示的“先搜索”是引导，不是代码拒绝。未知 Parent 返回 NO_PARENT_DOCUMENT；工具失败使用既有安全错误类别，不把异常正文送给模型或公开流。

## 流式事件与隐私

| 事件 | 可公开数据 |
|---|---|
| step | stage/status/sequence、问题长度等既有安全详情 |
| analysis | schema_version=1、is_clear、questions、source=model、relation、relation_source、action、协议/实时标识 |
| clarification | schema_version=1、pending、question、allowed_actions；清理后 pending=false、空 question/actions |
| node/model_start/model_call/tool_start/tool_call | node/event、event_sequence、实际调用/工具 ID、耗时和下列 details 白名单 |
| retrieval/tool_result | 本次真实工具结果的文档/Parent/Child ID、文件名、章节、页码、分数和检索正文；tool_result 含 tool/tool_call_id/parent |
| answer | aggregate_answers 的可见累计文本、sources；客户端整体覆盖上次值 |
| usage | Token 计数和 provider/estimate/mixed 来源、模型次数、分节点次数、耗时、cloud_calls；model_call_limit=null |
| error/complete | 白名单错误码和固定文字；completed/clarification/cancelled/failed 状态与安全原因 |

执行观察 details 仅允许 `status`、`duration_ms`、`model_call_id`、`input_tokens`、`output_tokens`、`usage_source`、`error_type`、`tool`、`tool_run_id`、`tool_call_id`。不透传未知 callback 字段；同一白名单用于公开 rag.execution 日志。

不公开 system/developer 提示、完整模型输入、研究摘要、私有推理字段、provider 密钥或异常正文。答案/澄清通过现有 visible_text 去 `<think>…</think>` 及尚未闭合块，累计流暂扣可能的开标签。检索正文属于获准的用户证据展示，不等同提示或私有推理。非公开诊断仅移交有界安全快照，失败不得改变问答；diagnostics node 的额外 details 限 diagnostic_id/diagnostic_status/reason。

实际图观察事件使用 `loop_protocol_version=reference.v1`、`replayed=false`；step、answer、usage 等保留各自契约，不要求所有事件新增相同字段。工具调用 ID 按 Send 分支区分，重复回调不重复登记；不能凭重复 ID 丢弃另分支的真实结果。

只有 aggregate_answers 的字符串 token 进入 answer；研究/历史摘要不进入答案区。中间 sources 可为空，正常完成时补齐来源；部分文本后失败仍以 failed 结束，不能标 completed。不发 verification/evaluation/answer_evaluation；保留独立旧核验组件不等于恢复在线调用。用量无预算分母，不宣称新的总额度。

## 来源匹配

采用当前 `_matching_sources` 的确定性规则，无模糊匹配或推测补来源：

1. 解析最终可见答案中首个独立英文 `Sources:` 块，读取紧随其后的 `- filename` 行并去该项首尾空白。
2. 文件名与本次 RequestObservation 的工具 artifact 中 `filename` 完全相等，区分大小写；不去路径、不去扩展名、不解释括号描述、不补历史来源。
3. 匹配项投影为 document_id、filename、section_title、page_start、page_end；章节缺失为空串，页码缺失保持未知，不推断。
4. 按 `(document_id, section_title, page_start)` 去重，保留首次真实记录的顺序；同名不同文档均可列出，不猜测唯一文档。
5. 没有 Sources 块或无交集则来源列表为空；来源相交只证明本次检索出现过该文档，不证明答案每个断言被支持。

## 错误与断开

图内仅 THREAD_BUSY、THREAD_NOT_FOUND、NO_PENDING_QUERY、MODEL_NOT_CONFIGURED、LOCAL_MODEL_NOT_CONFIGURED 映射为固定公开文字；其他 provider/递归/解析异常统一 RAG_PIPELINE_FAILED，公开异常类型可出现在观测白名单中，异常正文不能出现。研究超限走正常模型 fallback，不添加旧图或 provider 回退。

API 以有界事件队列向 SSE 交付；读端断开后停止继续消费，关闭时直接放入非阻塞哨兵唤醒等待队列的消费者；队列满说明已有可读项。worker 在当前 SDK 调用返回并推进迭代器时关闭。取消旧应用截止后，不能承诺断开立即中止 SDK、立即释放 worker/锁或回滚 checkpoint。A 的真实 ASGI 断开加受控阻塞模型检查已覆盖消费者独立退出，B 才核对真实服务；不另加未经批准的截止策略。
