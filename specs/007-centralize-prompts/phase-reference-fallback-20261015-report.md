# 唯一对象代词代码兜底实现与 RW07 复测报告

日期：2026-10-15。用户明确要求为唯一对象代词增加代码兜底。本阶段只修改入口分析后处理：当模型返回不清楚、当前问题含明确中文代词、历史中恰好只有一个型号样式对象时，将该对象写回当前问题；多个对象、没有对象或没有明确代词时继续使用原澄清路径。

## 实现

- 在 `backend/app/rag/query_analysis.py` 增加 `unique-reference-fallback-v1` 版本标识，并加入入口缓存键，避免旧的澄清结果复用。
- 从对话历史和摘要提取型号样式标识（例如 `PN8733`、`PX-200`）。
- 只处理“它／其／这个设备／该设备／这个型号／该型号／那个设备”等明确代词；历史中必须恰好有一个候选对象。
- 兜底只替换对象名称，不添加答案、设备类型、阈值或其他事实；多个候选对象仍澄清。
- 原始模型首答和 `reference_fallback` trace 均保留，最终业务结果才进入清楚分支。

## 结果

RW07真实复测：

- 历史：`PN8733 的启动电压是多少？`
- 当前问题：`它的恢复条件是什么？`
- 模型原始首答：`is_clear=false`，要求说明 PN8733 是什么设备。
- 代码兜底后：`is_clear=true`，问题为 `PN8733 的恢复条件是什么？`。
- 人工验收：**通过**。

本次批次为 **1通过、0失败、0待定、0未运行**；模型调用 1 次，模型等待 45.666 秒，工具、检索、云端、Judge、缓存和自动重试均为 0。

## 工程验证

| 命令 | 结果 |
|---|---|
| `python -m pytest -q --basetemp=.pytest-tmp-reference-fallback tests/unit/test_query_rewrite_v1.py -k "not test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity"` | 58 passed，1 个旧 v3 prompt 措辞断言排除 |
| `python -m pytest -q --basetemp=.pytest-tmp-reference-fallback tests/unit/test_v4_query_analysis.py -k "not test_context_prompt_limits_history_and_preserves_unconfirmed_conditions"` | 16 passed，1 个旧 v3 prompt 措辞断言排除 |
| `python -B output/test_pronoun_rw07_fallback_20261015.py` | 退出 0；真实 RW07 通过 |

被排除的两个断言只检查旧 v3 中文 prompt 的固定措辞，当前 v6-zh 已不包含这些旧文本；它们不是本次代码兜底的失败。新增唯一对象和多对象保守性测试均通过。

## 限制与证据

该兜底目前针对型号样式标识和中文明确代词，不能解决多个对象、普通名称无型号格式、缺少具体目标（如“它的怎么样？”）或复杂场景条件补全。完整17题、端到端检索和答案质量未运行。

- [批次摘要](../../output/prompt007/pronoun-rw07-fallback-20261015/run/summary.json)
- [基线与版本指纹](../../output/prompt007/pronoun-rw07-fallback-20261015/baseline.json)
- [RW07原始模型首答及兜底结果](../../output/prompt007/pronoun-rw07-fallback-20261015/run/RW07.raw.json)
- [RW07审阅](../../output/prompt007/pronoun-rw07-fallback-20261015/run/RW07.review.json)

**报告后暂停，等待用户验收。**
