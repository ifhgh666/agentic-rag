# 阶段 A 报告：云兼容端点的结构化输出兼容

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-15。功能：`009-cloud-provider-compat`。分支：`codex/model-driven-agent-loop`（未建新分支）。

授权：用户选择“授权我做 provider 级修复（推荐）”，要求按项目流程新建规格并单独记录。

**本报告交付后暂停，等待用户验收。**

## 1. 结论

云端兼容路径已从“整体不可用”修复为可用：真实入口请求不再以 `model_unavailable` 失败，第一次真实运行得到非空回答与来源。但**稳定性不足**——第二次运行因模型多轮检索用尽请求预算而以 `budget_exceeded` 结束；引用核验报 `issue_found`，数值与完整性仍未评估。因此本功能只能宣告“云端路径可用”，不能宣告“真实问答质量通过”。

## 2. 根因（两个，均已实测复现）

### R1 环境解压绑定不兼容（阻断任何云端调用）

- `brotli 1.0.9` 的 `Decompressor.process()` 不接受 `output_buffer_limit` 关键字参数；`openai 3.19.2` 依赖的 `httpx2 2.13.0` 在解压 brotli 响应时固定传该参数。
- 复现：`process(payload, output_buffer_limit=1024)` → `TypeError: takes no keyword arguments`；不带该参数则成功。
- 后果：任何**压缩返回**都会在解码阶段抛错，被归类为 `model_unavailable`。

### R2 端点不支持严格结构化输出（阻断入口分析）

- `OpenAICompatibleProvider` 对 `response_schema` 固定发送 `response_format={"type":"json_schema",...}`；实测该端点返回 400 `This response_format type is unavailable now`。
- 入口分析的字段要求**未进入提示词**（`query_analysis.py` 的 `schema_text` 只用于缓存键与 token 估算），因此仅去掉 `response_format` 无法得到合法结构。
- 修复前真实入口证据：请求 `[运行标识已移除]`，HTTP 200、6.5 秒、`calls_by_node={"query_analysis":1}`、`cloud_calls=1`、终态 `failed / model_unavailable`。

## 3. 改动文件

| 文件 | 改动 |
|---|---|
| `backend/app/rag/model_provider.py` | ① 云端客户端显式 `Accept-Encoding: identity`，绕开 R1；② `response_schema` 请求先走严格模式，仅当端点以 400 拒绝该 `response_format` 类型时，注入 schema 文本后改用通用 JSON 模式重试**一次**；③ `ModelResult` 新增 `structured_mode` 与 `structured_fallback`；④ 新增 `schema_instruction` / `with_schema_instruction` / `rejects_structured_format` |
| `backend/app/rag/query_analysis.py` | 入口分析的模型轨迹记录 `structured_mode` / `structured_fallback`；失败轨迹记为 `none` / `false`，失败原因仍为 `model_unavailable`，不写成输出非法 |
| `backend/app/rag/agent_loop.py` | 循环内模型轨迹同样记录上述两个字段 |
| `backend/app/rag/pipeline.py` | 公开模型遥测白名单加入 `structured_mode` / `structured_fallback`（仅 `details`，不新增顶层事件字段） |
| `backend/tests/unit/test_model_provider.py` | 新增 7 项断言：禁用压缩编码、严格被拒时回退且仅 2 次请求、schema 注入且不含密钥、严格成功时不回退、非 400 错误不回退、两次均被拒时不误报输出非法、本地 provider 无结构化模式 |

未改动：`backend/.env` 与 `.env.example`、`backend/requirements.txt`（未新增或升级依赖）、前端、索引格式、知识库数据、008 的任何文件。

## 4. 实际命令与结果（工作目录 `backend`，除注明外）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python -m pytest -q tests/unit/test_model_provider.py` | 0 | **16 passed**（原 9 项 + 新增 7 项） |
| `python -m pytest -q tests/unit/test_model_agent_loop.py` | 0 | 13 passed（1.92 秒） |
| `python -m pytest -q tests/unit/test_model_loop_protocol.py tests/unit/test_v3_3_query_analysis.py tests/unit/test_v4_query_analysis.py` | 1 | 24 passed, 1 failed（既有措辞失败，见 §6） |
| `python -m pytest -q tests/unit tests/contract tests/integration tests/security` | 1 | **591 passed, 2 failed in 134 秒**（两处均为既有措辞断言，见 §6） |
| `python tmp/_acceptance_008.py`（第 1 次真实运行） | 0 | 见 §5 运行 1 |
| `python tmp/_acceptance_008.py`（第 2 次真实运行） | 0 | 见 §5 运行 2（业务上失败） |

改前基线：`output/cloud009-baseline/pre-fix-targeted.txt`（45 passed, 1 failed）；改后全量：`output/cloud009-baseline/post-fix-full.txt`。

## 5. 真实运行证据（真实端点、真实索引、真实 HTTP/SSE 入口）

原始采集：`output/light008-phase4-rerun-20261015/chat-run-01.json`、`chat-run-02.json`。问题：`PX-200 的过流保护阈值是多少？`。配置：`openai_compatible` / `deepseek-flash` / 整次上限 300 秒。

### 运行 1（主证据，请求 `[运行标识已移除]`）

