# 016 当前真实验收失败

## 最新状态：E 全量已测，4 个部分正确场景（2026-10-28）

按用户“全部测试一遍、前题失败不影响后题”的新授权，gold-1.0 15 场景/19 轮已全部运行、无重试、0未运行。逐题完整答复审阅为11通过/4部分正确未通过；10道独立事实题36个必答点全覆盖不等于正文没有错误。模型79次、搜索20次、provider Token115247，运行346项保护无差异，原D首答/历史失败保留。

- **E-Q3 / E-Q15：错误文档缺失断言**。恢复主要步骤齐全，但附加段落称重新上电操作/自检等未说明；原PDF第2节已有ON、约五秒自检及READY/WAIT/FAULT判断，第3节要求恢复后重新执行上电流程。
- **E-Q9：恢复流程未完整表达并错误否定自检依据**。补充澄清行为正确，末答只说手动重启，未完整覆盖“重新执行上电流程”，并声称只有欠压保护明确自检。
- **E-Q14：错误电流区间推断**。正确给出>16 A/100 ms/立即断开主回路，却又从用户“>15 A”推出“未超过16 A、两个条件均不满足”；17 A/50 ms即为反例，电流条件满足而持续时间不足。

原答和标准答案逐题展示于 [历史评测结论（原文已脱敏）](phase-e-answer-comparison-20261028.md)，计数、命令与限制见 [E 报告](phase-e-full-gold-20261028-report.md)，机器记录见 [comparisons.json](../../output/reference016/phase-e/full-gold-20261028-01/comparisons.json)。本轮Q1覆盖了万用表，但产品未修、不据此改判D原失败。仅测试与分析，不自动修复；**报告后暂停，等待用户验收。**

## 最新状态：D 真实 PDF 首题完整性失败（2026-10-28）

用户明确“开始真实测试”后，当前 deepseek-flash/真实 fastembed ONNX+原 BM25 在正式测试 PDF 索引的隔离副本执行 gold-1.0 Q1 首答。链路 completed、5 次模型（含压缩 1 次、聚合 1 次）、2 次真实搜索、14.547 秒、provider Token 9527；最终答复遗漏已批准必答事实“合格的万用表”，故 **0通过/1失败/0待定/3未运行**，按本轮失败停止规则不执行 Q2–Q4，不重试。

**D-Q1-MISSING-MULTIMETER**：request_id=`c6485bd6-53c1-4706-8532-efcad2851560`。本次两个真实 Child 均包含“使用合格的万用表确认输入电压处于 198 V 至 242 V 范围内，频率处于 49 Hz 至 51 Hz 范围内。”，但最终答案没有万用表。能够确认“已召回而最终遗漏”，尚不能确定是压缩、研究生成还是最终聚合中首次丢失；不能把 Sources 匹配或 completed 当作质量通过。

证据：[原答](../../output/reference016/phase-d/formal-pdf-20261028-01/Q1.raw.json)、[真实事件/检索正文](../../output/reference016/phase-d/formal-pdf-20261028-01/Q1.events.jsonl)、[逐事实审阅](../../output/reference016/phase-d/formal-pdf-20261028-01/Q1.review.json)、[批次汇总](../../output/reference016/phase-d/formal-pdf-20261028-01/summary.json)、[D 报告](phase-d-real-pdf-20261028-report.md)。原准备阶段 BM25 缓存缺失已另存，补齐历史 hash 相同的官方词表后准备通过，准备模型调用 0；不是问答重试。以下 B/R 记录保持其当时事实，根目录旧失败未改判。**报告后暂停，等待用户验收。**

## 最新状态：B 剩余场景已通过（2026-10-27）

用户在 R 报告后“继续计划”，本轮 B02 澄清、B03 直接补充、B04 压缩、B05 多问聚合真实首答均通过，4 passed/0 failed/0 pending/0 not_run。模型 21 次、工具 7 次，provider 总 Token 40367。与 R 的 B01 在模型身份/全部产品 Python/临时索引内容及版本上核对一致，首题仅引用不重跑；五类所需场景均有通过证据，T017 采集交付完成，待用户验收。

当前 016 合成场景没有新增失败；原 B01 首次失败、诊断和 R 过程记录原文保留如下，不改成一次五题首次全通过。B02 的英文澄清及本轮未调用 Parent 是实际限制；没有正式 PDF、ONNX 语义检索或 HTTP/浏览器验收。见 [续测报告](phase-b-resume-20261027-report.md)。报告后暂停，等待用户验收。

