# 016 阶段 A 报告：参考 Agent 语义与工程收尾

日期：2026-10-27（用户时区 America/Phoenix）。功能：[恢复参考 Agent 执行语义](spec.md)。固定参考：GiovanniPasq/agentic-rag-for-dummies / `394c4f7519e41923d695af1efa75b6afec76c553`。

**结论：A=T001–T016 工程工作完成，按无新增失败、保留既有例外的门槛交付，待用户验收。完整后端 720 passed / 2 failed / 24 skipped / 2 deselected，退出 1；前端 40 passed，构建退出 0。不能写成全部测试通过或真实问答质量通过。报告后暂停，等待用户验收。**

## 目标、授权与交付范围

用户在 [规划修订报告](phase-planning-review-20261027-report.md)后明确“继续”，本轮执行到 A 收尾，未进入 B。原始快照、红测、失败与历次首答保持。采用项目内 [speckit-implement](../../.agents/skills/speckit-implement/SKILL.md)；check-prerequisites 退出 0 定位 016，现有 ignore 覆盖 Python/Node/本地配置/数据/输出，无需改动。无 `.specify/extensions.yml`，无前后置 hooks。

规格清单 19 项中 16 项设计检查已勾选、3 项工程收尾标记未勾选；用户这次继续明确覆盖这三项。按技能的只读清单规则没有替 reviewer 勾选，实际工程完成状态在 [tasks.md](tasks.md)记录；它们都不等同用户验收。

阶段整体已恢复参考主图/六节点研究子图、消息 reducer、历史摘要与研究压缩、原始提示和宽松三字段、完整 Parent、原生 SDK 模型、唯一 checkpoint、动作互斥及实时公开交付。旧独立 API/冻结依赖保留，正常入口无旧主图/预算/截止/准入/核验回退。来源是最终 Sources 与本次工具记录的交集，用量为观测、上限 null。

## 完成文件与本轮修复

| 范围 | 主要文件 | 实际完成 |
|---|---|---|
| 参考核心（前序实现，本轮核对） | backend/app/rag/graph.py、nodes.py、edges.py、graph_state.py、prompts.py、schemas.py、tools.py | 图/节点/状态/提示/schema 对照、工具适配及压缩/边界覆盖 |
| 模型/会话/交付 | backend/app/core/reference_model.py、reference_session.py、reference_observation.py、pipeline.py；backend/app/api/chat.py；backend/app/main.py | provider 适配、checkpoint、动作、来源、白名单、统计和装配 |
| legacy 与测试迁移 | backend/app/core/legacy_*.py 及独立旧消费方；[迁移索引](test-migration.md) | 旧语义保留到独立消费方，退休在线断言逐项有原账本入口 |
| 前端（本轮无源改动） | frontend/src/pages/Chat.tsx、api/client.ts、components/ProcessPanel.tsx、types/api.ts 及测试 | 默认补充、隐藏核验、实时节点、工具正文、累计答案/null 用量；重跑测试和构建 |
| 交接 | README.md、docs/CURRENT_STATUS.md、specs/016-reference-agent-semantics/ | 任务状态、当前导航、工程/真实边界、报告 |

本轮相对 `a-close-start-20261027-01/` 只改变 **2 个产品 Python 文件、3 个测试文件**，详见 [源码盘点](../../output/reference016/phase-a/a-close-inventory-20261027-01.json)和同目录 app/tests delta patch；Git HEAD 的累计大 diff 不代表本轮改动。

1. `core/reference_session.py`：取消/新题清理从“尾部按原题文本匹配”改为先定位本轮首个命名 clarification，再向前找原题。重复原题补充（包括入口传输失败后尚未命名的补充）不再误当起点；保留此前已完成的同名问题。`integration/test_reference016_session.py` 增加 5 个参数化 case。
2. `api/chat.py`：断开时直接非阻塞放入哨兵，唤醒被 asyncio.to_thread 留下的 queue.get 消费线程；队列满时已有可读项。`contract/test_reference016_disconnect.py` 通过真实 ASGI http.disconnect，在受控模型 worker 未返回时证明消费者退出。当前 SDK 调用仍可能等待，不新增模型截止策略。
3. `unit/test_reference016_parity.py`：实际 stream updates 增加节点名称、深度和访问次数对照；分支完成顺序不确定，不将其强行排序为执行时间保证。

