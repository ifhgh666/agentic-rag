# A3 单一 RAG 包收敛阶段报告（2026-10-20）

## 阶段目标与授权范围

用户在检查 Agent 节点和提示组织后，明确要求执行此前讨论的单包架构：保留 `backend/app/rag/` 作为唯一实现目录，移入 Agent 图职责，统一导入与提示来源，移除冗余兼容层。本轮完成 A3（T054–T058）的剩余验证、文档与阶段报告；不推进功能指针所指的 009，不修改模型、提示语义、检索算法、API/SSE、正式数据或真实质量结论。

本轮开始时，Agent 架构代码已存在于当前工作区 `backend/app/rag/`。007 的 A3 T055/T056 已标记完成；本轮核验并完成 T057/T058。`.specify/feature.json` 仍指向 `specs/009-cloud-provider-compat`，没有改动该指针。

## 实际架构

- `backend/app/rag/` 包含图、节点、边、状态、提示、schema、工具，以及原有检索、模型、生成、记忆、预算和索引服务。
- `backend/app/main.py` 从 `app.rag.graph` 导入生产 `AgentGraphService`；`pipeline.py` 导出同一对象。
- `prompts.py` 是生产提示和模型消息模板的唯一实现；改写提示版本为 `rewrite-prompt-v6-zh`。结构化模型输出在 `schemas.py` 定义。
- 生产代码、脚本、测试均未发现对 `app.rag_agent`、`app.rag.prompt` 或 `app.rag.model_schema` 的导入引用；旧单数模块和 `QueryDecision` 已无生产实现。
- `backend/app/rag_agent/` 当前只剩旧 `__pycache__/*.pyc`。本轮移除缓存的 PowerShell 命令被自动审查通道的 503 服务错误阻止，未执行删除；这是审查服务不可用，不是安全审查否决。该目录没有 Python 源文件或兼容入口，架构守护测试按源文件及运行导入检查通过。

## 实际验证

工作目录为 `C:\Users\ifhgz\Desktop\agentic-rag\backend`，Python 运行时为 3.12.4。全部 pytest 使用隔离 basetemp 并禁用 pytest 缓存插件。

| 命令 | 退出码与结果 |
|---|---|
| `python -m compileall -q app scripts tests` | 0；编译通过 |
| `rg -n --glob '*.py' '(^|[[:space:]])(from|import)[[:space:]].*(app\.rag_agent|\.prompt\b|\.model_schema\b)' app scripts tests` | 1；无匹配的旧模块导入 |
| 单包导入与对象身份检查（`AgentGraphService`、prompt/schema getters、`rewrite-prompt-v6-zh`、无 `QueryDecision`） | 0；通过 |
| 定向 pytest：架构、提示消费者、graph/state、model loop、deadline、provider、tools、structured query、采集器共 13 个测试模块 | 0；117 passed in 73.90s |
| `python -m pytest -q tests/unit tests/contract tests/integration tests/security --basetemp=../output/prompt007/single-rag-package-20261020/backend-regression -p no:cacheprovider` | 1；588 passed、3 failed in 156.13s |
| 单独复跑 `tests/contract/test_chat_request_deadline.py::test_progress_events_do_not_restart_total_deadline` | 0；1 passed in 0.44s |
| `git diff --check` | 0；无空白错误，Git 对现存 LF 文件输出 CRLF 转换提示 |

完整回归中的两项失败是既有旧 v4 提示文字断言：`test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity` 和 `test_context_prompt_limits_history_and_preserves_unconfirmed_conditions`。它们要求当前 v6 提示不再包含的原句；此前 A2 报告也记录了这两项失败。本轮没有改写 v6 或修改断言掩盖失败。

第三项失败是 `test_progress_events_do_not_restart_total_deadline` 在完整套件运行时超过 150 ms 的时间阈值。独立复跑通过；原始全量失败仍保留，单独结果不能覆盖全量结果。

第一次定向 pytest 启动时指定的 basetemp 父目录尚未创建，pytest setup 失败；创建本阶段隔离目录后重新运行，最终定向结果为 117 passed。该失败不涉及产品代码。

以上均为工程测试，使用 scripted/fake provider、假传输和临时数据，没有调用 Ollama 或云端模型，没有进行正式检索、正式题集评测或真实问答质量验收。未启动/停止服务、读取或重建正式 Qdrant、修改 `.env` 或用户数据。`CURRENT_FAILURES.md` 中既有质量失败结论保持不变。

## 交付与停止点

本轮更新 README、CURRENT_STATUS、007 spec/plan/任务、提示审阅、prompt 函数契约和 quickstart，并新增本报告。T057/T058 标记为已执行；两项既有提示措辞失败和全量套件中的时间测试失败均如实记录。

下一阶段范围尚未授权。本报告后暂停，等待用户验收。