- 终态 `completed / model_answered / stop_origin=model`，端到端 **16834 ms**。
- 事件序列完整：2×step → 2×model_call → agent_decision → tool_start/tool_call(`search_child_chunks`) → hybrid_search → model_call → agent_decision → analysis → query_rewritten → retrieval → answer → verification → usage → complete。
- 模型调用 3 次（`query_analysis` 1、`orchestrator` 2），工具 1 次，`cloud_calls=3`，`total_tokens=5072`（provider 实测），`budget_exceeded=false`。
- 回答 240 字符，含阈值 16 A、持续 100 ms、立即断开主回路、需手动恢复、故障代码 OC-16；来源 1 条（`rag-real-acceptance-upload.pdf`，页码未知）。
- 核验卡：`evidence_status=found`、`citation_status=issue_found`、`numeric_status=not_evaluated`、`completeness_status=not_evaluated`。
- 本地轨迹 `backend/data/logs/loop_traces/c9f1e642-….json` 记录 `query_analysis → structured_mode=json_object, structured_fallback=true`，两次 `orchestrator → none/false`，证明回退按契约发生。

### 运行 2（补充运行，仅用于验证遥测字段，请求 `[运行标识已移除]`）

- 终态 **`failed / budget_exceeded / runtime_guard`**，221 字符错误文案；端到端 16573 ms。
- 模型调用 4 次、工具 5 次（含 3 次检索、2 次 Parent 回读）、触发 `context_compression` 与 `budget` 事件；回答 22 字符、来源 0 条。
- 该次 `model_call.details` 已含 `structured_mode=json_object / structured_fallback=true`，验证了 §3 的遥测白名单改动。
- **如实记录：同一问题、同一配置下第二次运行未得到可用答案。** 这属于模型决策与预算交互的行为事实，本报告不将其归因于本次修复，也不据此宣称质量通过。

### 对 008 阶段 4 的影响

008 阶段 4 唯一未通过项是“真实问答在 300 秒内未产出答案与来源”。运行 1 已在真实入口产出答案与来源，该阻塞项**在本次条件下解除**；但 008 的验收结论仍由用户判断，本报告不代替 008 的验收，也不修改 008 的既有报告。

## 6. 失败与限制

1. **既有失败 2 项，非本次引入**：`tests/unit/test_query_rewrite_v1.py::test_stage_c_prompt_explains_shared_dependencies_comparison_and_capacity` 与 `tests/unit/test_v4_query_analysis.py::test_context_prompt_limits_history_and_preserves_unconfirmed_conditions` 均逐字断言 007 改写前的提示词措辞（“共享型号、电压、持续时间”“只使用必要历史”），而当前 `get_rewrite_query_prompt()` 已无这些字句。两者读取的是测试替身收到的系统提示词，不经过本次改动的回退路径。本次未修改这两处断言，留待独立授权处理。
2. **引用核验未通过**：运行 1 的 `citation_status=issue_found`，即答案中引文与来源记录的逐字/页码匹配存在问题（页码未知）。数值条件与步骤完整性仍为未评估，不能宣称答案正确。
3. **稳定性不足**：运行 2 以 `budget_exceeded` 结束，说明同一问题可能因模型多轮检索耗尽预算而失败；SC-002（连续 3 次结构有效，本报告只有 2 次）与 SC-005 未取得完整证据。
4. **回退只验证了真实端点一次路径**：严格模式被拒 → 通用模式的真实回退各环节均观察到，但未在“端点支持严格模式”的真实端点上验证不回退分支（该分支仅有单元测试覆盖）。
5. **环境缺陷未修复**：R1 只是在产品侧规避。若用户日后用其它不走该 provider 的代码路径，或直接调用 `httpx2`，仍会触发同一 `TypeError`。建议的彻底修法（二选一，需另行授权）：卸载 `brotli`，或升级到支持 `output_buffer_limit` 的版本。
6. **未做的检查**：未运行前端测试与构建（本功能不涉及前端）；未运行 30 题正式评测；未改 `docs/` 中的评测协议。

## 7. 环境与过程说明

- 测试必须在非受限沙箱下运行：受限沙箱下 pytest 无法创建/枚举临时目录（`WinError 5`）。已按 `diagnose-windows-sandbox-acl` 技能运行其脚本，判定 `NOT_THIS_CLASS`——工作区文件权限本身正常，故未做权限修改，改为在非受限环境运行测试。
- 曾出现一次目标测试批次墙钟 **10556 秒**的读数，原因是托管后台作业在会话空闲时被挂起；同样的文件单独重跑分别耗时 1.92 秒与 3.94 秒，不是测试卡住。
- 交付时服务状态：后端 `127.0.0.1:8000`（托管后台作业，`index_ready=true`）；前端 `127.0.0.1:5173`（旧会话遗留，仍在运行）；Ollama `127.0.0.1:11434` 在运行。旧会话遗留、占用 8000 端口与 Qdrant 锁的后端实例已停止（其加载的是 21:35 之前的 `ollama` 配置）。
- 知识库仍有 2 份 `ready` 文档，含阶段 4 遗留的 `rag-real-acceptance-upload.pdf`（按用户先前选择“先保留”未清理）。
- 密钥未写入任何报告、日志或命令；真实运行只输出非敏感用量指标。

## 8. 下一阶段范围

1. 用户验收本报告；确认是否将 008 的阶段 4 阻塞项视为已解除。
2. 若继续：就 §6.1 的两处既有失败单独授权修复；就 §6.2 的引用核验问题单独授权诊断。
3. 若继续：决定是否执行 §6.5 的环境彻底修复，以及是否把 009 的真实运行扩展为连续多次以取得 SC-002/SC-005 证据。
4. 未获新授权前不启动 30 题正式评测、不修改评测协议、不改前端。

**报告后暂停，等待用户验收。**
