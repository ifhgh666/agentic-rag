# 016 计划修订与证据复核报告

日期：2026-10-27（用户时区 America/Phoenix）。本轮目标：在用户“继续”指示下处理上一轮计划评审的文档问题。范围为既有 016 规划产物、现有代码/日志的只读核对和文档静态检查；没有执行 A 产品修复或进入 B。

**结论：规划修订完成；阶段 A 工程仍待统一复验、最终审查和总报告，尚未验收。报告后暂停，等待用户验收。**

## 完成文件

| 文件 | 修订内容 |
|---|---|
| [spec.md](spec.md) | 解释参考三字段、提示/硬约束区别、provider 差异、pending 失败边界与工程验收口径 |
| [plan.md](plan.md) | 修正包名称、阶段状态、宪章设计检查、旧限制对照、legacy 归属和运行门槛 |
| [tasks.md](tasks.md) | 保留 T001–T018；补充文件、依赖、验证和全部 15 个需求映射；明确已有实现与未闭合证据 |
| [research.md](research.md) | 按 Decision/Rationale/Alternatives 记录本机 SDK/参考控制流核对，不假定统一 function calling 或新的时限 |
| [data-model.md](data-model.md) | 明确主图/研究状态、reducer、摘要及 pending 状态转换 |
| [contracts/chat.md](contracts/chat.md) | 明确请求校验、动作模型调用边界、公开字段/错误白名单、精确来源匹配和断开边界 |
| [quickstart.md](quickstart.md) | 给出不覆盖旧证据的候选命令、唯一完整 runner、历史失败例外及 B 授权门槛 |
| [test-migration.md](test-migration.md) | 汇总原单元/API/legacy 迁移账本；粗覆盖映射仍交 T013/T015 核对 |
| [checklists/requirements.md](checklists/requirements.md) | 区分设计检查勾选与尚未完成的 T014/T015/T016 |

本报告为第 10 个文档文件；不是 `phase-a-report.md`，不勾选 T016，不更新导航为“A 已完成”。改前原件和工作区快照保存于 `output/reference016/planning-review-20261027-01/`，旧报告、测试原始输出与失败记录未覆盖。

## 上轮发现的处理与修正

| 原发现 | 本次处理 | 尚存工程事项 |
|---|---|---|
| A1 状态不一致 | T003/T004 的原冻结/基线/初始红测、T012 前端完成记录已定位；补为完成，其余有实现但待闭合逐项说明 | T005–T011/T013–T016 仍未勾选，不能按文件存在宣称完成 |
| A2 验收未闭合 | 计划列明允许的两项旧 prompt 例外、跳过/排除和新失败判据；补上先前漏读的 pending 定向修复记录 | 修复后统一完整回归尚未记录 |
| A3 三字段欠精确 | 补必填名称、类型和参考默认解析；纠正上轮可能误导的硬三问/清楚空串联动建议 | 不借补文档重新引入旧 schema；真实模型遵守提示待 B |
| A4 provider 描述漂移 | 准确区分兼容端点 function_calling 与本地 SDK 默认 json_schema，并修正适配包名称 | 本机 SDK 静态核对不证明服务端兼容 |
| A5 限制语义模糊 | 表列分支 8/10、递归 50、4 条历史及 2000/0.9；取消旧应用时限不承诺新墙钟上限 | 真实等待/传输行为待 B |
| A6 legacy 范围欠清 | 列实际冻结模块、独立消费方、旧在线断言替代边界并索引迁移证据 | 旧子报告列出的导入待办不是当前仍失败证明；最终充分性须按实际覆盖审查 |
| A7 公开事件/来源欠精确 | 写出 details 白名单、HTTP/SSE 错误层次、精确文件名交集及去重键 | 产品全面隐私/断开/覆盖审查仍属于 T013/T015 |

特别纠正：cancel 缺少显式 thread_id 是请求校验 HTTP 422；只有显式提供了不存在的线程才是图内 THREAD_NOT_FOUND。new 的清理不调用模型，但处理新题正常调用；cancel 整个动作不调用模型。

## 已有测试证据（本轮未重跑）

