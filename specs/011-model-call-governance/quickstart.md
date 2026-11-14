# P2 隔离验证指南

**状态：A–D 工程已交付、待用户验收；当前完整后端回归 797 passed / 2 failed / 2 deselected，前端 27 passed、noEmit 类型检查通过。** 两项既有提示词断言保留，未运行真实模型。实际命令、首轮失败及限制见 [D 报告](phase-d-report.md)。本指南不是继续测试、真实复验或下一阶段的授权。

## 已实现的内部接口

| 接口 | 职责和生命周期 |
|---|---|
| `ModelCallRunner.invoke(CallSpec, CallContext)` | 当前完整 messages/tools/schema 输入、原额度、活动 lease、原绝对期限、提供商执行及独立记录；不修改业务历史 |
| `owned_call_context` / `operation_context` | 图拥有请求；业务借用 shared context。独立操作在 request_id/context/lease 均未提供时创建 owner，答案与修复共用一个 scope；显式失效或冲突 scope 拒绝，不注册续命 |
| provider `before_attempt(PreparedAttempt)` | 实际发送前准入；首个获准 attempt 计一次逻辑调用，允许的格式回退重新检查容量和期限，不重复计费 |
| `DiagnosticRecorder.submit/status/close` | 有界非阻塞快照移交与安全状态；lifespan start/close，独立存储 seam 完整发布且不覆盖旧文件；产品不等待 saved |

覆盖分析、分支、答案修复、最终汇总、普通生成、旧改写及摘要。保留 8/12、分支 5/4/3、原工具/节点槽和最多 300 秒请求/默认 120 秒单次上限；配置覆盖仍受原规则约束。缓存命中不生成模型调用；摘要可选，不抢回答与汇总。旧改写未接回主图。公开调用投影不含输入/候选/工具正文；原分析和首答等私有诊断按原范围保留。

## 前提与隔离

1. 读取 AGENTS、当前阶段任务和最新报告，核对 git status/diff，保存当次快照；保留用户已有修改。
2. 使用仓库现有 Python/Node 与依赖，不为此升级。pytest 从 backend 目录运行，前端从 frontend 目录运行。
3. 测试环境设 LLM_PROVIDER=fake、EMBEDDING_BACKEND=deterministic、SPARSE_OFFLINE_FALLBACK=true，DATA_DIR / Qdrant / basetemp 指向当次 output 内的独立路径，不读取或覆盖 backend/.env。
4. 复用 P1 已修正的进程内 guard，另存本阶段版本和命令。它阻止真实 Dense 加载与普通 socket.connect，仅允许 Windows asyncio socketpair 内部唤醒对；所有提供商均为 scripted/fake 或真实 adapter 的假传输。
5. 每次工程执行前须准备并验证 guard 和对应 pytest 运行器。D 的已验证版本为 `output/governance011/engineering/phase-d-20261021/context011_d_guard.py` 与 `context011_d_runner.py`：运行器将自身目录加入 PYTHONPATH，禁用 Settings 默认 dotenv，保留展开的 argv/cwd/exit/guard hash 和原日志。不能只设 fake 环境而漏掉已有用例的显式真实后端覆盖。

## 分阶段场景

| 阶段 | 主要 seam | 需要证明 |
|---|---|---|
| A | 现有 graph.run / chat SSE + recorder 存储 interface | 保存成功/关闭/异常/慢写/队列满/重复标识/关闭，问答与历史不被覆盖 |
| B | graph.run + runner + 两真实 adapter 假传输 | 相同物理输入、一次逻辑预占、回退后超限/超时、迟到 guard、loop/汇总/修复槽 |
| C | 各现有服务 interface + graph.run | 分析、普通生成、旧改写、摘要及 owned context；缓存无虚构调用、独立修复不重置额度 |
| D | 完整问答/SSE与既有前端消费 | 多分支、P1组合、完整回归和隐私；所有公开字段、次数、原因及单终态一致 |

诊断慢写用可控 Event 门阻塞 worker：先确认 SSE 已有 complete，再释放门；不要以极短 sleep 或脆弱墙钟阈值代替不等待证明。调用期限用受控时钟和等待 adapter；真实 adapter 只替换传输 client，不能调用真实 API。

## 测试入口与可复验命令

