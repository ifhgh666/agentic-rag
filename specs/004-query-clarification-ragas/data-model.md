# 数据模型与状态转移

**状态（2026-10-07 首批结束）**：线程状态、入口分析、题集验证、离线运行器和在线核验已实施。15 题已获批准，首批真实采集/评估结束，达到 80 次 Judge 上限；只有 Q7 五项完整，回答人工复核及正式总验收未完成。见[本批报告](formal-ragas-report.md)。

## 1. 会话状态 `ThreadState`

| 字段 | 含义 | 约束 |
|---|---|---|
| `thread_id` | 当前工作台会话标识 | 非空；不同线程完全隔离 |
| `state_version` | 乐观并发版本 | 每次有效状态转移递增；同线程并发冲突须重试或拒绝 |
| `phase` | `idle`、`awaiting_clarification`、`answering` | 唯一当前阶段 |
| `recent_messages` | 有类型的普通用户/助手已完成轮次 | 不包含工具消息、模型内部分析、未解决澄清问答 |
| `summary_backlog` | 移出近期窗口但尚未成功摘要的普通消息 | 原文保留；摘要成功后只移除本次已处理部分 |
| `conversation_summary` | 较旧普通轮次的压缩背景 | 只供理解问题；不是可引用 PDF 证据 |
| `pending_query` | 尚未解决的原始问题 | `awaiting_clarification` 时必填，`idle` 时为空 |
| `pending_clarifications` | 依时间排列的用户补充 | 仅当待办存在时保留；不得混入新题 |
| `last_request_id` | 最近进入回答流程的请求标识 | 用于追踪；不是完整的重复请求幂等机制 |

首批由进程内 `ConversationMemory` 的 `ThreadState` 字典统一保存；主图 `MainState` 是请求临时状态，不再另用跨轮 checkpoint 保存待办。重启后状态消失，界面已有提示。近期窗口默认保留 4 条普通消息，溢出进入 `summary_backlog`。有剩余调用预算时才调用增量摘要模型（每请求最多 1 次，输出最多 2000 字符），摘要成功且型号/数值/限定条件校验通过才移除原文。预算不足或摘要失败时保留原文，下次分析仍读取；不直接截断关键内容。

简单请求总上限仍为 2 次，分析和生成都调用时不能追加摘要。历史、摘要、待办及补充的分析输入默认合计上限为估算 4000 Token；超限会明确返回 `history_budget_exceeded` 并建议新会话，而不是无声丢弃内容。历史助手回答及摘要只作为会话背景，不是 PDF 证据。日志记录必要元数据，不泄露密码或密钥。

### 状态转移

| 旧状态 | 输入关系或显式动作 | 处理 | 新状态 |
|---|---|---|---|
| `idle` | 清楚的新题 | 保存分析结果并进入检索/回答 | `answering` → `idle` |
| `idle` | 不清楚的新题 | 保存原题和一个澄清问题，不检索 | `awaiting_clarification` |
| `awaiting_clarification` | `continue_clarification` 或可靠判为补充 | 加入补充列表并重新分析原题；仍不清楚则追问 | `awaiting_clarification` 或 `answering` |
| `awaiting_clarification` | `new_question` 或可靠判为新题 | 归档/清除旧待办，原样处理新输入 | `idle`、`awaiting_clarification` 或 `answering` |
| `awaiting_clarification` | `cancel` | 清空旧待办，不生成答案 | `idle` |
| `awaiting_clarification` | `uncertain` | 要求用户显式选择，不默默拼接 | `awaiting_clarification` |
| 任意 | 模型超时/输出无效/预算不足 | 返回可追踪的失败或安全降级，不写成“已理解” | 保留原阶段 |

自动模式下，模型判为补充但仍无法形成完整问题时，采取通用状态保护：转为 `uncertain`，不写入补充；用户明确选择 `continue_clarification` 后才累计不完整补充。这是状态约束，不按具体措辞做正则语义判断。可靠且完整的补充直接进入回答，不需要额外模型调用。

