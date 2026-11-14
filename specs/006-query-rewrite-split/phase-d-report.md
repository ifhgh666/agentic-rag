# 006 阶段 D 报告：观测与工程回归

日期：2026-10-11（Asia/Shanghai）  
授权范围：用户确认 C 已完成，要求完善滞后状态文字并执行 D（T022–T029）。  
前置：A–C 已有报告，C 记录为 115 passed；规格质量清单 16/16 项完成。  
结论：**D 工程工作完成、最终检查通过，等待用户验收；E/F 真实质量未评估。**

**报告后暂停，等待用户验收。**

## 完成内容与文件

| 任务 | 实际变更与验证 |
|---|---|
| T022 | `backend/tests/contract/test_chat_stream_api.py` 覆盖三字段映射、保持原文仍有处理事件、模型/缓存/待办状态/取消来源、调用 ID、版本 1 和失败零重试；`test_chat_request_deadline.py` 覆盖 API 300 秒配置上限与迟到入口/usage 不发送。实际到期等待使用缩短模拟，未等待真实 300 秒。 |
| T023 | `backend/app/rag/graph_state.py` 与 `graph.py` 保存动作/待办状态来源；`pipeline.py` 保留既有事件与版本 1，增量传递 source、relation_source、action、budget_node=query_analysis、真实 model_call_id 和耗时、replayed。没有调用时不伪造 ID 或耗时。 |
| T024 | `frontend/src/types/api.ts`、`api/client.ts`、`components/ProcessPanel.tsx` 及对应测试同步可选增量字段；兼容旧版本 1 分析，忽略未知版本和无效字段映射；显示“问题补全与拆分”、缓存/动作/状态来源及执行后回放。 |
| T025 | 新增 `backend/tests/security/test_query_rewrite_log_privacy.py`；公共模型遥测使用字段白名单，`backend/app/observability/execution.py` 隐藏嵌套原始消息/历史/摘要等诊断字段。已有本地 loop_traces 仍保存完整诊断；未增加接口或扩大读取范围。`test_request_deadline.py` 增加带原待办和确认补充的迟到回滚检查。 |
| T026 | README、CURRENT_STATUS 及 006 的 spec/plan/tasks、契约、数据模型、quickstart、验收矩阵同步 A–D 工程进度与 E/F 未测状态；历史 research 加导航说明，原规划研究和 A–C 报告保留。预算以当前代码和非敏感配置核对为 8/12、入口 1、300/120 秒。 |
| T027 | 后端 unit/contract/integration/security 全量工程回归最终 494 passed。发现并迁移 `test_v3_5_cost_control.py` 的旧四字段缓存夹具，保留线程/索引隔离断言，增加实际 model/cache 来源断言。 |
| T028 | 前端 8 个文件、26 项测试通过；TypeScript 与 Vite 生产构建通过。构建产生的既有 `frontend/tsconfig.tsbuildinfo` 更新保留。 |
| T029 | 保存本报告、勾选 T022–T029 并同步停止点；T030–T035 保持未勾选。 |

未修改检索算法、模型配置、依赖或正式知识库；未提交、推送、重启服务或运行真实模型。

## 实际命令、退出码与原始记录

记录目录：[engineering/phase-d-20261011](../../output/query-rewrite-v1/engineering/phase-d-20261011/)。运行器为 [run_query006_phase_d.py](../../output/run_query006_phase_d.py)，每个标签独立保存 `.log` 与 `.json`，拒绝覆盖记录。

下面运行器命令均在 `C:\Users\ifhgz\Desktop\agentic-rag` 执行；后端子进程 cwd 为 `backend`，前端子进程 cwd 为 `frontend`：

```powershell
python output/run_query006_phase_d.py d-targeted-red-01 backend -q tests/contract/test_chat_stream_api.py tests/contract/test_chat_request_deadline.py tests/security/test_query_rewrite_log_privacy.py
python output/run_query006_phase_d.py d-targeted-red-02 backend -q tests/contract/test_chat_stream_api.py tests/contract/test_chat_request_deadline.py tests/security/test_query_rewrite_log_privacy.py
python output/run_query006_phase_d.py d-targeted-green-01 backend -q tests/contract/test_chat_stream_api.py tests/contract/test_chat_request_deadline.py tests/security/test_query_rewrite_log_privacy.py tests/unit/test_request_deadline.py tests/unit/test_pipeline_events.py
python output/run_query006_phase_d.py d-backend-full-01 backend -q tests/unit tests/contract tests/integration tests/security
python output/run_query006_phase_d.py d-backend-full-02 backend -q tests/unit tests/contract tests/integration tests/security
python output/run_query006_phase_d.py d-frontend-test-01 frontend-test
python output/run_query006_phase_d.py d-frontend-build-01 frontend-build
```

