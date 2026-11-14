# 016 B 真实模型诊断报告

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-27（America/Phoenix）。用户在询问失败原因后要求“直接用真实模型呀”。范围为原入口真实复现、单变量诊断及首题完整图验证；不实施产品修复，不覆盖原 B 首次失败，不运行余下四题或正式题库。

**结论：根因已确认。思考模式与结构化入口的指定工具选择冲突。相同真实模型在诊断请求中关闭思考后，入口及完整首题均成功；产品代码和配置尚未修复，B 整阶段仍未通过。报告后暂停，等待用户验收。**

## 证据与原因

沿用实际 `openai_compatible / deepseek-flash`、原端点及密钥、temperature=0、seed=42。原产品 `rewrite_query`、提示及 QueryAnalysis 三字段 schema 不变；SDK function_calling 会指定 QueryAnalysis 工具。凭据和端点不写入命令或记录，身份只保存端点哈希。

原入口直接真实调用记录 HTTP 400 / OpenAIInvalidRequestError，服务错误为：`Thinking mode does not support this tool_choice`，服务请求标识 `[运行标识已移除]`。这是本轮实际返回证据；原 B 日志仍只有异常类型，不回填不存在的原始错误正文。

[DeepSeek 官方 API 说明](https://api-docs.deepseek.com/api/create-chat-completion/)明确：思考模式不接受 required 或指定函数的 tool_choice，会返回 400；[思考模式说明](https://api-docs.deepseek.com/guides/thinking_mode/)说明默认开启以及通过 extra_body 传递开关。为避免把错误信息已明确的冲突扩展成无依据的广泛猜测，本轮直接做单变量对照：只增加 `extra_body={"thinking":{"type":"disabled"}}`，不改指定工具、模型、提示/schema、温度或种子。

## 实际运行

工作目录：`C:\path\agentic-rag`。以下均直接使用真实模型，无 fake/mock、Judge、SDK 自动重试或 provider 切换；每条命令只运行一次。第二、三条是明确标记的诊断变体，不能当作原批次首次成绩。

| 实际命令 | 退出码 | 结果 |
|---|---:|---|
| `D:\newsoft\python.exe output/reference016/phase-b/diagnose_real.py diagnosis-20261027-original-01` | 1 | 原产品入口复现 HTTP 400；2,861 ms，1 次模型调用尝试 |
| `D:\newsoft\python.exe output/reference016/phase-b/diagnose_real.py diagnosis-20261027-disabled-01 --thinking-disabled` | 0 | 单变量关闭思考，入口清楚并保留原题；3,162 ms，1 次模型调用 |
| `D:\newsoft\python.exe output/reference016/phase-b/diagnose_real.py diagnosis-20261027-graph-01 --thinking-disabled --graph` | 0 | 原完整图完成首题，待审输出经 Codex 核对通过；4 次模型调用、1 次搜索 |
| `D:\newsoft\python.exe output/reference016/phase-b/audit_diagnosis.py` | 0 | 三次运行各 308 项保护指纹无差异 |

入口探针只有一次实际模型调用，无知识库依赖，因此可直接复现原错误。完整图使用 AgentGraphService 的既有 model 注入点，在本诊断进程为模型全部调用增加关闭思考参数，不修改产品文件或启动 HTTP 服务。

本轮合计 6 次真实模型调用尝试。完整图 provider 报告 2,925 输入 / 218 输出 / 3,143 总 Token；两个独立入口探针未采集 provider usage，首个失败也不能按实际零计费报告。完整图耗时：产品 usage 2,758 ms、逐题采集 2,763 ms、包括本地模型/索引初始化的诊断总耗时 5,445 ms，口径分别保留。

## 完整首题与逐项核对

问题：ZX-731 的巡检周期是多久？

原始聚合答案：

[真实运行原文已移除]

请求 ID：`[运行标识已移除]`。入口清楚，单分支；模型执行 rewrite_query 1 次、orchestrator 2 次、aggregate_answers 1 次，真实 search_child_chunks 1 次。最终 completed、无 error、pending 为空。

Codex 核对：72 小时符合临时资料；附加的 45 天、8 GB 也出自同一资料，无本题事实错误；来源文件名与本次实际检索元数据匹配，页码为 null。只证明该合成首题的诊断变体通过，不证明其他业务场景质量。结果和逐事件记录见 [B01.raw.json](../../output/reference016/phase-b/diagnosis-20261027-graph-01/B01.raw.json)、[B01.events.jsonl](../../output/reference016/phase-b/diagnosis-20261027-graph-01/B01.events.jsonl)、[独立 review](../../output/reference016/phase-b/diagnosis-20261027-graph-01/B01.review.json)。

## 文件、保护与限制

- 新增辅助脚本 `output/reference016/phase-b/diagnose_real.py`、`audit_diagnosis.py` 及三个 diagnosis 目录的 manifest/result/before/audit；完整图另存 fixture、真实临时 Qdrant 知识库、事件、首答和审阅。错误字段只保留经脱敏的 type/code/param/message，不记录提示或私有推理。
- 更新 README、docs/CURRENT_STATUS、当前功能 CURRENT_FAILURES 与 tasks 的事实补充。本报告及原 B/A 报告分别保存，不改写旧成绩。
- 三次运行各 308 项保护指纹无差异，包含产品 Python、backend/.env、正式知识数据/索引、原 A 报告和顶层原证据；正式内容不作为输入，执行时禁止打开正式数据路径。当前产品仍未传入关闭思考参数，原入口冲突尚未正式修复。
- 临时索引使用真实 DocumentStore/IndexStore/Qdrant/Retriever 和 deterministic Dense/local BM25；不是生产 ONNX 语义检索验收，没有 PDF 解析、浏览器/HTTP/认证、长上下文压缩、多问及澄清续答验证。未改产品代码，未重跑工程全量；本轮模拟测试为零。
- 原 B01 失败保留，B02–B05 未执行，T017 仍部分完成；T018 的原失败报告不覆盖。没有服务启动/重启、依赖升级、提交或推送。

下一范围为正式模型适配修复及另批次 B 验证；需按用户后续明确指示和项目 Spec Kit 流程落实，不以本次临时参数成功宣称产品已修好。

**报告后暂停，等待用户验收。**
