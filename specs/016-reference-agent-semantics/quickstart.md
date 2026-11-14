# 016 验证指南

本指南保留 A 收尾的隔离验证入口。2026-10-27 规划修订当时未运行 pytest/npm；随后用户继续授权 A 收尾，实际新结果见下文。重用时仍需相应执行授权，不覆盖旧标签或进入 B。

## 前置与隔离

A 只用 fake/scripted 模型、deterministic embedding、临时 Qdrant。现有 runner 为 `output/reference016/phase-a/run.py`，guard 为同目录 `reference016_guard.py`，源自最终隔离保护；禁 dotenv、真实 Dense、外部 socket、正式数据打开，并禁 tiktoken 编码下载。asyncio 内部 socketpair 的受控本地连接例外不用于服务请求。

使用本机现有 `D:\newsoft\python.exe`，不安装或升级。每批指定未用过的标签；runner 断言同名 json 不存在，禁止覆盖或复用旧 `before-full`。测试应明确限制四个 tests 子目录，避免误收集 backend/tmp。guard/runner 变动须记录 hash 和原因，不降低隔离来取得通过。

## A 定向与完整回归

以下工作目录为仓库根目录 `C:\path\agentic-rag`。标签如已存在则换新编号；命令是未来操作说明。

```powershell
& 'D:\newsoft\python.exe' output/reference016/phase-a/run.py a-close-focused-20261027-01 tests/unit/test_reference016_graph.py tests/unit/test_reference016_model.py tests/unit/test_reference016_parity.py tests/unit/test_rag_tools.py tests/unit/test_rag_architecture.py tests/integration/test_reference016_session.py tests/contract/test_reference016_stream.py tests/contract/test_reference016_observation.py tests/contract/test_reference016_diagnostics.py tests/security/test_reference016_privacy.py
& 'D:\newsoft\python.exe' output/reference016/phase-a/run.py a-close-full-20261027-01
```

runner 保存 `<label>.json`（实际命令/cwd/退出码/guard hash）、`.log` 原始输出、`-guard.json`（阻拦/屏蔽/跳过/pytest状态）。两个命令独立记录退出码；不能靠后一个覆盖前一个结果。定向通过后、代码不再修改时才做完整批次；审查若修代码，再用新标签复验。

| 场景 | 主要检查位置/判据 |
|---|---|
| 单问、三分支、有序聚合、多轮 | test_reference016_graph.py / test_reference016_parity.py；参考消息、调用、上下文、输出对照，agent_answers 不累积旧轮 |
| 工具/迭代边界与无工具收尾 | test_model_loop_budget.py / test_reference016_parity.py；等于/超过边界、越界整批不执行、无工具优先 collect |
| 压缩/历史摘要 | test_context_compression.py / test_model_agent_loop.py / test_reference016_parity.py；严格大于阈值、检索标识和首问保留；A 编码回退不冒充真实 tokenizer 实测 |
| 完整 Parent/空检索/重复工具 | test_rag_tools.py / test_parent_context_admission.py；未知但合法 ID、ready 约束、无分页/先搜索硬前置；重复只由提示引导 |
| auto/continue/new/cancel/异常/互斥 | test_reference016_session.py / test_query_rewrite_v1.py；补充失败保留 pending，普通失败不变澄清 |
| provider 参数与宽松入口 | test_reference016_model.py / test_v3_3_query_analysis.py；两种原生结构化路径，不恢复旧联动 |
| 实时进度/累计答案/来源/null用量 | test_reference016_stream.py / test_reference016_observation.py；聚合完成前有实际事件、只聚合进入答案、来源精确交集 |
| 隐私/诊断/断开 | test_reference016_privacy.py / test_reference016_diagnostics.py / 相关 API 契约覆盖；白名单、敏感异常不透传、诊断不改变交付；断开不虚称即时取消 |

完整测试还包含其余 unit/contract/integration/security，以 guard 隔离后的实际收集为准。上表是定位索引，不声称当前每个边界都有充分断言；T013/T015 须核对，缺覆盖时明确补齐，不能仅凭文件名勾选。

## 前端

工作目录 `C:\path\agentic-rag\frontend`：分别运行并保存命令和退出码。

```powershell
npm test -- --run
npm run build
```

现有 package.json 没有 lint 脚本，不安装依赖；Vitest mock SSE/DOM 与构建均是工程检查。40 passed/构建成功的旧记录不证明真实浏览器或模型质量。

## A 工程验收规则