后端实际使用 `D:\newsoft\python.exe -m pytest -p no:cacheprovider --basetemp <记录目录>/pytest-<标签> ...`。每个 fixture 的 DATA_DIR 为独立 tmp_path，QDRANT_DB_PATH 是相对该目录的独立名称；LLM_PROVIDER=fake、EMBEDDING_BACKEND=deterministic、SPARSE_OFFLINE_FALLBACK=true。关闭 pytest 缓存插件仅避免既有缓存写权限问题，不跳过任何测试。

| 记录 | 退出码 | 结果 | 子进程记录耗时 |
|---|---|---|---|
| [d-targeted-red-01](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-targeted-red-01.log) | 1 | 2 个预期隐私断言失败、12 个 setup error。运行器误用共享绝对 Qdrant 路径导致临时锁冲突，随后改为每个测试 data_dir 下的相对路径；未触碰正式索引。 | 24.828 秒 |
| [d-targeted-red-02](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-targeted-red-02.log) | 1 | 4 failed、10 passed。实现前复现来源/关联缺失和公共历史诊断泄漏。 | 18.641 秒 |
| [d-targeted-green-01](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-targeted-green-01.log) | 0 | 19 passed。 | 19.953 秒 |
| [d-backend-full-01](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-backend-full-01.log) | 1 | 493 passed、1 failed；旧缓存测试仍输出 relation 和 null 澄清，违反三字段严格契约。 | 100.000 秒 |
| [d-backend-full-02](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-backend-full-02.log) | 0 | **494 passed**，pytest 自身耗时 78.35 秒；无失败或 warning。 | 89.735 秒 |
| [d-frontend-test-01](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-frontend-test-01.log) | 0 | 实际 `npm test -- --run`：**8 个文件、26 tests passed**。 | 36.671 秒 |
| [d-frontend-build-01](../../output/query-rewrite-v1/engineering/phase-d-20261011/d-frontend-build-01.log) | 0 | 实际 `npm run build`：`tsc -b` 与 `vite build` 完成，92 个模块转换。 | 14.329 秒 |

首次失败、中间错误和最终结果分别保存，没有挑选真实模型重试成绩。本表耗时是工程命令耗时，不是模型问答时延。

其他检查：

- `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`：退出 0，定位 006；checklists/requirements.md 为 16/16，未修改清单标记。
- `git diff --check`：退出 0；既有修改及未跟踪文件均保留。
- 非敏感 `Settings()` 白名单读取：退出 0，确认 Ollama qwen3:4b-instruct、8/12 次总模型预算、入口 1、工具 16、300 秒请求、120 秒模型等待、4096/3072/768/256 窗口配置及 300 秒/256 条缓存。
- `python output/check_query006_phase_d_artifacts.py`：首次退出 1，辅助校验误把 A 基线的知识库相对路径按仓库根解析；[首次辅助错误记录](../../output/query-rewrite-v1/engineering/phase-d-20261011/artifact-check-01.json)保留。修正为 backend/data 后退出 0，[artifact-check-02.json](../../output/query-rewrite-v1/engineering/phase-d-20261011/artifact-check-02.json)确认 11 个正式知识库文件与 A 基线一致、.env 与 A 基线一致、CURRENT_FAILURES 与 A 基线一致、10 个文档 UTF-8 和本地链接有效。这是与历史 A 基线的比较，未冒称本轮开始前新增的快照。
- `.specify/extensions.yml` 不存在，技能前后扩展钩子均无需执行。

## 工程与真实质量的边界

后端使用 fake/scripted provider、确定性嵌入和临时索引；前端使用 Vitest/JS DOM。通过结果证明协议、来源、预算计费键、日志隐私、动作适配、期限与迟到隔离等工程行为。

真实 Ollama 问题补全/拆分、数字保真、条件推导、完整答案和最终比较仍未评估。没有产生真实模型调用/工具数量、请求 ID、Token 成绩、答案分数或模型时延结论。300 秒 API 上限通过配置/模拟测试验证，真实 300 秒到期行为未新增实测。

`CURRENT_FAILURES.md` 未修改。005 Q16 的 `400 ms` 数字失真仍未复验通过，C-UV 历史超时仍待真实补测；未勾选 005 T018，未开始 005 D 或 30 题正式评测。A–C 历史报告和原始证据未覆盖。

## 下一阶段与停止点

任务 T001–T029 工程勾选完成；D 待用户验收。E（T030–T032）在另行授权后才实现有限采集工具并进行固定 17 次真实入口首次验收；E 报告后再次暂停。F 的正常 API 三题补测同样需要独立授权，不包含在本轮。

**报告后暂停，等待用户验收。**