## 实际验证命令与结果

调用 runner 的工作目录为 `C:\Users\ifhgz\Desktop\agentic-rag`，形式为 `D:\newsoft\python.exe output/reference016/phase-a/run.py <标签> [测试目标]`；它生成的每份 JSON 均包含**底层完整 argv、backend 工作目录、真实退出码和 guard hash**。下表链接到实际命令，未省略真实失败证据。

| 标签/命令记录 | 结果 | 退出码 | 原始输出 |
|---|---|---:|---|
| [a-close-focused-20261027-01.json](../../output/reference016/phase-a/a-close-focused-20261027-01.json) | 核心/工具/架构/会话/事件/隐私 49 passed，21.33 s | 0 | [log](../../output/reference016/phase-a/a-close-focused-20261027-01.log) |
| [a-close-red-review-20261027-01.json](../../output/reference016/phase-a/a-close-red-review-20261027-01.json) | 修改产品前，5 个会话 case + ASGI 断开共 6 failed，4.05 s | 1 | [log](../../output/reference016/phase-a/a-close-red-review-20261027-01.log) |
| [a-close-green-review-20261027-01.json](../../output/reference016/phase-a/a-close-green-review-20261027-01.json) | 修复后相关会话/流式/兼容/pending 29 passed，9.63 s | 0 | [log](../../output/reference016/phase-a/a-close-green-review-20261027-01.log) |
| [a-close-parity-20261027-01.json](../../output/reference016/phase-a/a-close-parity-20261027-01.json) | 固定参考及节点访问对照 8 passed，1.44 s | 0 | [log](../../output/reference016/phase-a/a-close-parity-20261027-01.log) |
| [a-close-full-20261027-01.json](../../output/reference016/phase-a/a-close-full-20261027-01.json) | 720 passed / 2 failed / 24 skipped / 2 deselected，174.99 s | 1 | [log](../../output/reference016/phase-a/a-close-full-20261027-01.log) |
| [npm.cmd test -- --run](../../output/reference016/phase-a/a-close-frontend-tests-20261027-01.json) | frontend 工作目录，8 文件 / 40 passed | 0 | [log](../../output/reference016/phase-a/a-close-frontend-tests-20261027-01.log) |
| [npm.cmd run build](../../output/reference016/phase-a/a-close-frontend-build-20261027-01.json) | frontend 工作目录，tsc + Vite 构建成功 | 0 | [log](../../output/reference016/phase-a/a-close-frontend-build-20261027-01.log) |

完整后端使用 fake/scripted 模型、deterministic embedding 和临时 Qdrant，不运行真实服务。guard hash 保持 `4822850e4ab8dad835ef7c64477bbe4ba828598483fe0a44d6b66ba12ef5063b`，全部新批次 blocked_attempts=[]；4 个正式路径可用性探测被屏蔽，没有用正式文档测试。实际跳过/排除清单见 [full guard](../../output/reference016/phase-a/a-close-full-20261027-01-guard.json)和 full JSON：24 项正式 PDF 来源检查跳过、两项真实 Dense 检查排除，不算通过。无新增 skip/xfail/deselect 或 collection error。

此前 before-full 为 819 passed / 3 failed；resume-full-20261026-final 为 713 passed / 3 failed，其中 pending 保留失败已在本轮完整结果消除。原始成绩不覆盖，也不把三个不同版本合成稳定性成绩。所有结果是工程验证，不能证明真实模型按提示正确拆分/压缩/回答或实际语义检索质量。

## 失败与限制

以下两项原 legacy prompt 措辞断言仍失败，按批准计划作为有记录的历史例外保留；未改 prompt、未改预期、未跳过：

- `tests/unit/test_query_rewrite_v1.py::test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity`：冻结提示没有旧断言要求的“共享型号、电压、持续时间”等字面措辞。
- `tests/unit/test_v4_query_analysis.py::test_context_prompt_limits_history_and_preserves_unconfirmed_conditions`：冻结提示没有“只使用必要历史”字面措辞。