- 迁移前 before-full：819 passed / 3 failed / 24 skipped / 2 deselected，退出 1。保留两项 legacy prompt 及旧 deadline 首次失败。
- 收尾前完整 resume-full-20261026-final：713 passed / 3 failed / 24 skipped / 2 deselected，退出 1；含 pending 保留失败。
- 随后 resume-pending-transport-fix-20261026：4 passed，退出 0，不覆盖原完整失败。
- 本轮 a-close-full-20261027-01：720 passed / 2 failed / 24 skipped / 2 deselected，退出 1；无新增失败，原两项 prompt 例外保留。前端重跑 40 passed、构建退出 0。修复后统一完整复验已完成。
- 可记录为“无新增失败，保留历史例外”的完整结果仅限两项既有 prompt：`test_query_rewrite_v1.py::test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity` 和 `test_v4_query_analysis.py::test_context_prompt_limits_history_and_preserves_unconfirmed_conditions`。pytest 仍应退出 1，不能写“全部通过”。例外只用于区分新退步，不代表修好历史质量。
- 24 项正式 PDF 跳过、2 项真实 Dense 排除必须与 guard/runner 清单核对，不能算通过；新增 skip/xfail/deselect 或数量变化必须有逐项理由。collection error、网络/正式数据阻拦和其他新增失败均不能闭合 T014。
- 核对 [测试迁移索引](test-migration.md)、实际旧保护清单和当前任务；解释前后测试数量差异，不比较通过数量推断功能等价。原真实质量失败及 CURRENT_FAILURES.md 不改判。
- A 总报告另存 `phase-a-report.md`：文件、真实命令/cwd/退出码、工程/真实区别、全部失败与限制、任务/保护差异、B 范围及“报告后暂停，等待用户验收”。

## B 门槛

用户验收 A 并明确授权 B 才进入。冻结现有 provider/model 身份和临时知识数据，先明确工具/澄清/压缩/聚合场景与逐题通过判据，再采集首答、异常、实际调用/耗时/用量；不挑重试最佳结果、不自动正式题库或云端切换。B 的运行配置、质量判据及失败后策略须在获准范围内明确，本指南没有授权真实调用。

2026-10-27 用户随后明确继续 B，实际按 [B 协议](phase-b-protocol.md)执行。采集脚本入口为 `D:\newsoft\python.exe output/reference016/phase-b/capture.py prepare`（先冻结并建立临时索引）、`... capture.py supervise`（原图真实首答、逐题等待 review、外部 900 秒观察上限）和 `... capture.py audit`（指纹复核）；同一 first-20261027-01 不可重跑覆盖。实际 B01 失败后停止，后四项未运行，结果见 `phase-b-report.md`。工程脚本 4 项 fake/临时索引检查通过不构成 B 质量通过；无需因未修改产品代码而重复全量后端或前端回归。
# R 修复验证补充（2026-10-27）

本轮授权见 plan 的 R 阶段，T019–T023。先经 `output/reference016/phase-a/run.py` 对新 SDK 协议回归运行红测，修复后运行模型、图、会话、观察、流式与隐私定向检查，日志使用独立 r-fix 标签。假 HTTP 测试只证明工程协议。

工程通过后，从根目录运行 `D:\newsoft\python.exe output/reference016/phase-b/diagnose_real.py r-fix-20261027-b01-01 --graph`，明确不传 `--thinking-disabled`。这是一次单题复验，直接走已修产品 factory；须完成原问题的真实检索/聚合、72 小时答案与实际来源，事件无错误。工具采用独立 Qdrant、本地 BM25 和 deterministic Dense，不等同于正式 PDF/ONNX/浏览器验收。失败即停止，不自动重试或跑剩余题目。

核对保护指纹，只有计划内产品 factory 可改变；`.env`、正式数据、原失败与历史报告必须保持。结果保存到 `phase-r-report.md`，报告后暂停等待用户验收。

# B 剩余场景续测（2026-10-27）

用户在 R 后明确继续，本轮按 [续测协议](phase-b-resume-20261027-protocol.md)恢复 T017。先对 resume_remaining.py 与原 capture.py 做隔离工程检查，再依次运行 `D:\newsoft\python.exe output/reference016/phase-b/resume_remaining.py prepare`、`... resume_remaining.py supervise`、完成后 `... resume_remaining.py audit`。新目录 remaining-20261027-01 独占，B01 证据只引用，不发新请求。每题先保存首答并由 Codex 写 review，任何非通过停止，不改题/提示或重试。续测报告另存，报告后暂停。

## D 真实 PDF/ONNX 首批（2026-10-28）

用户明确要求开始真实测试后，按 [D 协议](phase-d-real-pdf-20261028-protocol.md)执行 `python -X utf8 output/reference016/phase-d/capture_real_pdf.py prepare`、`... supervise`、`... audit`。本阶段仅 Q1–Q4，原 gold 题/历史/判据保持；准备先核对真实 PDF/ONNX/BM25/快照版本，任何非通过首答停止、后续 not_run。原 BM25 缓存缺失的首次准备失败单列；补齐历史 hash 相同的官方词表后仅恢复准备，不重试模型答案。不运行 pytest/npm/Judge、服务或浏览器，报告后暂停。

## E 全量真实测试（2026-10-28）

用户改为全测、失败继续后，执行 `python -X utf8 output/reference016/phase-e/capture_full_gold.py prepare`、`... supervise`、`... audit`，按 [E 协议](phase-e-full-gold-20261028-protocol.md)重新完整尝试 15 场景/19 轮。各场景独立子进程，900 秒外部 watchdog 只限制本场景，失败继续下一场景；没有每题人工 gate 或重试。全部结束后输出模型原答/正确答案/逐题差异与分类型汇总，报告后暂停。