| 记录 | 实际历史结果 | 能证明的范围 |
|---|---|---|
| before-full | 819 passed / 3 failed / 24 skipped / 2 deselected，退出 1 | 016 迁移前隔离基线，含旧 deadline 与两项旧 prompt 失败 |
| resume-full-20261026-final | 713 passed / 3 failed / 24 skipped / 2 deselected，退出 1 | 当时完整工程结果，包含 pending 保留失败 |
| resume-pending-transport-fix-20261026 | 4 passed，退出 0 | 后续 pending/普通失败场景定向复验；不能改写前一完整批次 |
| frontend-tool-text-final-tests / build | 40 passed / 构建退出 0 | mock SSE/DOM 工程和构建；没有真实浏览器或模型验收 |

完整证据入口见 [迁移索引](test-migration.md)。前后通过数量不同不表示行为等价，T015 必须按迁移账本解释覆盖变化。原 CURRENT_FAILURES.md、真实模型首答与质量状态保持。

## 实际命令与静态校验

以下目录为 `C:\path\agentic-rag`；工具只读查阅/元数据与文档静态检查不属于产品测试。

| 命令/操作 | 退出状态 | 结果 |
|---|---|---|
| `git status --short --untracked-files=all`、`git diff --no-ext-diff --no-color` | 0 | 保存改前快照，保留既有脏工作区 |
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 解析到 016；已有 plan 未被模板覆盖；实际 Git 分支保持 codex/model-driven-agent-loop |
| `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0 | 载入任务模板和现有设计产物，保留原任务编号/历史完成记录 |
| 下方 `importlib.metadata` 命令 | 0 | 仅查询 8 个已安装发行包版本，没有 import 产品 app 或调用模型 |
| `D:\newsoft\python.exe output/reference016/planning-review-20261027-01/validate_planning.py` | 0 | 报告加入前：9 文档链接/空白/编码、18 任务格式、15/15 需求映射、12 固定 blob 身份及 356 保护文件未变 |

发行包查询的实际命令：

```powershell
& 'D:\newsoft\python.exe' -c 'import importlib.metadata as m; print("\n".join(f"{p}={m.version(p)}" for p in ("langgraph","langchain-core","langchain-openai","langchain-ollama","openai","ollama","tiktoken","httpx")))'
```

静态校验细节见 [document-validation.json](../../output/reference016/planning-review-20261027-01/document-validation.json)。报告加入后的完整复核命令为 `D:\newsoft\python.exe output/reference016/planning-review-20261027-01/validate_planning.py document-validation-final.json`，结果见 [document-validation-final.json](../../output/reference016/planning-review-20261027-01/document-validation-final.json)：10 个文档、356 保护文件无变动、退出 0。报告补全实际命令后另用 `document-validation-report-final.json` 复核，不覆盖前两轮。保护检查覆盖本轮前存在的产品源文件、测试、前端、README/状态导航、失败清单及 phase-a 顶层原证据；未打开 `.env` 或正式知识数据，不能借此声称重新验证正式索引。

项目内使用 [speckit-plan](../../.agents/skills/speckit-plan/SKILL.md) / [speckit-tasks](../../.agents/skills/speckit-tasks/SKILL.md)，执行研究、技术上下文、宪章检查、设计/契约和任务映射修订。一个只读研究子代理核对了 SDK 默认与参考控制流，没有写文件或执行产品测试。`.specify/extensions.yml` 不存在，因此无前后置 hooks。

一致性复核：11 个 FR + 4 个 SC 均有任务映射；18 项任务中 US1 6 项、US2 3 项、跨故事 9 项；5 项完成证据、13 项未勾选（含 B 两项）。没有发现新增宪章级设计冲突；这不是代码正确性或运行通过结论。

本轮 pytest/npm、真实模型/云端/Judge、正式数据操作、服务启动/重启、提交/推送均为 0。未修改产品代码、配置或历史证据。文档静态检查不能消除真实问答质量失败。

## 下一范围和停止点

本轮交付到规划修订为止。若后续明确授权 A 收尾，按现有 T005–T015 的未闭合范围核对实现、补齐必要覆盖、运行修复后的完整隔离批次、保存 A 总报告并更新导航；不能将本轮报告视为 A 验收，也不能进入 B。B 仍要求用户先验收 A 并明确继续。

**报告后暂停，等待用户验收。**
