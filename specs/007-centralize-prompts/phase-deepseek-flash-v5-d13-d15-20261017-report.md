# rewrite-prompt-v5 + DeepSeek Flash：D13/D14/D15 真实复测报告

日期：2026-10-17（America/Los_Angeles）  
授权范围：用户要求“用 `rewrite-prompt-v5` 测试”，只重测此前失败的 D13、D14、D15 三道入口题。

## 结论

本轮已将运行时入口提示词切换为用户提供的 `rewrite-prompt-v5` 原文，并使用当前配置的 DeepSeek Flash 对 D13、D14、D15 各真实调用一次。结果为 **0 通过、3 失败、0 待定、0 未运行**。

三题的模型结构输出均可解析，且 `source=model`；模型都把原题保留为一个问题并判定 `is_clear=true`，没有按 v5 中的拆分上限、独立信息需求和澄清边界完成预期处理。

## 逐题结果

| 题目 | 模型首答 | 验收结论 |
|---|---|---|
| D13 | `is_clear=true`；只返回一个问题：`PX-200 输入电压为 245 V，持续 400 ms，是否触发保护，如果触发如何恢复？` | 失败。预期拆成“是否触发保护”和“如果触发如何恢复”两个问题，且恢复子问题保留共享条件。 |
| D14 | `is_clear=true`；只返回一个问题：`PN8733 和 PX-200 的过流阈值分别是多少？哪个更高？` | 失败。预期拆成 PN8733、PX-200 两个阈值查询，把“哪个更高”留给后续汇总比较。 |
| D15 | `is_clear=true`；只返回一个问题：`PX-200 的启动电压、过流阈值、维护周期和记录保留期限分别是什么？` | 失败。原题有四个独立需求，预期超过最多三项时先澄清并请求选择三项。 |

## 配置与调用记录

- provider：`openai_compatible`
- model：`deepseek-flash`
- base URL：`https://api.deepseek.com/v1`
- prompt 版本：`rewrite-prompt-v5`
- prompt 文本 SHA-256：`6abfafc8117886ba54375d47e0046cbc2765c9a3b190967f27b0929739999862`
- 真实调用：3 次，每题 1 次；自动重试 0 次
- D13：1550 ms（模型 trace 1547 ms），输入 1180、输出 100 tokens
- D14：1300 ms（模型 trace 1297 ms），输入 1175、输出 89 tokens
- D15：1436 ms（模型 trace 1435 ms），输入 1176、输出 83 tokens
- 入口分析之外的检索、工具、Judge 和其他模型调用：0 次
- 三题均记录 `structured_mode=json_object`、`structured_fallback=true`；结构结果已成功解析
- API Key 未写入报告或测试产物

## 代码层边界

本轮只替换 `backend/app/rag/prompt.py` 中的入口提示词版本和正文，没有新增代码层语义校验、拆分器或强制改写逻辑。三题均为模型原始决策，没有触发 `reference_fallback`。当前工作区运行时仍保持 `rewrite-prompt-v5`，此前 v6 中文版本已备份为 `output/prompt007/deepseek-flash-v5-d13-d15-20261017/prompt-before-v5.py`。

这批只验证入口问题分析，不代表检索、答案生成、来源引用或完整端到端质量。旧报告和旧首答保持不变。

## 证据

- 批次摘要：[summary.json](../../output/prompt007/deepseek-flash-v5-d13-d15-20261017/summary.json)
- 测试脚本：[run_v5_d13_d15.py](../../output/prompt007/deepseek-flash-v5-d13-d15-20261017/run_v5_d13_d15.py)
- v5 切换前备份：[prompt-before-v5.py](../../output/prompt007/deepseek-flash-v5-d13-d15-20261017/prompt-before-v5.py)
- 当前运行时定义：[prompt.py](../../backend/app/rag/prompt.py)

**报告后暂停，等待用户验收。**
