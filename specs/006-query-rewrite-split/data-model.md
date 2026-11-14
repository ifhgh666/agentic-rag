# Data Model: 问题补全与拆分 V1

设计日期：2026-10-10。进度更新：2026-10-11，A–D工程检查已完成，E首批在RW03失败后停止。F采集工具和39项工程检查完成；首次Q16入口failed、完整答案not_verified，另两题not_run；[F首次真实报告](phase-f-first-20261011-report.md)后暂停。工程与真实质量结论以最新阶段报告为准。

## 1. 模型输出 QueryAnalysis

| 字段 | 约束 |
|---|---|
| `is_clear` | 必填严格bool，不把字符串true转换成bool |
| `questions` | 必填字符串列表，最多3；正文只trim首尾；非空且判重副本规范化后不重复 |
| `clarification_needed` | 必填字符串，不接受null；清楚时必须为空字符串；不清楚时必须具体非空 |

禁止额外字段，不输出`relation/requires_procedure/source/failure_reason`。`is_clear=true`需1–3问；`false`需空问题列表。每问长度≤2000字符，整体输入/输出继续服从窗口。协议检查不验证题意、数字、否定或条件依赖。

## 2. 入口输入与内部运行结果

- `original_query`：API现有首尾trim后的本次原题，内部字符不变。
- `recent_messages/conversation_summary`：现有普通记忆；摘要只用于理解。
- `pending_query/clarifications`：仅显式继续补充时传入原题和确认补充。
- `action`：沿用auto/continue_clarification/new_question/cancel；系统状态，不新增模型字段。
- 内部运行元数据继续保留`source/failure_reason/model_trace`；`analysis_relation`从动作适配，`analysis_relation_source`记录 action/pending_state。旧`requires_procedure`无新的语义替代。

## 3. 主图与分支

继续使用现有`MainState.questions/rewritten_query/question_is_clear/clarification`，不并行维护两套同义字段。`rewritten_questions`是设计含义，映射现有`questions`即可。

`original_query`不可被questions覆盖；`resolved_original_question`为原待办及确认补充的原始组合。每个分支接收完整原题和本分支问题，原题含最终比较目标。单分支直接采用Loop答案，多分支现有模型汇总；共享证据身份和引用定位保留。

## 4. 状态转换

| 既有状态/动作 | 入口行为 | 后续状态 |
|---|---|---|
| idle + auto | 0或1次入口（缓存/模型） | 清楚→answering；不清楚→awaiting_clarification |
| awaiting + auto | 0次模型，返回动作选择 | 原待办原样保留 |
| awaiting + continue | 原题+确认补充+本次补充，一次入口 | 清楚→answering；仍不清楚→原待办+确认补充 |
| any + new_question | 屏蔽旧待办，普通历史可用 | 新题流程；成功后不混入旧待办 |
| any + cancel | 0次模型/工具，清待办 | idle |
| idle + continue | 既有NO_PENDING_QUERY，0次模型 | idle |
| 模型、下游失败或timeout | 不用生成文本提交记忆 | 恢复请求开始前的待办版本 |

保留现有ThreadState版本/请求租约/回滚机制。成功后普通user历史存真实原题；补充完成时保存原题及每次确认补充的原始组合，不能存模型生成子问题。assistant回答仍是历史对话，不当作PDF证据。

## 5. 缓存与日志

2026-10-11仅E采集状态追加：显式继续模式在单题failed/uncertain后处理下一题，批次覆盖完但存在失败为 `completed_with_failures`；该状态不进入产品API/SSE。续测引用保留原人工失败状态和首答哈希，不生成新的前缀调用。见[继续规则](phase-e-continue-policy-20261011.md)。

入口缓存键：原题精确哈希、thread、摘要/普通历史/pending/确认补充/action哈希、索引版本、提供者与模型身份、`query-rewrite-v1`契约/提示版本。TTL300秒，容量256不变。缓存只保存有效解析结果；不可复用旧QueryDecision结构。

本地已批准诊断保存原题、上下文来源范围、原始模型输出、节点/调用ID、耗时和错误。公共事件只展示必要原题/子问题、来源、数量和耗时，不复制完整历史或提示词；不增加调试HTTP接口。
