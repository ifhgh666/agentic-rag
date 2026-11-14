# 016 数据与状态

## 主图 State（MessagesState）

| 字段 | 类型/行为 |
|---|---|
| messages | 消息 reducer，支持按 ID 更新与 RemoveMessage |
| questionIsClear | bool，是否进入研究路由 |
| conversation_summary | string，普通历史滚动摘要，与研究摘要独立 |
| originalQuery | string，本轮聚合的原题及必要补充 |
| pendingQuery / pendingClarifications | string / list[str]，未解决原题及累计补充 |
| rewrittenQuestions | list[str]，参考入口产物，不按本地代码强制三项 |
| agent_answers | list[dict]，累加 reducer；新轮 summarize_history 用 reset 哨兵清空 |

普通消息筛选排除内部 name/tool call 消息；回答前保留 3 条近期普通消息，旧消息合并摘要，回答加入后为近期 4 条设计。参考行为不另行接旧 ConversationMemory。

## 研究 AgentState（MessagesState）

| 字段 | 类型/reducer |
|---|---|
| question / question_index | string / int，Send 的问题和稳定聚合序号 |
| messages | 单分支研究消息；压缩后保留首问，移除后续旧消息 |
| context_summary | string，模型研究压缩结果及已检索标识 |
| retrieval_keys | set[str]，set union，标识搜索/Parent，引导避免重复而非执行闸门 |
| retrieved_contexts | list[str]，按正文首次出现追加去重 |
| final_answer / agent_answers | string / list[dict]，收集后交主图按 question_index 聚合 |
| tool_call_count / iteration_count | int，add reducer，含当前 orchestrator 返回批次；阈值语义见规格 |

QueryAnalysis 三个必填字段为 `is_clear: bool`、`questions: list[str]`、`clarification_needed: str`，保持参考默认解析，不增加字段联动/strict/硬列表上限。ToolMessage.content 为参考字符串，artifact 为本次真实记录；artifact 不注入额外模型决策。

## 会话状态转换

| 当前状态/输入 | 下一状态 |
|---|---|
| 普通轮完成 | checkpoint 保存普通历史/摘要，next 为空 |
| 入口判不清楚 | pending 保留；中断在 request_clarification 前 |
| pending + auto/continue | 追加补充，恢复图；可继续澄清或进入研究 |
| pending 入口传输失败 | 保留未解决原题并释放请求互斥；不承诺全部节点事务回滚 |
| 普通轮失败 | 清理失败续跑，不能变成澄清待办 |
| new/cancel | 删除未完成待办尾部，保留已完成历史与摘要；new 再运行新题，cancel 结束 |

checkpoint 是在线事实来源；RequestObservation 是请求级事件、用量和本次来源集合，不保存会话事实。进程内会话重启丢失；同线程互斥，跨线程独立。Sources 与 artifact 的关系及公开投影见 [聊天契约](contracts/chat.md)。

## B 采集侧车记录（不加入产品状态）

manifest 保存 provider/model/temperature/seed、端点 hash、凭据已配置标识、源码/采集器/fixture hash 和临时索引版本；不保存端点明文或凭据。每个 case 有不可覆盖的 events.jsonl/raw.json 与 Codex review.json，summary 仅汇总 passed/failed/pending/not_run；未通过 review 不提交下一输入。失败路径 Token 估算零值与远端实测未知分开记录。具体冻结/停止规则见 [B 协议](phase-b-protocol.md)。
# R 补充：模型传输策略

正常参考图模型实例在构造时确定传输模式：`openai_compatible` 且 `llm_model == 'deepseek-flash'` → `extra_body.thinking.type='disabled'`，由同一实例的结构化、工具绑定及普通调用继承。无新配置字段或会话状态，不持久化 reasoning_content，不影响 legacy 实例、其他模型或 Ollama。

# B 续测记录补充

continuation.json 关联只读 R B01 请求/首答/审阅/事件和报告哈希、续测包装 hash、协议 hash、固定 B02–B05 顺序及空 model_override。每个剩余 case 仍使用原始 fixture 字段和同一线程标识；B02/B03 必须保持 clarify 线程相同。此为采集记录，不新增产品状态。

## D 真实 PDF 采集记录

复用 B 的 events/raw/review/summary 记录形状；fixture 保留原 gold Q1–Q4 和历史，标准答案仅供采集后审阅，不进入模型。manifest 增加 PDF hash、正式索引版本/点数、真实 Dense 身份/维度、原 BM25 词表 hash 和准备阶段模型调用为 0 的标识。准备失败单独保存，不混入首答计数。详见 [D 协议](phase-d-real-pdf-20261028-protocol.md)，无新增产品或 checkpoint 字段。

## E 全量采集与比较记录

每轮以 `Qn-Tm` 独占保存 raw/events，保留 action、request_id、checkpoint、实际 answer/clarification/error 和用量；场景命令及 watchdog 单列。capture-summary 只声明采集覆盖，不宣称语义通过。comparisons/review 关联原题/正确答案或预期行为/各轮原答/逐事实覆盖/来源/行为差异及判定，汇总按 case_type 分母。前题失败不改变下一条原定输入。无新增产品状态或 API 字段。