每个线程有非阻塞请求锁；忙碌请求返回 `THREAD_BUSY`。更新在存储锁内校验 `state_version`，拒绝旧版本覆盖；读取深拷贝防止外部改写。进入回答后若下游抛出异常，恢复原待办和历史，同时版本继续递增。未知线程取消返回 `THREAD_NOT_FOUND`；取消不调用分析模型、不检索、不写普通消息。不同线程互不占用该请求锁；持久化、多进程和完整幂等不在本阶段范围内。

## 2. 问题分析结果 `QueryDecision`

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `relation` | `new_question`／`clarification`／`uncertain` | 仅在有待办时参与切换，显式用户动作优先 |
| `is_clear` | 布尔值 | 是否能安全进入检索 |
| `questions` | 0～3 条非空、去重的独立问题 | 清楚时至少 1 条；不清楚时必须为空 |
| `clarification_needed` | 可空文本 | 不清楚时必须为一条具体、可回答的询问 |
| `failure_reason` | 可空、非敏感代码 | 模型异常时设置，不能被当成正常澄清 |
| `source` | `model`／`cache`／`safe_fallback` | 用于审计成本与降级路径 |

程序需校验原问题中的型号、数值、否定与范围未被无依据改写。只把分析后的独立问题用于检索；不能把摘要、待办拼接串当作 PDF 引用。

## 3. 标准答案题目 `GoldCase`

当前使用版本化 UTF-8 JSON 文件[标准答案集](gold-cases-v1.json)，由用户明确批准后登记为 `gold-1.0`，15 题均有带时区的人工审核记录；审核者是当前会话项目维护者，不是 Codex。验证模式定义于 `backend/scripts/validate_v4_gold_dataset.py`；原五题草案文件保留不覆盖。见[审核稿](gold-cases-review.md)及[确认来源](gold-review-approval.md)。

| 字段 | 含义 | 约束 |
|---|---|---|
| `case_id`、`dataset_version` | 题目与题集版本 | 稳定、唯一；修改标准答案需更新版本 |
| `case_type` | `answerable`／`unanswerable`／`clarification_flow` | 只有适用类型进入对应 RAGAS 指标 |
| `document_id`、`document_sha256` | 来源文档身份与内容指纹 | 索引/文档版本不一致时禁止正式评分 |
| `question`、`history_fixture` | 用户原问题与必要的前置会话 | 交互题需指定逐轮输入和预期转移 |
| `reference_answer` | 经复核的标准答案 | `answerable` 必填；可以是语义等价范围而非唯一措辞 |
| `source_spans` | 文档页码、章节、逐字引文 | 可回答题至少一个来源位置 |
| `required_facts`、`ordered_facts`、`forbidden_claims` | 必须覆盖、有序步骤及不得出现的事实 | 列表非空项且不重复；有序步骤必须同时登记为必答事实 |
| `expected_behavior` | 回答、澄清或证据不足 | 无答案题不能强行填事实答案 |
| `review_status`、`reviewer`、`reviewed_at`、`review_kind` | 草案/已审核及复核记录 | 草案不填审核记录；已审核须具备人工审核者、带时区时间和 `review_kind=human` |
| `flow_steps`、`flow_expectation_basis` | 逐轮输入、动作、问题、待办和检索预期及协议依据 | 交互题至少两轮；协议预期不冒充 PDF 事实 |
| `unanswerable_reason`、`absence_check` | 无答案理由、核对页码和未出现的检索词 | 无答案题须覆盖全部页码且无事实型标准答案；关键词缺失不是语义缺失的充分证明 |
| `negative_response_fixture` | 人工构造的漏步骤答案及预期遗漏 | 只用于后续评估测试，不是本阶段系统实测答案 |

题集顶层保存 `schema_version=1`、`dataset_version`、`status`、`source_document` 与 `cases`。来源清单含文档 UUID、文件名、SHA-256、严格整数页数和文档版本。题目中的身份、指纹及题集版本必须与清单一致；所有引文在指定页核对，仅允许忽略排版空白，不能修正数值或标点。

