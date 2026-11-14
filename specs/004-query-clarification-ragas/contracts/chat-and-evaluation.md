# 聊天、澄清与离线评估契约

**状态（2026-10-07 首批结束）**：在线请求、澄清、版本 2 核验与离线运行器已实施；题集已获用户批准，首批真实采集/评估已结束并达到 80 次 Judge 上限。完整评分、回答人工签收及正式总验收未完成。现有认证与在线事件不变，见[本批报告](../formal-ragas-report.md)。

## 1. 在线请求：`POST /chat/stream`

现有 `ChatRequest` 支持可选 `action`：

```json
{
  "question": "PX-200 的过流保护后如何恢复？",
  "thread_id": "same-thread-id",
  "action": "auto"
}
```

`action` 取值：`auto`（默认，由一次模型分析判断）、`continue_clarification`、`new_question`、`cancel`。除 `cancel` 外，`question` 必须非空且不超过现有 2000 字符；`cancel` 必须指定已有 `thread_id`，可省略或留空 `question`。显式动作优先于模型判断；旧客户端不传 `action` 时保持 `auto`。若同线程已有进行中的请求，应返回明确的冲突/忙碌结果，不能同时覆盖待办。

### 分析与澄清事件

新 SSE `analysis` 事件只给出非敏感概要，不包含整段摘要或文档正文：

```json
{
  "schema_version": 1,
  "request_id": "uuid",
  "thread_id": "same-thread-id",
  "is_clear": true,
  "relation": "new_question",
  "questions": ["PX-200 的过流保护后如何恢复？"],
  "source": "model"
}
```

新 SSE `clarification` 事件仅在仍需补充或关系不确定时发送：

```json
{
  "schema_version": 1,
  "request_id": "uuid",
  "thread_id": "same-thread-id",
  "pending": true,
  "question": "请说明你指的是哪个设备型号？",
  "allowed_actions": ["continue_clarification", "new_question", "cancel"]
}
```

澄清请求不发送普通 `answer`、`retrieval`、旧 `evaluation` 或 `verification`；其 `complete.status` 为 `clarification`。取消时 `complete.status` 为 `cancelled`，分析模型调用为 0。模型分析输出无效、超时或预算耗尽时，发送可追踪的 `error`、`usage`、`complete.status=failed` 并保留待办，不发送“分析成功”的 `analysis`。

并发冲突通过 SSE `error.code=THREAD_BUSY`、`complete.status=failed` 表示，不改变待办。未知线程取消使用 `THREAD_NOT_FOUND`；有线程但无待办的补充使用 `NO_PENDING_QUERY`。请求校验错误返回 HTTP 422（例如空普通问题、超过 2000 字符或取消缺少线程）；已有登录权限校验保持不变。自动模式下不完整补充可能通过状态保护变为 `uncertain/source=safe_fallback`，追踪中记录 `decision_guard`。前端仅在 `complete.status=completed/cancelled` 后清除已有澄清卡，失败则保留。

## 2. 在线核验事件：替代固定评分

新 SSE `verification` 事件使用显式版本和枚举状态，不含 `overall/relevance/faithfulness/completeness` 的伪精确百分比：

```json
{
  "schema_version": 2,
  "request_id": "uuid",
  "thread_id": "same-thread-id",
  "evidence_status": "found",
  "citation_status": "verified",
  "numeric_status": "not_evaluated",
  "completeness_status": "not_evaluated",
  "reason": "已定位引用；操作步骤完整性尚未自动核验。"
}
```

`evidence_status`：`found`／`insufficient`／`not_evaluated`；`citation_status` 与 `numeric_status`：`verified`／`issue_found`／`not_applicable`／`not_evaluated`；`completeness_status`：`verified`／`issue_found`／`not_evaluated`，仅当有可靠的完整性检查时才可用 `verified`。前端不得把单项 `verified` 合成为总体可信度。

当前实现：仅有已知 `[E1]` 编号只能证明引用对象存在，仍为 `not_evaluated`；未知编号为 `issue_found`。生成器实际展示的 `“原文” [来源：文件，第N页，章节]` 必须同时匹配逐字片段、文件、页码及章节，才能报告 `verified`；片段或位置不匹配且有证据记录时为问题，没有充分记录时为未评估。数值条件和步骤完整性尚无可靠语义核验，有证据时均保留 `not_evaluated`；无证据时数值条件为 `not_applicable`。没有在线 Judge，也不因引文可定位而宣称答案完整。

迁移顺序：先增加服务端和前端对新事件的契约测试；同一发布批次切换前端展示；再停止发送旧 `evaluation` 固定分数事件。旧客户端若收不到 `evaluation`，最多不显示评分，不能继续看到旧的虚假分数。现有 `answer`、`retrieval`、`usage`、`complete` 保持可用。日志中的请求标识与事件一致。