实际测试入口如下；对应运行成绩按阶段报告核对，不将代码存在当作执行通过。

| 约束 | 已实现测试模块（backend/tests 下） |
|---|---|
| runner、lease、期限与独立修复 | `unit/test_model_call_governance.py`、`unit/test_model_call_consumers.py`、`unit/test_request_deadline.py` |
| 内置 adapter 假传输、strict/fallback | `unit/test_model_call_attempts.py`、`unit/test_query_analysis_structured_output.py` |
| 诊断快照/发布/关闭/存储故障 | `unit/test_diagnostics.py`、`unit/test_diagnostics_lifecycle.py`、`contract/test_diagnostics_stream.py` |
| P1 与预算 | `unit/test_context_admission.py`、`test_parent_context_admission.py`、`test_batch_context_admission.py`、`test_multi_branch_context_admission.py`、`test_model_loop_budget.py` 及对应 contract |
| 全调用链与诊断组合 | `unit/test_model_call_delivery.py`、`contract/test_model_call_delivery_stream.py` |
| 公开投影与私有记录 | `security/test_model_call_privacy.py`、`security/test_query_rewrite_log_privacy.py`、`contract/test_model_call_stream.py` |

获准复验后，可使用已保存的 D 运行器；每次换新标签，旧同名 JSON 已存在时会拒绝覆盖。下例标签仅为下一次运行示例，不代表已经执行：

```powershell
# cwd: C:/Users/ifhgz/Desktop/agentic-rag
python output/governance011/engineering/phase-d-20261021/context011_d_runner.py delivery-recheck-01 tests/unit/test_model_call_delivery.py tests/contract/test_model_call_delivery_stream.py
```

完整后端复验同样使用该运行器（它固定排除下述两项真实嵌入相关用例），排除不算通过：

```powershell
python output/governance011/engineering/phase-d-20261021/context011_d_runner.py full-recheck-01 tests/unit tests/contract tests/integration tests/security
```

固定排除：`tests/integration/test_v3_1_retrieval.py::test_four_baseline_questions_have_facts_in_top5_child_or_parent` 与 `tests/unit/test_embeddings.py::test_missing_real_model_does_not_silently_fall_back_to_hash`。后端 pytest 实际 cwd 由运行器设为 backend。

前端兼容检查（按实际影响选择，不虚构 lint）：

```powershell
# cwd: C:/Users/ifhgz/Desktop/agentic-rag/frontend
node node_modules/vitest/vitest.mjs run
node node_modules/typescript/bin/tsc --noEmit --incremental false
```

如改动前端源码/构建配置，再按 package.json 构建并保存记录；不要覆盖用户已有 buildinfo 或将旧构建说成本轮成绩。

## 验收记录

- 基准与故障运行配对核对 answer、sources、status、reason、usage 中的调用/Token/来源和历史；请求 ID、耗时本来不同，不做整份 JSON 字节相等断言。
- 诊断状态经 status(job_id) 或受控完成通知检查；文件完整性在 worker 完成后确认，产品不等待该通知。
- 已存在正式文件保存原始字节/hash，故障和重复发布后保持；只在临时数据中测试，不删除历史证据。
- 组合测试将每个场景的 request_id、逻辑调用/可得用量、诊断 job 状态和公开事件写入本轮 basetemp 的 `delivery-evidence-*.json`；汇总索引为 D output 下 `delivery-scenarios.json`，私有完整性/公开日志审查为 `privacy-and-preservation.json`。
- 首次输出、失败、完整命令、cwd、退出码及 guard 原始日志分别保存，修复后另存结果，不覆盖红测。
- 保留两项旧 v4 提示原句断言及历史真实失败；P1 最后 646 passed 等是旧阶段记录，不能冒充当前成绩。
- 阶段报告保存至 specs/011-model-call-governance/phase-a/b/c/d 对应报告文件，给出实际完成与限制，并写“报告后暂停，等待用户验收”。

限制：future.cancel 不保证停止已获准的外部 I/O；已关闭 guard 禁止后续许可和迟到业务提交。输入 Token 仍是既有估算，不冒充精确 tokenizer；提供商未给出的用量保留 null，格式回退不冒称完整实测。诊断文件发布不保证断电持久性，非诊断同步日志仍维持原能力。fake/scripted 与假 client 通过不证明真实模型质量或历史失败已解决。
