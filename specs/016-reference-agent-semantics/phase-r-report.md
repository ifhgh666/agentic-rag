# 016 R：DeepSeek Flash 兼容修复报告

日期：2026-10-27（America/Phoenix）。用户在真实诊断及错误原因解释后明确“继续”。本阶段仅正式修复当前模型的传输兼容问题、运行相关工程检查并真实复验 B01；原 A/B/诊断记录保留，不执行剩余 B 场景。

**结论：R 修复完成，待用户验收。51 项定向工程检查通过；无临时模型参数的产品工厂真实 B01 通过。当前正常参考图的新建 deepseek-flash 实例默认关闭思考。原 B 整阶段仍未完成，T017 不勾选。报告后暂停，等待用户验收。**

## 最终改动与原因

唯一产品改动是 [core/reference_model.py](../../backend/app/core/reference_model.py)：在 `openai_compatible` 且模型标识精确等于 `deepseek-flash` 时，ChatOpenAI 构造参数增加 `extra_body={"thinking":{"type":"disabled"}}`，同一实例的入口、研究、摘要及聚合继承。其他模型标识、Ollama、独立 legacy 路径不注入该参数；模型/端点/凭据/温度/种子及 `.env` 文件不变。代码对新建实例生效，本轮没有重启后端。

先前真实返回明确为 `Thinking mode does not support this tool_choice`；[官方说明](https://api-docs.deepseek.com/guides/thinking_mode/)给出思考开关，并要求携带工具时回传历史 reasoning_content。本机 ChatOpenAI 明确不保存第三方该字段，因此采用已经真实验证的整链路非思考方案。没有修改参考提示/schema、工具或图、HTTP/SSE 字段，没有新增业务重试、SDK 重试、provider 切换、依赖或私有推理记录。修复不是对其他 DeepSeek 别名的兼容承诺。

回归位于 [test_reference016_model.py](../../backend/tests/unit/test_reference016_model.py)：通过实际产品 factory、LangChain 和 OpenAI SDK、在假 HTTP 接缝重现相同 400，再验证结构化入口、工具请求/结果往返及普通生成都继承参数；检查其他模型及 Ollama 未被误改、400 仍直接传播且不重试。假 HTTP 结果仅证明工程协议。

## 实际验证与命令

命令从 `C:\Users\ifhgz\Desktop\agentic-rag` 执行；隔离 runner 的 pytest 子进程工作目录为 `backend`。既有环境，无安装或服务启动。

| 实际命令或完整 argv 证据 | 退出码 | 实际结果 |
|---|---:|---|
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0 | 定位 016，保留既有模板和原任务编号 |
| `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0 | 加载任务模板，追加同一 R 阶段 T019–T023 |
| `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0 | 当前功能完整 |
| `D:\newsoft\python.exe output/reference016/phase-b/freeze_fix.py` | 0 | 保存原代码/文档/Git及 308 项保护指纹 |
| `D:\newsoft\python.exe output/reference016/phase-a/run.py r-fix-red-20261027-01 tests/unit/test_reference016_model.py` | 1 | 修复前 1 failed / 3 passed；同类 OpenAIInvalidRequestError / HTTP 400 红测 |
| `D:\newsoft\python.exe output/reference016/phase-a/run.py r-fix-related-20261027-01 tests/unit/test_reference016_model.py tests/unit/test_reference016_graph.py tests/unit/test_reference016_parity.py tests/unit/test_rag_architecture.py tests/integration/test_reference016_session.py tests/contract/test_reference016_stream.py tests/contract/test_reference016_observation.py tests/contract/test_reference016_diagnostics.py tests/security/test_reference016_privacy.py` | 0 | 修复后 51 passed，21.06 秒；模型、参考图/节点对照、会话、流式、观察、诊断及隐私定向检查 |
| `D:\newsoft\python.exe output/reference016/phase-b/diagnose_real.py r-fix-20261027-b01-01 --graph` | 0 | 当前真实模型和产品工厂完整运行 B01 一次，无 `--thinking-disabled` 或临时 override |
| `D:\newsoft\python.exe output/reference016/phase-b/audit_fix.py` 首轮 | 1 | 审计器的 Windows 路径分隔符比较不一致；原 audit.json 保留，未发现额外产品变化 |
| 同一审计命令，修正审计器路径规范化后 | 0 | 仅计划内 factory 改动，其余原保护文件保持；真实复验期间 314 项无差异 |

工程完整 argv/退出码见 [red JSON](../../output/reference016/phase-a/r-fix-red-20261027-01.json)、[related JSON](../../output/reference016/phase-a/r-fix-related-20261027-01.json)，对应同名 `.log` 为完整输出；两个 guard 的 blocked_attempts 均为空，没有实际网络/正式数据拦截尝试。真实模型仅上表的一次复验，共 4 次模型调用，没有 fake/Judge 或自动重试。

本轮未跑完整后端、前端或构建：产品变化只在一个模型工厂，相关工程与真实复验均通过，未发现需要扩大的失败；A 的 720 passed/两项既有失败为历史结果，不能写成本轮重新通过。原两项 legacy prompt 措辞失败保持。

## 真实首题结果

身份：原 `openai_compatible/deepseek-flash`、temperature=0、seed=42，端点只保存哈希，云端别名不证明权重修订固定。manifest 的 diagnostic_override 为 `{}`；实际模型由修复后的产品工厂创建，没有模型替身或采集器附加参数。

问题：ZX-731 的巡检周期是多久？

最终聚合原文：

> ZX-731 的巡检周期是 72 小时。同一份规程还记载：ZX-731 的温度记录保存 45 天，归档存储上限为 8 GB。
>
> Sources:
> - B016-ZX731.md

Codex 核对：入口清楚且保留原题；真实 search_child_chunks 执行一次，完成单分支与统一聚合；72 小时正确，额外的 45 天/8 GB 也在该合成资料中。来源来自本次实际检索元数据，页码为 null；完成状态 completed，无 error、无 pending。原始结果和独立审阅分别保存，没有把字符串命中单独当作质量验收。

- request_id：`29fdc3e5-6942-4a76-94e2-e9a4b876d8a6`。
- 模型 4 次：rewrite_query 1、orchestrator 2、aggregate_answers 1；工具 1 次，cloud_calls=4，model_call_limit=null。
- provider 报告输入 2925 / 输出 218 / 总计 3143 Token；usage_source=provider。
- 产品 usage 4346 ms、逐题采集 4350 ms、模型累计 4227 ms；含初始化的诊断进程计时 8048 ms。分别报告，不混用口径。

证据：[manifest](../../output/reference016/phase-b/r-fix-20261027-b01-01/manifest.json)、[原始首答](../../output/reference016/phase-b/r-fix-20261027-b01-01/B01.raw.json)、[逐事件](../../output/reference016/phase-b/r-fix-20261027-b01-01/B01.events.jsonl)、[review](../../output/reference016/phase-b/r-fix-20261027-b01-01/B01.review.json)。这是修复后的独立复验，不改判原 B01 首次失败；B02–B05 仍未测。

## 保护、交付与限制

[规范化审计](../../output/reference016/phase-b/fix-20261027-01/audit-verified.json)显示：原 308 项中仅 factory 一项获准变化，其余 307 项不变，包括 `.env`、正式数据/索引、旧产品文件及 A 原证据；真实复验期间的 314 项指纹全部保持。原 A/B/诊断报告与冻结快照一致。产品 AST 定义只改变 create_reference_model；[精确源差异](../../output/reference016/phase-b/fix-20261027-01/source-verified.patch)包含工厂和新增回归，工作区其他修改保留。

文档按 Spec Kit 补充 spec/plan/research/data-model、model-transport 契约、quickstart/tasks，维护 README、CURRENT_STATUS 与功能失败清单。`.specify/extensions.yml` 不存在，未有前后 hooks。requirements 清单 16 项设计标记已勾、3 项旧 A 工程标记未勾；保持 reviewer 标记只读，依据 A 完成证据与用户当前继续授权执行 R，不将旧标记当成重新执行 A 的要求。

临时知识库仍为真实 DocumentStore/IndexStore/Qdrant/Retriever、deterministic Dense/local BM25；无正式 PDF 内容、PDF 解析、真实 ONNX 语义检索、HTTP/浏览器或认证实测。没有服务启动/重启、正式数据重建、提交或推送。关于“默认关闭”的结论仅覆盖正常参考图、精确 deepseek-flash 标识和新建实例。

T019–T023 完成本轮工程交付，不代表用户验收。T017 因剩余四场景未执行保持部分完成；原 T018 失败报告、旧真实质量失败保留。下一范围为按用户明确指示开展独立批次的剩余 B 澄清、续答、压缩及多问聚合验收。

**报告后暂停，等待用户验收。**