## 3. 离线题集与评估输入

离线工具不暴露新的在线 API。题集文件按[数据模型](../data-model.md)维护；正式评估只读取 `review_status=reviewed` 且 `document_sha256` 与被测知识库一致的题。典型可回答题需有 `question`、`reference_answer`、至少一条 `source_spans`、`required_facts` 和审核记录。无答案题使用 `expected_behavior=insufficient_evidence`，其不适用的 RAGAS 指标记 `not_applicable`。

已实现的只读验证入口是 `python -m scripts.validate_v4_gold_dataset`：普通草案校验可返回成功，但不会将草案加入正式准入列表；加 `--require-reviewed` 后，任何未审核题、PDF 指纹失配或引文失败都会返回非零状态。全部题集须通过，而不是筛掉失败题后计算好看的均值。校验成功不等于模型答对，也不证明正式索引已匹配；阶段 6 的评估运行器还须登记并检查实际索引版本。

RAGAS 对适用题目的最小输入：

```json
{
  "user_input": "经过会话解析的本轮独立问题",
  "reference": "人工核对的标准答案",
  "response": "系统实际生成的答案",
  "retrieved_contexts": ["实际进入评估范围的原文证据，保留顺序"]
}
```

运行记录还必须另存原始用户问句、前置会话、原始检索候选排序、最终生成上下文、来源页、答案模型与 Judge 模型、RAGAS 版本、每项指标原始结果及人工复核。检索指标与回答支撑指标使用哪个上下文层级须在运行配置中显式声明，不能混用或事后替换。指标实现与字段适配在阶段 D 通过固定一题的兼容性冒烟确认；任何不适用/执行失败项都不能记成 0 分。

离线入口为 `python -m scripts.evaluate_v4_ragas`，依赖仅见 `backend/requirements-eval.txt`。`--smoke` 只使用内置合成来源，单题实际回答再送入五项指标，不读取正式题集、PDF 或索引。正式模式先拒绝未审核题集，再读取 `--inputs` 实际 Graph 快照和 `--index-manifest`；PDF 指纹、索引清单字节指纹、源文档聚合指纹及全部题目身份必须匹配。它不初始化或重建向量索引，也不是完整向量库一致性扫描。

快照顶层为 `schema_version=1/capture_kind=graph_run`，保存题集版本、PDF SHA-256、索引版本（清单文件 SHA-256）、回答提供商 `ollama`、回答模型和全部逐题输出。`capture_graph_result()` 从实际运行结果导出；调用者须真实执行对应会话和交互，不能复制标准答案充当实际输出。2026-10-07 新增 `python -m scripts.capture_v4_formal --capture-local`，在正式索引的只读隔离快照上执行当前 Graph，逐题保存真实输出；不是 UI 验收。

批量采集每题一个独立 `thread_id`，按已批准的 `history_fixture` 初始化有类型的历史，不凭空补助手消息。交互题的 `flow_turns` 保存每轮实际结果、动作、待办、用量与核验；`flow_checks` 是协议/字面预期比较，不是语义评审。题级 `answer_cost` 汇总全部轮次，不只取最后一轮。可回答题意外进入澄清时记录 `run_error=unexpected_clarification`，不当作正常答案评分。

`retrieval_batches` 保存每次 Child 工具返回的查询及候选原始排序，三项检索指标使用该层；`generation_records/generation_contexts` 保存实际送入答案生成器的记录，Groundedness 使用该层。摘要另存为 `generation_summary`，不拿摘要或标准答案补充检索证据。参考答案仅用于 Accuracy、Precision、Recall。所有交互题/无答案题暂记不适用，留给人工或独立交互测试。

Judge 必须显式指定已安装的本机模型；仅允许回环地址，禁用环境代理、重定向和 RAGAS 遥测，不自动下载或使用云端。默认总模型 HTTP 调用上限 16、每项超时 60 秒；Instructor 和评级重试限制为 1。成本来自服务返回的 usage；缺少 usage 记录为未知而不是估算为零。结果保存至 `backend/tmp/v4-evaluations/<run_id>.json`，失败项值为 `null`，记录异常类型；原始分数保持库返回精度。原始理由/轨迹若库未提供则保持 `null`，不伪造解释。人工结论默认为 `pending`。

## 4. 验收契约

- 清楚问题走分析→检索→回答；不清楚问题走分析→澄清，且不会生成无证据答案。
- 待澄清时明确新题不会与旧问题合并；显式取消不会继续检索旧题。
- 在线不调用离线 Judge；`usage` 能区分分析、摘要、生成与离线评估成本。
- Q3 故意缺少“断开负载/等待完全放电”时，在线不能显示“完整可信”，离线人工必答点检查明确标出遗漏。
- 权限、`request_id`、来源引用和现有 SSE 基本事件保持一致；新事件应有前后端契约测试。
