# 阶段 B 报告：云兼容端点连续真实验证

日期：2026-10-18。功能：`009-cloud-provider-compat`。

授权：用户选择“连续真实云端验证”。本阶段只执行真实端点复验，不修改应用代码、配置、提示词、知识库或索引；报告交付后暂停，等待用户验收。

## 1. 结论

连续提交同一问题三次，三次请求在登录后均通过真实前端 SSE 入口返回 HTTP 200，并使用 `openai_compatible / deepseek-flash` 云端模型。入口分析三次均完成结构化回退，得到 `json_object` 且 `structured_fallback=true`；但三次都在答案生成前触发 `context_budget_exceeded`，没有可验收答案或来源卡。

本阶段证明云端提供商回退链路仍然可用，但在当前“只保留动态阈值、删除证据压缩”的实现下，真实循环稳定性未通过：检索证据装载到模型窗口前后，物理上下文边界会阻止最终回答。请求均在数秒内结束，没有触发 300 秒总期限、120 秒单次等待或调用预算。

## 2. 验证范围与环境

- 问题：`PX-200 的过流保护阈值是多少？`
- 每次使用“新会话”，三次均为独立请求；失败后继续下一次，没有重试或挑选成功结果。
- 真实路径：浏览器登录态 → `POST /api/chat/stream` → 本地 Qdrant 正式索引 → 云端兼容端点。
- 健康检查：`output/cloud009-real-20261018/health.json`，`status=ok`、`index_ready=true`。
- 非敏感配置快照：`output/cloud009-real-20261018/config-visible.txt`。本次生效值包括 `LLM_PROVIDER=openai_compatible`、`LLM_MODEL=deepseek-flash`、整次 300 秒、单次 120 秒、`MAX_CONTEXT_TOKENS=3072`、`MAX_SIMPLE_LLM_CALLS=8`、`MAX_LLM_CALLS_PER_REQUEST=12`、`MAX_TOOL_CALLS=16`、`base_token_threshold=2000`、`token_growth_factor=0.9`。
- 后端进程为 PID 8916，前端进程为 PID 4496；测试后保持运行，供用户继续查看页面。

登录态在后端重启后第一次尝试返回过一次 401；用户重新登录后才开始本阶段三次样本。该 401 没有进入样本，也没有调用云端模型。

## 3. 三次真实结果

| 样本 | 请求标识 | 端到端耗时 | 模型/云端调用 | 工具调用 | 检索结果 | 终态 | 答案/来源 |
|---|---|---:|---:|---:|---:|---|---|
| 1 | `98831067-7a7b-4670-a880-8c5593c97ec1` | 11,063 ms | 2 / 2 | 2 | 4 | `failed / context_budget_exceeded` | 错误提示，0 来源 |
| 2 | `dfc7a876-1f3a-4f2a-9bdc-c36b4c310607` | 2,893 ms | 3 / 3 | 2 | 5 | `failed / context_budget_exceeded` | 错误提示，0 来源 |
| 3 | `6f4f8fe6-5a24-4922-9be2-728a1ce5729d` | 1,786 ms | 2 / 2 | 1 | 5 | `failed / context_budget_exceeded` | 错误提示，0 来源 |

“模型/云端调用”分别表示 SSE `usage` 中的逻辑模型调用数与 `cloud_calls`；三次均相等，总计 `7 / 7`。第 2 次命中 1 次检索缓存，但仍未绕过上下文边界。

三次均返回 `evidence_status=found`，而 `citation_status`、`numeric_status`、`completeness_status` 均为 `not_evaluated`，因为没有生成可核验答案。原始 SSE 分别保存为：

- [`run-01.sse.txt`](../../output/cloud009-real-20261018/run-01.sse.txt)
- [`run-02.sse.txt`](../../output/cloud009-real-20261018/run-02.sse.txt)
- [`run-03.sse.txt`](../../output/cloud009-real-20261018/run-03.sse.txt)
- [`summary.json`](../../output/cloud009-real-20261018/summary.json)
- [`network-requests.txt`](../../output/cloud009-real-20261018/network-requests.txt)

