# 轻量英文入口 prompt 三道旧失败题复测报告

日期：2026-10-14。授权：用户要求“现在测试一下，直接测试之前出错的那几道题目”。本轮只运行此前失败的 RW13、RW14、RW15 对应冻结案例 D13、D14、D15；使用当前 `rewrite-prompt-v5`（用户提供的轻量英文 prompt）、`granite4.1:8b`、本机 Ollama 和现有独立 `QueryAnalysis` schema。没有运行六题变体、完整17题、端到端检索或回答链。

## 结果

三道题各真实调用一次，**0通过、3失败、0待定、0未运行**。结构化输出均有效，失败来自业务语义审阅：

| 案例 | 模型首答表现 | 结论 |
|---|---|---|
| D13 / RW13 | 两个子问题都保留 PX-200、245 V 和 400 ms 的语义，但第二问使用“上述条件”，没有在该子查询中自包含地重写共享条件。 | 失败：共享条件未完整展开。 |
| D14 / RW14 | 输出两个阈值事实查询后，额外增加“哪个更高”的第三个比较查询。 | 失败：比较应留在原题语义中，由后续汇总完成。 |
| D15 / RW15 | 四个独立需求被判为清楚，只返回启动电压、过流阈值、维护周期三个问题，静默丢弃“记录保留期限”。 | 失败：超过三项时应先澄清选择，不能丢题。 |

本轮还观察到 D14 的子问题被改写成英文、D13 把 `400 ms` 表达为“400毫秒”。这些变化不是本轮主要失败条件，但说明英文指令会影响中文输入的输出语言和表述形式。

## 工程与真实调用记录

| 命令 | 退出状态 | 说明 |
|---|---:|---|
| `D:/newsoft/python.exe -B output/test_previous_rewrite_failures_20261014.py` | 0 | 3 次真实入口调用，逐题审阅后继续。脚本汇总状态为 `completed_with_failures`。 |
| `D:/newsoft/python.exe -B output/audit_previous_rewrite_failures_20261014.py` | 0 | 12 项审计通过。 |

真实调用使用的模型身份、prompt/schema/provider 指纹、每题 request/thread/model_call_id、首答、用量和审阅理由均已保存。三次调用合计模型等待约 76.965 秒；工具调用、检索、云端调用、Judge、缓存和自动重试均为 0。没有修改 schema、provider、query analyzer 或正式题集。

工程测试方面，之前轻量候选的定点工程检查仍有一个旧断言失败：它禁止 prompt 中出现普通英文单词 `questions`，而用户给出的 prompt 明确包含 “maximum of 3 rewritten questions”。本轮未把这个旧断言改写成通过，也没有把它冒充为真实质量结果。

## 证据

- 三题批次摘要：[summary.json](../../output/prompt007/previous-failures-20261014/run/summary.json)
- 审计：[audit.json](../../output/prompt007/previous-failures-20261014/audit.json)
- 指标：[metrics.json](../../output/prompt007/previous-failures-20261014/metrics.json)
- D13 首答与审阅：[D13.raw.json](../../output/prompt007/previous-failures-20261014/run/D13.raw.json)、[D13.review.json](../../output/prompt007/previous-failures-20261014/run/D13.review.json)
- D14 首答与审阅：[D14.raw.json](../../output/prompt007/previous-failures-20261014/run/D14.raw.json)、[D14.review.json](../../output/prompt007/previous-failures-20261014/run/D14.review.json)
- D15 首答与审阅：[D15.raw.json](../../output/prompt007/previous-failures-20261014/run/D15.raw.json)、[D15.review.json](../../output/prompt007/previous-failures-20261014/run/D15.review.json)

## 结论与下一范围

这三道旧失败题在轻量英文 prompt 下仍全部失败，当前证据不足以接受 v5 替代 v3。下一步如继续，应由用户决定是否恢复 v3、改用中文/双语 prompt，或只补充这三条业务约束后再测；本报告不自动扩大题集，也不自动替换 prompt。

**报告后暂停，等待用户验收。**
