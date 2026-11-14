# 数据模型与状态转移

**状态**：A/B与C工程已按此契约实施；2026-10-09运行验收仍有失败，实际结果见phase-c-report.md。沿用现有ConversationMemory唯一线程状态。

## 1. ModelMessage与ToolCall

ModelMessage字段：role(system/user/assistant/tool)、content、tool_calls、tool_call_id、name。ToolCall字段：id、name（两个工具白名单）、args字典。保留模型原始调用名称/参数；适配器只做协议形状转换，不补业务查询或替模型选Parent。

Ollama和兼容提供者统一返回以上结构；assistant工具调用与所有tool结果一一对应。缺少上游ID时可生成稳定内部ID并标记来源，不能改变动作；坏参数返回对应错误ToolMessage。工具消息不进入普通聊天历史。

## 2. RequestRun

字段：request_id、thread_id、原始问题、解析问题列表、index_version、protocol_version、模型版本/上下文窗口、请求开始/截止时间、共享预算、分支列表、证据注册表、最终答案、终态、usage。

最多三个分支共享预算。线程记忆写入仍检查state_version；同线程请求冲突沿用串行或明确拒绝，不能混合两个请求的证据。

## 3. BranchRun

字段：branch_id、question_index、question、original_question、user_conditions、messages、context_summary、retrieval_keys、query_history、evidence_ids、模型/工具次数、轮次、剩余配额、候选答案、候选修正次数、终态和原因。

正常转移：ready → model_decision → tool_requested → tool_completed → context_ready → model_decision。

完成转移：model_decision → answer_candidate → citation_check → answered/partial/insufficient。

有限修正：citation_check/协议错误 → 带错误反馈的model_decision；最多一次候选修正且服从配额。资源/工具错误回填对应观察，不由程序选择下一个业务动作。取消、超时、预算或上下文资源不足可直接进入运行终态，标明runtime_guard。

## 4. EvidenceRecord与Claim

EvidenceRecord：evidence_id、document_id、child_id/parent_id、文件名、页码、章节、完整raw_text、索引版本、产生它的tool_call_id/decision_id、检索分数/模式。原文不可变；压缩摘录记录原证据ID和位置。候选与最终模型输入分别保存，不能把原始召回当作实际送入上下文。

Claim：kind(document_fact/user_condition/derived_result)、text、citation_ids、user_input_refs、input_refs、可选简短比较/公式、validation_status。标签由模型生成，不自动等于已验证；user_condition必须回指真实用户输入，不能把猜测值标成用户条件。document_fact有出处，derived_result列出输入来源；一般数值/语义完整性未独立审核仍not_evaluated。

## 5. BranchAnswer

字段：status(answered/partial/insufficient/failed/cancelled)、answer、citations[{citation_id,quote}]、claims、missing_information、stop_reason、stop_origin(model/runtime_guard)、verification。

answered/partial必须有可定位来源；insufficient说明具体缺口及实际查询记录。没有检索尝试时不能宣称查证后无资料，可反馈NEEDS_RETRIEVAL_ATTEMPT让模型自己选择工具。failed区分模型不可用、格式错误、工具错误、引用失败、上下文/预算/时间停止。最终汇总只能使用各分支答案及其注册证据，新增引用需已有对应证据。

## 6. DecisionEvent与预算

DecisionEvent：decision_id、model_call_id、branch_id、iteration、action、tool_calls、source(model/cache/runtime_guard)、可选brief_reason、公开缺口、耗时/Token。brief_reason只使用模型明确提供的简短动作理由；模型未给出时不伪造推理。

共享预算：request_limit、已预留调用、按节点用量、分支配额、汇总槽、共享辅助槽、逻辑工具请求数、实际工具执行数、缓存命中、deadline。每次调用前原子预留；工具多请求分别计数，模型按实际invoke次数计数。摘要不抢回答槽。

## 7. 线程与缓存

线程继续区分近期普通消息、summary_backlog、有效摘要、pending_query、pending_clarifications、phase。摘要失败保留原历史；澄清失败不污染独立新题。当前procedure标记不再作为答案覆盖开关，可迁为模型声明的question_kind或需求，不承担程序语义路由。

工具缓存按query/Parent、index_version及请求权限隔离；若缓存模型决定，键必须含问题、历史指纹、可用证据、模型/提示词/协议版本。模型决定缓存非首期必需；工具缓存先复用。所有缓存事件关联原调用且显示source=cache，不当作本轮新模型调用。
