# 016 阶段 B 首次真实验收报告

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-27（用户时区 America/Phoenix）。授权：用户在 [A 总报告](phase-a-report.md)后明确“继续”，只执行 B=T017–T018。[B 协议](phase-b-protocol.md)在真实调用前冻结场景、判据和失败停止规则。

**结论：B 未通过。0 通过 / 1 失败 / 0 待定 / 4 未运行。B01 在入口 rewrite_query 请求链以 OpenAIInvalidRequestError 失败，未生成答案、未执行检索；未重试。T017 部分完成，T018 失败报告交付。报告后暂停，等待用户验收。**

## 冻结条件与实际范围

- 当前实际身份是 `openai_compatible / deepseek-flash`，temperature=0、seed=42，沿用原端点及密钥；仅保存端点 hash 和密钥已配置标识。云端模型别名未暴露固定权重修订，不伪称冻结了服务端权重。
- 临时数据路径：`output/reference016/phase-b/first-20261027-01/knowledge/`，两份合成规程分别 97 / 11,457 字符，各 1 个真实 Qdrant point。DocumentStore、IndexStore、Retriever 和原图工具均为产品实际实现；临时配置使用 deterministic Dense / local BM25，检索预检各返回 1 条。
- 模型使用原 `AgentGraphService/RagPipeline` 和原 SDK factory（兼容入口 function_calling，max_retries=0）；未修改任何产品 Python 源码、提示/schema、模型身份或配置文件。Token 估算仅采用参考字符回退路径，避免资源下载。
- 没有 PDF 上传/解析、真实 ONNX 语义向量、HTTP 服务/认证/浏览器端到端实测；这些不能从本轮结果推断通过。真实调用只涉及合成问题/规程，正式知识内容不作为模型或工具测试输入。

冻结资料、问题/预期、产品源码 hash、collector hash、索引版本及身份见 [manifest](../../output/reference016/phase-b/first-20261027-01/manifest.json) / [fixture](../../output/reference016/phase-b/first-20261027-01/fixture.json)。首答和已有批次使用独占创建，不可同名重跑覆盖。

## 首答、事件与判定

| case | 原始输入/范围 | 本轮状态 |
|---|---|---|
| B01 单问工具 | ZX-731 的巡检周期是多久？ | failed：入口请求链异常，未取得答案 |
| B02 澄清 | 无历史问“它的巡检周期是多久？” | not_run |
| B03 默认补充 | 沿 B02 线程补充 ZX-731 | not_run |
| B04 长上下文 | NL-640 五步维护和校验码，观察实际压缩 | not_run |
| B05 多问聚合 | ZX-731 周期/记录期限/归档容量 | not_run |

B01 request_id：`[运行标识已移除]`。模型尝试开始到错误记录 416 ms；usage 请求耗时 446 ms，采集器整次耗时 448 ms，两个耗时口径分别保留。最终 `failed / RAG_PIPELINE_FAILED`；analysis、clarification、answer 均未产生，工具 0、来源 0。观察异常类型为 `OpenAIInvalidRequestError`。

模型尝试计数 1、cloud 路径计数 1，均来自实际回调/配置统计；**不证明请求被远端受理**。失败路径输出 Token=0、usage_source=estimate，为异常占位值，实际远端 Token/计费不可得，不报告为实测零消耗。上限 null，没有产品 budget_exceeded。

判定：B01 要求清楚入口、真实搜索、正确聚合和真实来源，本次在入口请求阶段失败，结构流程未完成；语义正确性未评估。原始首答/错误记录与 Codex 审阅分别保留，未把错误转换为“没有知识”或可用答案。

证据：[B01 raw](../../output/reference016/phase-b/first-20261027-01/B01.raw.json)、[事件 JSONL](../../output/reference016/phase-b/first-20261027-01/B01.events.jsonl)、[review](../../output/reference016/phase-b/first-20261027-01/B01.review.json)、[summary](../../output/reference016/phase-b/first-20261027-01/summary.json)。当前日志按隐私契约没有异常正文，因此具体被拒绝参数、SDK/远端拒绝层次与根因尚未确定，不能断言端点不支持某一特性。