范围：016 B 的隔离真实模型采集。根目录 CURRENT_FAILURES.md 的 005 两项历史失败保持原文，未在本文件重新判定。

## B-FAIL-001：首题入口请求失败

- 首次执行日期：2026-10-27（用户时区 America/Phoenix）。批次 `first-20261027-01`，题目 B01：`ZX-731 的巡检周期是多久？`。
- 冻结身份：openai_compatible / deepseek-flash，temperature=0、seed=42，原端点/密钥保持；云端别名不证明固定权重修订。
- 请求标识：`5d626400-28f1-45ef-9f0a-264cd3f8ea38`。
- 实际：rewrite_query 模型尝试在 416 ms 后记录 `OpenAIInvalidRequestError`；整次采集 448 ms，以 failed / RAG_PIPELINE_FAILED 结束。analysis/answer/source 均未产生，工具 0。
- 观测 model_calls=1、cloud_calls=1，代表调用链尝试统计，不证明远端已受理；失败路径 Token=0、usage_source=estimate，实际 Token/计费不可得。
- 尚未确定：具体错误参数、服务端或 SDK 拒绝层次及根因。当前公共日志按隐私契约不保留异常正文，不能据此断言端点不支持某个特性。
- 当前状态：**未通过；未诊断修复，未重试**。后续 B02–B05 按冻结失败停止规则均 not_run。

证据：[首答/错误记录](../../output/reference016/phase-b/first-20261027-01/B01.raw.json)、[实际事件](../../output/reference016/phase-b/first-20261027-01/B01.events.jsonl)、[Codex 审阅](../../output/reference016/phase-b/first-20261027-01/B01.review.json)、[批次汇总](../../output/reference016/phase-b/first-20261027-01/summary.json)。

上述“尚未确定”“未诊断”保留首次失败时的事实。用户随后明确要求“直接用真实模型呀”，已另开诊断批次，结果如下。

## 2026-10-27 真实诊断补充（原失败不改判）

- 原入口再现 HTTP 400，脱敏错误正文明确为 `Thinking mode does not support this tool_choice`。思考模式与 SDK 结构化入口的指定工具选择冲突。
- 同一真实模型、端点、原始提示/schema，仅在诊断进程增加 `extra_body={"thinking":{"type":"disabled"}}`，入口成功；完整 B01 原图随后完成，真实模型 4 次、真实搜索 1 次，正确回答 72 小时并给出实际资料来源。
- 合计本轮诊断 6 次模型调用尝试（原样复现 1、关闭思考的入口验证 1、完整图 4），没有 fake/mock、SDK 自动重试或 provider 切换。不是原批次首次计分；B02–B05 未执行，T017 仍不完成。
- 当前状态：**根因已确认，临时请求参数已验证；产品源码和 backend/.env 未修，正常入口仍保留原冲突风险**。三次运行各 308 项保护指纹无差异。

见[真实诊断报告](phase-b-diagnosis-20261027-report.md)、[原样错误](../../output/reference016/phase-b/diagnosis-20261027-original-01/result.json)、[完整图答复](../../output/reference016/phase-b/diagnosis-20261027-graph-01/B01.raw.json)。后续产品修复和完整 B 补测分别记录，保留原首次失败。报告后暂停，等待用户验收。

## 2026-10-27 R 正式修复结果

用户再次“继续”后，`core/reference_model.py` 已对精确 `openai_compatible/deepseek-flash` 的正常参考图实例默认传入 `thinking.type=disabled`，覆盖入口、研究工具往返、摘要和聚合。其他模型、Ollama 和 legacy 保持。该策略对新建实例生效，本轮未重启服务。

51 项隔离定向工程检查通过；未带 `--thinking-disabled` 或任何临时 override 的产品工厂，真实 B01 completed，模型 4 次、搜索 1 次，正确答案 72 小时及实际文件来源。请求 `29fdc3e5-6942-4a76-94e2-e9a4b876d8a6`；采集 4.350 秒，provider Token 3143。见 [R 报告](phase-r-report.md)及[独立审阅](../../output/reference016/phase-b/r-fix-20261027-b01-01/B01.review.json)。

当前结论：**B-FAIL-001 的传输冲突已修复并完成单题真实复验**；原 B 首次失败仍保留，完整 B 质量验收仍未完成，B02–B05 未运行，T017 不勾选。307 项原保护文件未变，唯一产品变化为模型工厂；真实复验期间 314 项指纹无变化。原 A/B/诊断报告保持。报告后暂停，等待用户验收。