对应后端本地轨迹保留在 `backend/data/logs/loop_traces/` 的三个同名请求文件中；本报告只引用汇总字段，不复制提示词、原文证据或令牌。

## 4. 结构化回退与上下文边界证据

每次 `query_analysis` 的模型事件均为：

```text
structured_mode=json_object
structured_fallback=true
```

每次 `orchestrator` 事件均为 `structured_mode=none`、`structured_fallback=false`，符合仅入口分析需要结构化输出的现有调用关系。三次 SSE 和后端执行轨迹都没有 `context_compression` 事件或压缩模型调用；终止事件均为 `runtime_guard / context_budget_exceeded`。这与本阶段保留动态 Token 阈值、删除证据摘要/摘录/压缩的实现一致。

页面实际显示“证据和消息超过模型窗口，无法在本轮预算内完整装载”，而不是超时或“模型不可用”。因此本轮失败点已从云端提供商切换问题收敛为证据/消息装载与模型物理窗口之间的边界处理。

## 5. 不变量与验收判定

- **HTTP/SSE**：登录后的 3/3 请求返回 HTTP 200，并产生完整 `complete` 事件。
- **回退可观察性**：3/3 入口分析记录了 `json_object + structured_fallback=true`。
- **调用一致性**：每次 `cloud_calls == model_calls`；没有未记录的逻辑云端调用。
- **边界**：最大端到端耗时 11,063 ms，远低于 300 秒；没有 `budget_exceeded`，单次模型等待也未接近 120 秒。
- **隐私扫描**：原始 SSE 中未发现 `api_key`、`authorization`、`input_messages`、`system_prompt`、私有推理字段或令牌模式；结果见阶段目录中的采集文件。
- **SC-001**：未通过。三次没有非空答案与来源。
- **SC-002**：入口结构化结果 3/3 有效；这只证明入口 schema 回退，不证明完整问答质量。
- **SC-003**：真实轨迹可见回退模式；内部严格请求与通用 JSON 请求的实际 HTTP 次数不在 SSE 中单独暴露，最多两次的边界仍由提供商单元测试证明，本阶段不把逻辑调用数当作底层 HTTP 次数。
- **SC-004**：本阶段未重新运行本地 provider 回归；上一阶段报告中的工程结论保持，不在此处改判。
- **SC-005**：三次逻辑调用计数与 `cloud_calls` 一致；回退内部的底层尝试数未单独计入遥测，因此只报告可观察部分。

## 6. 实际命令与退出状态

| 命令/操作 | 结果 |
|---|---|
| 启动 `D:\newsoft\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` | 进程 PID 8916，启动成功 |
| 启动 `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort` | 进程 PID 4496，启动成功 |
| `GET http://127.0.0.1:8000/api/health` | HTTP 200，`index_ready=true` |
| 浏览器真实登录后连续 3 次 `/api/chat/stream` | HTTP 200 × 3；业务终态均为 `context_budget_exceeded` |
| SSE 汇总脚本写入 `summary.json` | 退出码 0 |
| SSE 敏感字段扫描 | `rg` 退出码 1（无匹配，按“无匹配”记录） |

本阶段没有运行 fake/mock、确定性嵌入或单元测试；以上结果全部来自真实云端、真实索引和真实浏览器入口。它不能证明答案质量通过，也不能把当前失败归因于模型 API 不可用。

## 7. 下一阶段与停止点

本阶段没有改动上下文边界或检索策略。若要让该问题在删除压缩后继续生成答案，需要另行决定并授权处理上下文超限策略（例如减少装载证据、调整检索/消息预算或重新定义物理窗口边界）；这不属于本次真实验证范围。引用核验诊断也无法在没有答案的样本上完成。

**报告后暂停，等待用户验收。**
