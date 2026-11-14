# 中文入口 prompt 三道旧失败题复测报告

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-14。用户授权将轻量入口 prompt 改为中文后，要求直接复测此前失败的三道题。本轮使用 `rewrite-prompt-v6-zh`、`granite4.1:8b`、本机 Ollama 和现有独立 `QueryAnalysis` schema，只运行 D13/RW13、D14/RW14、D15/RW15；每题一次真实入口调用，错误继续，零重试。

## 结果

三题均取得结构有效的首答，但业务语义审阅为 **0通过、3失败、0待定、0未运行**。

| 案例 | 中文 prompt 首答 | 审阅结论 |
|---|---|---|
| D13 / RW13 | [运行记录已移除] | 失败。第二问仍用[运行摘录已移除]，没有自包含展开 `245 V` 和 `400 ms`，不能作为独立检索问题。 |
| D14 / RW14 | [运行记录已移除] | 失败。比较应留在原题语义中，由后续汇总完成，不能增加第三路比较检索。 |
| D15 / RW15 | [运行记录已移除] | 失败。原题有四个独立需求，静默丢弃[运行摘录已移除]；应先请求用户从四项中选择最多三项。 |

D14 的子问题已经恢复为中文，说明更换中文指令解决了上一批观察到的输出语言变化；共享条件和容量处理仍未解决。

## 调用与审计

| 项目 | 结果 |
|---|---|
| 模型 | `granite4.1:8b`，digest `444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852` |
| prompt 版本 | `rewrite-prompt-v6-zh` |
| 真实模型调用 | 3 次，每题 1 次 |
| 模型等待合计 | 78.715 秒 |
| 工具、检索、云端、Judge、缓存、自动重试 | 均为 0 |
| 审计 | 12/12 项通过 |

实际命令：

- `python -B output/test_previous_rewrite_failures_20261014_zh.py`：三题完成，脚本状态 `completed_with_failures`，退出状态 0。
- `python -B output/audit_previous_rewrite_failures_20261014_zh.py`：12 项审计通过，退出状态 0。

## 证据

- [批次摘要](../../output/prompt007/previous-failures-20261014-zh/run/summary.json)
- [基线与版本指纹](../../output/prompt007/previous-failures-20261014-zh/baseline.json)
- [审计结果](../../output/prompt007/previous-failures-20261014-zh/audit.json)
- [D13 首答](../../output/prompt007/previous-failures-20261014-zh/run/D13.raw.json) / [审阅](../../output/prompt007/previous-failures-20261014-zh/run/D13.review.json)
- [D14 首答](../../output/prompt007/previous-failures-20261014-zh/run/D14.raw.json) / [审阅](../../output/prompt007/previous-failures-20261014-zh/run/D14.review.json)
- [D15 首答](../../output/prompt007/previous-failures-20261014-zh/run/D15.raw.json) / [审阅](../../output/prompt007/previous-failures-20261014-zh/run/D15.review.json)

本批只验证入口改写，不代表检索、答案生成、引文核验或完整 17 题质量通过。上一批 v5 的原始记录和报告保持不变。

**报告后暂停，等待用户验收。**