验证器输出 `valid`、`formal_ready`、`unreviewed_case_ids`、逐题来源检查与错误明细。普通检查允许合法草案通过，但正式准入必须是顶层和全部题目均已审核且来源检查全通过；混合审核状态会拒绝整个题集，不静默排除未审核题。`eligible_case_ids` 只在整体正式准入后给出，`ragas_case_ids` 进一步限于 `answerable`。题集验证器只核对 PDF 本体；阶段 D 运行器另核对清单文件与源文档聚合指纹，不初始化向量库。当前批准版本已通过题集准入，不等于实际回答通过。

2026-10-08 新增 [candidate-2.0](gold-cases-v2.json)，保持现有 `GoldDataset` 模式与旧默认路径不变，23 个场景全部为草案。配套 [量规](gold-cases-v2-rubrics.json)登记可选事实及逐字来源、行为条件、语义正负例、11 个知识组、主要题／挑战题／交互／无答案分层；这些是独立审核资料，当前验证器及 RAGAS 不自动读取，不冒充已实现语义评分。

澄清规约区分真实入口 E01 与 [S01–S08 合成待办起点](clarification-state-fixtures-v2.json)。端到端分支第二轮仅在首轮状态、待办与未检索前置均成立时执行，否则记 `blocked_by_prerequisite`。合成起点使用合法 `ThreadState` 的独立字段，不能塞进普通 `history_fixture` 或注入线上会话；结构检查不等于模型通过。现有采集器尚不加载夹具或执行门槛，流程运行器对齐待办明确留在任务中。

Q1～Q5 为首批种子题；至少再覆盖 10 个不同场景，包括同义表述、代词追问、并列问题、待澄清补充/换题/取消、无证据、数值冲突和故意遗漏步骤。新增题不能仅是同一句的小幅换词来虚增样本量。

## 4. 离线评估运行 `EvaluationRun`

| 字段 | 含义 |
|---|---|
| `run_id`、`started_at`、`dataset_version` | 运行身份与题集版本 |
| `index_version`、`document_sha256` | 被测知识库快照；不匹配则拒绝正式运行 |
| `answer_model`、`judge_model`、`ragas_version` | 模型与指标实现版本；Judge 与回答模型相同须标记探索性 |
| `case_results[]` | 每题原问题、最终独立问题、检索候选排序、实际送入生成器的上下文、回答、引文、分项结果与人工复核 |
| `cost` | 回答与 Judge 分别统计调用、实测/估算 Token、耗时 |

实际运行器使用 `judge_cost`、逐题 `answer_cost/model_trace`、分项 `metrics.*.cost/duration_ms`，合成冒烟另有 `smoke_answer_cost`。usage 缺失时列出 `unknown_usage_calls`，不把未知 Token 当作零成本。模型名、模型 digest、关键依赖版本与预先设定的 Judge 配置分别登记；`formal_acceptance` 不会由高分自动置真。

`raw_retrieval_candidates` 是主图合并后的候选记录，另存 `retrieval_batches` 保留查询/分支次序和工具返回排序。检索指标使用 `tool_results_in_query_and_rank_order` 层级，Groundedness 使用 `generation_contexts`；`generation_summary` 只登记辅助缺口，不能当作原始 PDF 证据。

五项分数为可空值；不适用时记录 `not_applicable_reason`，Judge 失败时记录 `evaluation_error`，不能补 0 或沿用旧分数。答案是否完整，尤其 Q3 安全步骤，必须同时保留按 `required_facts` 的人工核验结果。

`literal_probe.potential_missing_facts` 仅是字面匹配提示，`is_semantic_verdict=false`，不能判断同义表达、执行顺序或安全正确性。人工记录始终先为 `pending`；本阶段没有虚构审核者或结论。

## 5. 在线核验结果 `OnlineVerification`

`schema_version=2`；包含 `request_id`、`thread_id`、`evidence_status`、`citation_status`、`numeric_status`、`completeness_status`、`reason`。状态值为已核验/存在问题/未评估（按字段适用性细化）；**无 `overall` 百分比分数**。`citation_status=verified` 只表示引用能定位，不推出答案事实或步骤完整。