## 实际命令和工程/真实区别

工作目录均为 `C:\path\agentic-rag`，没有依赖安装或服务启动。

| 实际命令 | 退出码 | 结果 |
|---|---:|---|
| `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0 | 定位既有 016；保持当前分支/功能指针 |
| `.specify/scripts/powershell/setup-plan.ps1 -Json`、`setup-tasks.ps1 -Json` | 0 | 使用项目 Spec Kit 模板补齐 B 操作协议，不覆盖既有 A 报告或任务编号 |
| `D:\newsoft\python.exe output/reference016/phase-a/run.py b-collector-engineering-20261027-01 ../output/reference016/phase-b/test_capture.py` | 0 | 4 项隔离工程检查通过；没有真实模型/网络/正式数据访问 |
| `D:\newsoft\python.exe output/reference016/phase-b/capture.py prepare` | 0 | 冻结身份/资料/源码并建立两份临时真实 Qdrant 索引，未调用模型 |
| `D:\newsoft\python.exe output/reference016/phase-b/capture.py supervise` | 1 | 子进程 real 首题失败，review 后按规则结束，watchdog 未触发 |
| `D:\newsoft\python.exe output/reference016/phase-b/capture.py audit` | 0 | 308 项指纹无差异 |

工程检查证明身份投影不包含测试凭据/端点、首次答复文件不被覆盖、临时检索目录隔离及采集记录/计数，不证明真实 B 质量通过。实际命令 argv/cwd 见 [工程 JSON](../../output/reference016/phase-a/b-collector-engineering-20261027-01.json)与[真实 command.json](../../output/reference016/phase-b/first-20261027-01/command.json)；工程/真实原始输出分别为同名工程 log 和真实目录 capture.log。

外部 supervisor 900 秒是整个自建采集进程的观察上限，未改变产品 SDK 或图的截止；本次正常以首题失败退出，未超时、未杀进程。每题保存后等待 Codex review，通过才可进入下一题；B01 失败 review 后停止，B02–B05 没有发出模型请求。

## 完成文件、保护与限制

- 本轮新增 collector/4 项工程测试、冻结数据/模型/源码 manifest、临时知识库、逐事件记录/首答/review/summary/命令证据，均在 `output/reference016/phase-b/`；工程日志另有独立 b-collector 标签。
- 维护 `specs/016-reference-agent-semantics/phase-b-protocol.md`、plan/spec/tasks/quickstart、README 与 docs/CURRENT_STATUS.md，新增 [016 当前失败清单](CURRENT_FAILURES.md)。这是 B-FAIL-001；根目录 005 的 CURRENT_FAILURES.md 不改写，原真实失败不变。
- [before](../../output/reference016/phase-b/first-20261027-01/boundary-before.json) / [after](../../output/reference016/phase-b/first-20261027-01/boundary-after.json) 的 308 项指纹无差异，包括 `.env`、产品 Python、正式数据/索引、A 总报告与 A 顶层原证据。正式数据仅只读 hash 校验，不用于测试；模型/工具后续打开正式路径被采集器保护拒绝。
- 无产品源码/前端改动，因此不重复 A 全量回归；A 的 720 passed / 两项既有失败是历史工程结果，不是本轮重新运行。没有真实模型业务重试、Judge、云端切换、正式索引写入/重建、服务启动/重启、提交或推送。
- spec-quality 清单保持 reviewer 的只读标记；项目 Spec Kit plan/tasks/implement 流程沿用原 A/B 边界，没有 `.specify/extensions.yml` hooks。

T017 冻结/采集器/首题已执行，但四个必需场景未运行，仍不勾选；T018 记录这次失败和限制后完成。不能把工程检查通过或完成失败报告写成阶段 B 质量通过。

## 下一范围与停止点

后续需用户明确授权诊断 B01 的 SDK/兼容端点原生入口请求失败；在已有证据基础上补齐安全的失败类别/参数证据，不猜测根因。任何修复或新批次补测都另行记录，保留此次首次失败，不自动重试、改提示、切 provider、运行剩余场景或正式题库。

**报告后暂停，等待用户验收。**
