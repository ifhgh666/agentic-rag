# 唯一对象代词补全 RW07 复测报告

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-15。用户要求重新测试问题指代能力。本轮沿用冻结 RW07：历史消息为“PN8733 的启动电压是多少？”，当前问题为“它的恢复条件是什么？”。使用当前 `rewrite-prompt-v6-zh`、`granite4.1:8b` 和独立 `QueryAnalysis` schema，只进行一次真实入口调用。

## 结果

首答结构有效，但语义验收失败：**0通过、1失败、0待定、0未运行**。

模型返回：

```json
{
  "is_clear": false
}
```

历史中的唯一对象 `PN8733` 确实进入了模型输入，但模型仍要求用户重新说明对象，没有将“它”改写为“PN8733”。按 RW07 验收标准，预期应为 `PN8733 的恢复条件是什么？` 或同义表达，因此本次代词补全仍失败。

## 调用记录

| 项目 | 结果 |
|---|---|
| prompt 版本 | `rewrite-prompt-v6-zh` |
| 模型 | `granite4.1:8b`，digest `444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852` |
| 模型调用 | 1 次 |
| 模型等待 | 46.288 秒 |
| 工具、检索、云端、Judge、自动重试 | 均为 0 |

实际命令：

- `python -B output/test_pronoun_rw07_20251015.py`：完成 1 次真实入口调用，状态 `completed_with_failures`，退出状态 0。

## 证据

- [批次摘要](../../output/prompt007/pronoun-rw07-20261015/run/summary.json)
- [基线与版本指纹](../../output/prompt007/pronoun-rw07-20261015/baseline.json)
- [RW07 原始首答](../../output/prompt007/pronoun-rw07-20261015/run/RW07.raw.json)
- [RW07 人工审阅](../../output/prompt007/pronoun-rw07-20261015/run/RW07.review.json)

本轮只验证入口问题改写，没有进入检索、答案生成或引文核验；历史 RW07 失败记录保持不变。

**报告后暂停，等待用户验收。**