当前工程结论是“无新增失败”，pytest 退出仍为 1。正式模型兼容、真实检索/答案/中文输出/三问提示遵循、压缩保真、真实网络等待及浏览器交互均未新增验收。取消旧 300/120 秒后不承诺替代墙钟上限；断开修复只保证队列消费者退出，不声称 SDK/图 worker 立即终止或 checkpoint 事务回滚。

## 独立审查与测试迁移

采用 [code-review 技能](../../../../.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.1/skills/engineering/code-review/SKILL.md)的双轴审查，以 016 原快照为固定点；两个子代理没有执行产品测试或编辑文件。完整发现与复核见 [独立审查记录](../../output/reference016/phase-a/a-close-review-20261027-01.md)。

### Standards

初次 1 项 P2：ASGI 断开遗留消费者；依据宪章稳定传输契约和仓库 SSE 约定。最小唤醒修复及真实 ASGI 回归后，复核未发现新增资源泄漏。未引入气味驱动重构。

### Spec

初次 2 项 P2：重复原题补充导致未完成轮清理不完整；ASGI 断开消费者不退出。均违反已有 FR-006/断开边界，最小修复后独立复核无残余可复现缺陷。

两轴初次分别 1 / 2 项（断开为重合问题），最终未解决分别 0 / 0；不以某一轴替代另一轴。

AST 测试函数 502→442：unit 428→393、contract 30→22、integration 39→21、security 5→6。149 个旧函数名退役、89 个新增、11 个同名函数体变化；退役函数均有原迁移账本条目，无未记账删除。参数化完整 case 为 848→748，不能与函数数混用。减少主要来自取消/合并旧在线额度、准入、分页、核验、双会话和截止的细碎断言；独立 legacy 能力保留。现行路由、批次、完整 Parent、聚合、会话和观测按新规格验证，不宣称等量或新旧算法等价。详见 [迁移说明](test-migration.md)。

额外静态核对：30 个参考图/节点/边/状态/schema/提示定义仅剥离 log_route 与 logged_node 观测包装后 AST 无差异；未标准化业务判断或提示正文。原始未标准化比较中两条边有移除日志调用的差异，亦已保留证据。工具/基础设施适配差异按契约单列，不混称 AST 相同。

## 保护核对与任务状态

实际保护命令：

```powershell
& 'D:\newsoft\python.exe' output/reference016/phase-a/resume_audit.py a-close-before-20261027-01
& 'D:\newsoft\python.exe' output/reference016/phase-a/resume_audit.py a-close-after-20261027-01 a-close-before-20261027-01
& 'D:\newsoft\python.exe' output/reference016/phase-a/a-close-inventory-20261027.py
```

均退出 0。前后 86 项 `.env`、knowledge、正式数据/索引及 CURRENT_FAILURES.md 指纹一致，read_errors=0；对 016 原始 12 项代码/配置保护无差异，原 132 份顶层历史证据 hash 保持。正式内容仅用于只读 hash，不作为测试输入或模型资源加载。原文件内容不在公开报告输出，见 [after audit](../../output/reference016/phase-a/a-close-after-20261027-01.json)及 inventory。

`git diff --check` 对本轮受影响已跟踪源文件退出 0；新增文件由最终静态校验核对 UTF-8/结构/链接。完整命令、原始日志和改前快照均保留在 `output/reference016/phase-a/`。需求/任务和报告预发布静态检查记录为 `a-close-document-validation-20261027-01.json`。

T001–T016 均为工程完成，T017–T018 保持未执行。CURRENT_FAILURES.md 无变化；旧 Q16/C-UV 和其他真实模型质量失败不因 fake 通过而解决。实际 Git 分支保持 `codex/model-driven-agent-loop`；未提交、推送或发布。

本阶段真实模型/云端/Judge 调用、正式索引写入/重建、服务启动/重启均为 0。内部测试调用、认证和检索均使用合成/临时隔离资源。

## 下一阶段范围

B 需用户验收本报告并明确指示继续后另行运行：冻结现有真实 provider/model 身份与临时知识库，先明确工具/澄清/压缩/聚合样例及逐题判据，再保存首次答复、请求标识、实际次数/用量/耗时、失败和限制；不自动正式题库、不重试挑最好成绩、不切 provider。报告后的沉默或时间经过不构成 B 授权。

**报告后暂停，等待用户验收。**
