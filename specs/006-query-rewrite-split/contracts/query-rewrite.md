# Contract: 三字段问题改写与现有聊天接口

状态：2026-10-11，A–D工程检查已完成；E首批RW01/RW02通过、RW03失败、14未运行。F工具和39项工程检查完成，首次Q16入口因恢复子问丢共同条件failed、完整答案not_verified，另两题未运行。目标代码`model_schema.py/query_analysis.py/graph.py/pipeline.py`本轮未修改；全部真实质量尚未通过。见[F首次真实报告](../phase-f-first-20261011-report.md)。

## 模型结果

```json
{"is_clear":true,"questions":["PN8733 的启动电压是多少？"],"clarification_needed":""}
```

```json
{"is_clear":false,"questions":[],"clarification_needed":"你指的是哪一个设备的什么参数？"}
```

严格三个必填字段、禁止额外字段、bool/list[str]/str类型、≤3问、每问≤2000字符。内部空白不折叠；判重不改变正文。clear需非空questions且空澄清；unclear需空questions且非空澄清。

## 基础失败与路由

| 情况 | 处理 |
|---|---|
| 非JSON/缺字段/额外字段/类型错/空或重复/四问/交叉约束错 | failed / invalid_model_output，0检索，0自动重试 |
| 模型不可用 | failed / model_unavailable，不切云、不伪装改写 |
| 模型或整请求到期 | failed / timeout，同一个deadline |
| 历史/窗口/预算不足 | 沿用真实原因，不裁掉关键条件或加隐藏调用 |
| 有待办+auto | clarification，提示选择动作，source=safe_fallback，兼容relation=uncertain |
| 有效模型is_clear=false | clarification，保存原待办/明确补充，不检索 |
| 有效模型is_clear=true | 现有Send分支，模型Loop决定检索动作 |
| 格式有效但数字/题意失真 | 本版没有入口语义拦截；真实质量验收失败，记录原始输出 |

`constraint_mismatch`不再由问题入口新增产生；其他既有摘要/答案检查的原因不在本次取消范围。引用/工具/权限边界继续生效。

## API与SSE兼容

聊天请求继续`question/thread_id/conversation_id/action`，不新增接口。三个动作按钮复用。新题不注入pending；继续必须存在pending；取消零模型。

保留现有`analysis/query_rewritten/clarification/usage/complete`事件形状及版本1。内部预算键仍为query_analysis，显示名为“问题补全与拆分”。`relation`若存在仅作动作适配兼容字段，metadata/界面说明来源是明确动作，不能声称模型分类。

`analysis` 和 `query_rewritten` 增量元数据为：`source=model/cache/safe_fallback`、`relation_source=action/pending_state`、本轮 `action`、`budget_node=query_analysis`、`model_call_id`、`duration_ms` 和 `replayed=true`。有实际入口调用时关联其真实 ID 与耗时；缓存和状态分支的调用 ID/耗时为 null，不伪造模型调用。`query_rewritten.decision_source` 映射为 model/cache/runtime_guard；未选择动作的待办关系来源为 pending_state。前端兼容缺少这些增量字段的旧版本 1 事件。

`query_rewritten`表明已经得到处理结果，不保证正文发生改变。保持原文也要能看到本轮入口模型或缓存来源。无效输出用failed事件，不假装进入澄清或资料不足。

SSE仍在完成后回放，事件记录真实执行顺序而非宣称实时推送；原始系统提示、全历史和私有推理只按既有本地诊断访问范围处理。

## 输入/输出责任

- 原题是回答与条件的依据，子问题是检索目标；每分支同时收到两者。
- 比较目标保留在原题并由最终汇总覆盖，不能依子问题数量声称已完整回答。
- 不增添额外语义自检、自动数值替换或运行时意图分类字段。
