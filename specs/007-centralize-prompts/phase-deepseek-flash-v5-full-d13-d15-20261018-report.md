# rewrite-prompt-v5 + DeepSeek Flash：D13/D14/D15 完整 RAG Loop 真实测试报告

日期：2026-10-18（America/Los_Angeles）  
授权范围：用户要求跳过片面的入口判断，按完整 RAG loop 测试当前效果。

## 结论

本轮在知识库隔离副本上，对 D13、D14、D15 各执行一次完整链路：入口问题分析 → Agent loop → 混合检索 → 上下文处理 → 回答生成 → 引用核验。三题均真实调用 DeepSeek Flash，结果为 **0 题完成、3 题失败**。

失败不是三题都在入口处直接结束：D14 的 Agent loop 确实自主把比较题拆成了 PN8733 和 PX-200 两路检索；但后续仍未生成可验收答案。D13、D15 在上下文压缩阶段失败，D14 在第二轮检索后触发分支预算。

## 逐题结果

| 题目 | 入口分析 | Loop 实际行为 | 终止原因 | 答案验收 |
|---|---|---|---|---|
| D13 | `is_clear=true`，一个合并问题 | 执行 2 次混合检索，拿到 4 条结果；证据已包含 PX-200 过压阈值、245 V/400 ms 题设和恢复条件 | `invalid_model_output`：上下文压缩调用没有返回可解析的可见 JSON，输出达到 768 tokens | 未生成最终答案与来源卡 |
| D14 | `is_clear=true`，一个合并比较问题 | 第 1 轮分别检索 PN8733、PX-200；压缩后提示缺少 PN8733 阈值；第 2 轮再次分别检索两个型号 | `budget_exceeded`：继续下一轮前没有可用模型槽位 | 未生成最终答案与来源卡 |
| D15 | `is_clear=true`，一个包含四项需求的问题 | 执行 1 次混合检索，拿到 5 条结果；进入上下文压缩 | `invalid_model_output`：上下文压缩调用没有返回可解析的可见 JSON，输出达到 768 tokens | 未生成最终答案与来源卡 |

D14 的第一轮检索结果已经显示 PX-200 过流保护为“输出电流超过 16 A 持续 100 ms”，但 PN8733 阈值尚未找到，所以系统没有依据不足的证据强行给出比较结论。

## 配置与调用记录

- provider：`openai_compatible`
- model：`deepseek-flash`
- base URL：`https://api.deepseek.com/v1`
- 入口提示词：`rewrite-prompt-v5`
- 入口未新增代码层语义校验；本轮也没有修改产品代码
- 每题独立新线程、动作 `new_question`，每题首次执行一次；自动重试 0 次
- D13：15.163 秒，模型调用 3 次，工具调用 2 次
- D14：7.249 秒，模型调用 4 次，工具调用 4 次
- D15：6.102 秒，模型调用 3 次，工具调用 1 次
- 检索调用均为混合 Dense + Sparse；Judge 调用 0 次；云模型调用来自当前 DeepSeek 配置
- 当前请求上限保持 300 秒，单请求模型预算和工具预算保持现有配置

## 数据与边界

本轮将 `backend/data` 中的文档、Parent/Child、索引和 Qdrant 复制到本轮独立目录；没有重建或写入正式知识库。正式知识库测试前后指纹一致。测试副本的运行日志、Loop trace 和原始事件均单独保存。

这批证明了完整链路的实际停点和证据流，不代表三题答案正确；三题都没有生成可人工验收的最终答案，因此不能把检索到证据等同于回答通过。浏览器端此前显示“聊天请求无法建立”，属于当前登录/前端请求层问题，本轮核心结果来自隔离服务直接执行，不把该 UI 错误混入模型质量结论。

## 证据

- 批次摘要：[summary.json](../../output/prompt007/deepseek-flash-v5-full-d13-d15-20261018/summary.json)
- 人工审阅摘要：[manual-review.json](../../output/prompt007/deepseek-flash-v5-full-d13-d15-20261018/manual-review.json)
- D13 完整事件：[D13.full.json](../../output/prompt007/deepseek-flash-v5-full-d13-d15-20261018/D13.full.json)
- D14 完整事件：[D14.full.json](../../output/prompt007/deepseek-flash-v5-full-d13-d15-20261018/D14.full.json)
- D15 完整事件：[D15.full.json](../../output/prompt007/deepseek-flash-v5-full-d13-d15-20261018/D15.full.json)
- 测试脚本：[run_full_loop.py](../../output/prompt007/deepseek-flash-v5-full-d13-d15-20261018/run_full_loop.py)
- 当前入口提示词：[prompt.py](../../backend/app/rag/prompt.py)

**报告后暂停，等待用户验收。**
