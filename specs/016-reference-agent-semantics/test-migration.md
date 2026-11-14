# 016 测试迁移与证据索引

2026-10-27 规划复核整理。此文件索引原记录，不覆盖历史内容，也不证明 T013/T015 已完成最终审查。任务见 [tasks.md](tasks.md)，工程门槛见 [quickstart.md](quickstart.md)。

| 范围 | 原始账本/证据 | 本轮判定 |
|---|---|---|
| 迁移前源码与 Git 工作区 | `output/reference016/phase-a/before/`、git-status-before.txt、git-diff-before.txt、before-hashes.json | 既有工作快照，不以 Git HEAD 大 diff 代表 016 改动 |
| 迁移前完整结果 | [before-full.log](../../output/reference016/phase-a/before-full.log)、同名 json/guard | 819 passed / 3 failed / 24 skipped / 2 deselected，非全通过 |
| 独立旧接口及采集器导入 | [legacy-test-migration.md](../../output/reference016/phase-a/legacy-test-migration.md) | 该子报告的剩余导入问题是当时事实；后续完整运行已完成收集，不能将旧列表全部当作当前错误 |
| 原在线单元断言迁移 | [unit-test-migration.md](../../output/reference016/phase-a/unit-test-migration.md) | 有旧 nodeid、替代位置和依据；当前充分性仍需 T015 按函数内容复核 |
| API/SSE/安全/集成迁移 | [api-test-migration.json](../../output/reference016/phase-a/api-test-migration.json) | 有 retained/replaced 分类；仅指向整个文件的条目须核对实际对应场景，不能把粗映射算完成证明 |
| 参考来源/对照 | [manifest.json](../../backend/tests/fixtures/reference016/manifest.json)、test_reference016_parity.py、reference_baseline.py | blob 身份与行为对照是不同证明；不能只验 hash 宣称行为相同 |
| 前端变化 | [frontend-task-report.md](../../output/reference016/phase-a/frontend-task-report.md)及后续补充日志 | 旧报告较早计数保留；最近工具正文日志为 40 passed/构建 0 |
| 最近完整批次 | [resume-full-20261026-final.log](../../output/reference016/phase-a/resume-full-20261026-final.log)、同名 json/guard | 713 passed / 3 failed / 24 skipped / 2 deselected，退出 1 |
| pending 修复后定向 | [resume-pending-transport-fix-20261026.log](../../output/reference016/phase-a/resume-pending-transport-fix-20261026.log)、同名 json/guard | 4 passed，退出 0；缺修复后统一完整批次 |

## 保留、替代和收尾要求

1. 独立 QueryAnalyzer、ModelCallRunner、AnswerGenerator/AnswerEvaluator、ConversationMemory、EvidenceSelector 等旧 API 的测试保留原语义，导入实际冻结依赖；不能接回正常图。
2. 旧在线预算、准入、分页、核验、单问跳过聚合、双会话状态和截止断言由 016 替代；保存原断言/快照，逐 nodeid 说明替代依据和现行覆盖。没有覆盖的条目仍是未完成工作，不能仅删除。
3. 旧 ModelAgentLoop/ContextAdmission 不复制成第二套生产图。测试使用当前参考图或独立旧接口，区分行为替代与纯导入迁移。
4. 两项已知 legacy prompt 措辞断言保留失败；原 deadline 失败若因撤销旧在线策略而替代，需保留原日志与迁移理由，不宣称原超时缺陷真实复验通过。
5. 不新增 skip/xfail/全局忽略造通过；既有 24 正式 PDF 跳过、2 真实 Dense 排除在每批结果中单列。测试数量减少必须按账本解释，工程结果不改写真实答复质量。
6. 最终 T015 审查覆盖原账本所有条目、当前执行代码和接口隐私；归档完整结果后才决定勾选 T005–T011/T013–T016。本次仅索引和文档复核，未进行产品全面审查。

## 2026-10-27 A 收尾追加

上述段落记录规划复核当时状态。用户随后继续授权 A 收尾，两位独立审查者已核对当前实现及原迁移账本；新增发现和修复分别保留于 `output/reference016/phase-a/a-close-review-20261027-01.md`。

- 重复原题补充（含传输失败后）取消/新题的四项参数化回归，以及历史已完成同名问题保留检查，补入 `backend/tests/integration/test_reference016_session.py`。
- 真实 ASGI 断开且 SDK worker 未返回时的队列消费者退出检查，补入 `backend/tests/contract/test_reference016_disconnect.py`。
- `test_reference016_parity.py` 除消息/调用/输出外，对照实际节点名称、深度和访问次数；只忽略分支完成顺序，不忽略节点次数。
- 六项新增缺陷检查在修改产品代码前均失败；修复后相关 29 项通过，parity 8 项通过；完整 `a-close-full-20261027-01` 为 720 passed / 两项旧失败 / 24 skipped / 2 deselected，退出 1。原失败日志不覆盖。

AST 盘点为旧 502 个测试函数→当前 442 个，149 个原函数名退役、89 个新增、11 个同名函数体变化。149 个退役函数均能在原 unit/API 账本找到明确条目，见 `a-close-inventory-20261027-01.json`；映射存在不单独证明语义等价，已结合当前具体场景及独立审查核对。

| 目录 | 旧函数 | 当前函数 |
|---|---:|---:|
| unit | 428 | 393 |
| contract | 30 | 22 |
| integration | 39 | 21 |
| security | 5 | 6 |

原完整 848 个参数化 case（819+3+24+2）→当前 748（720+2+24+2），不能与函数数量混用。主要减少来自撤销和合并旧在线额度、准入、分页、核验、双会话和截止的细碎断言，例如 batch_context_admission 的旧 8 函数由 3 个参考批次场景承载；独立旧接口保持。不能宣称等量回归或数量减少证明质量提升。原 132 份历史证据 hash 保持，两项 legacy prompt 失败不改写。
