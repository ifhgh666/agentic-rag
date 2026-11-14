# 007阶段B：提示函数接入与工程交付

日期：2026-10-13。授权：用户“执行b阶段”。范围为当前007的T008–T014；T007已在A结构化补充完成，本轮保留。采用项目speckit-implement流程，前后hooks因extensions.yml不存在而跳过，16/16只读内容门禁通过。功能指针保持007，Git分支保持codex/model-driven-agent-loop；不提交或推送。

**B工程交付完成，等待用户验收。** [prompt.py](../../backend/app/rag/prompt.py)的11个纯函数全部有实际调用位置；[改写函数与schema全文](prompt-review.md)可直接检查。改写入口保持A补充的独立schema绑定，本轮其余提示等价接入，不改业务规则或输出契约。

## 完成文件与实际行为

| 文件 | 本轮改动 |
|---|---|
| conversation_summary.py | 调用get_conversation_summary_prompt(memory.summary_max_chars)，JSON摘要、待办排除、保真与预算保持 |
| agent_loop.py | 调用orchestrator(protocol)、context_compression及loop_repair getter，移除重复LOOP_PROMPT及附文；native/structured工具协议、keep/gaps和一次候选修正保持 |
| generator.py | 调用基础答案、aggregation、answer_repair及aggregation_instruction getter，移除重复SYSTEM_PROMPT；原题/分支payload、引用和已有一次修正保持 |
| model_compression.py / query_planner.py | 分别调用旧证据选择与检索词getter；兼容路径保留，不恢复旧图决策 |
| tests/unit/test_prompt_consumers.py | 新增12项实际消费点检查，通过变更getter返回值确认消息使用该结果，并检查参数/协议/调用次数/原题和待办边界 |
| 当前007设计/审阅/契约、README与CURRENT_STATUS | 同步完成事实、调用位置、验证命令和停止点；旧报告和失败不覆盖 |

prompt.py、model_schema.py、model_provider.py、query_analysis.py本轮源码保持。全部函数源码与签名未改；非入口10函数共15种参数场景对照本轮基线逐字等价。提示版本rewrite-prompt-v3、query-rewrite-v1协议、入口json_schema模式保持。新旧提示/结构缓存隔离检查在本轮完整回归中实际运行，工程位置与指纹见delivery.json。

## 实际函数映射

| 函数 | 参数 | 已接入消费者 |
|---|---|---|
| [get_rewrite_query_prompt](../../backend/app/rag/prompt.py)（定义第10行） | 无 | query_analysis.py 第133行 |
| [get_conversation_summary_prompt](../../backend/app/rag/prompt.py)（定义第38行） | max_chars | conversation_summary.py 第36行 |
| [get_orchestrator_prompt](../../backend/app/rag/prompt.py)（定义第48行） | protocol | agent_loop.py 第316行 |
| [get_context_compression_prompt](../../backend/app/rag/prompt.py)（定义第73行） | 无 | agent_loop.py 第262行 |
| [get_aggregation_prompt](../../backend/app/rag/prompt.py)（定义第82行） | 无 | generator.py 第68行 |
| [get_answer_generation_prompt](../../backend/app/rag/prompt.py)（定义第98行） | 无 | generator.py 第41行 |
| [get_evidence_selection_prompt](../../backend/app/rag/prompt.py)（定义第103行） | 无 | model_compression.py 第72行 |
| [get_retrieval_rewrite_prompt](../../backend/app/rag/prompt.py)（定义第114行） | 无 | query_planner.py 第81行 |
| [get_answer_repair_prompt](../../backend/app/rag/prompt.py)（定义第122行） | feedback | generator.py 第90行 |
| [get_loop_repair_prompt](../../backend/app/rag/prompt.py)（定义第127行） | feedback | agent_loop.py 第366行 |
| [get_aggregation_instruction](../../backend/app/rag/prompt.py)（定义第132行） | 无 | generator.py 第122行 |

动态原题/历史/summary/pending/证据在原调用点构建，工具schema仍由工具注册生成。两种压缩保持各自keep/gaps与excerpts/gaps格式。其他节点结构化模式未扩大；仅入口schema分工延续用户授权补充。

## 实际命令与退出状态

所有辅助脚本工作目录为根目录；pytest子进程工作目录backend，使用新独立output目录保存数据和cache。没有真实模型调用。

| 命令 | 退出状态与实际结果 |
|---|---|
| .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks | 0，定位007并读取设计；requirements.md为16已选/0未选 |
| D:/newsoft/python.exe -B output/prepare_prompt007_stage_b.py | 0，保存3466项已有文件指纹、17项正式数据/备份指纹、git status和完整diff；既有修改保留 |
| D:/newsoft/python.exe -B output/run_prompt007_stage_b.py bindings-before -B -m pytest -q tests/unit/test_prompt_consumers.py --basetemp=../output/prompt007/implementation-20261013-b/pytest-before -o cache_dir=../output/prompt007/implementation-20261013-b/cache-before | 1，实现前12项预期失败，2.86秒，外层14.284秒；消息仍用旧内联字符串，getter未调用，原记录保留 |
| D:/newsoft/python.exe -B output/run_prompt007_stage_b.py bindings-after -B -m pytest -q tests/unit/test_prompt_consumers.py --basetemp=../output/prompt007/implementation-20261013-b/pytest-after -o cache_dir=../output/prompt007/implementation-20261013-b/cache-after | 0，12通过，1.61秒，外层10.913秒 |
| D:/newsoft/python.exe -I -B output/check_prompt007_stage_b.py | 0，11实际绑定、15项原提示等价检查通过，模块无导入/模型/文件副作用，prompt.py字节保持 |
| D:/newsoft/python.exe -B output/run_prompt007_stage_b.py backend -B -m pytest -q tests/unit tests/contract tests/integration tests/security --basetemp=../output/prompt007/implementation-20261013-b/pytest-backend -o cache_dir=../output/prompt007/implementation-20261013-b/cache-backend | 0，566通过，141.33秒，外层151.846秒 |
| D:/newsoft/python.exe -B output/finalize_prompt007_stage_b.py | 0，根据实际检查产物写交付指纹、更新导航与报告草稿 |
| D:/newsoft/python.exe -I -B output/audit_prompt007_stage_b.py | 0，保护指纹/UTF-8/链接/任务核对及git diff --check通过，实际结果见artifact-audit.json |

原始证据：[基线](../../output/prompt007/implementation-20261013-b/baseline.json)、[实现前记录](../../output/prompt007/implementation-20261013-b/bindings-before.log)、[接入检查](../../output/prompt007/implementation-20261013-b/bindings-after.log)、[静态等价与绑定](../../output/prompt007/implementation-20261013-b/module-validation.json)、[完整回归](../../output/prompt007/implementation-20261013-b/backend.log)、[交付指纹](../../output/prompt007/implementation-20261013-b/delivery.json)、[最终核对](../../output/prompt007/implementation-20261013-b/artifact-audit.json)。每个pytest命令完整参数/退出码/外层耗时另存同名JSON。

## 工程与真实结果、失败和限制

12项消费点检查使用scripted输出，完整后端检查包含假Ollama传输、mock兼容客户端、fake/scripted provider、确定性嵌入和独立临时索引；验证入口动作/缓存/schema、摘要、工具配对、压缩、汇总、预算、超时/迟到隔离、API/SSE及日志隐私。工程通过不代表真实语义质量通过。

真实产品模型、真实检索、云端、Judge调用均0，无新的真实请求ID、Token用量或问答耗时。未下载/切换模型、改.env、写正式知识库/索引、修改采集器、启动/重启服务或构建前端；没有确认正在运行的旧进程是否加载新代码。所有17项正式数据和旧证据保护指纹核对保持；CURRENT_FAILURES未修改。新增普通文本集中来源，不新增数字/空格语义拦截。

实现后本轮检查未发生失败。实现前12项预期失败保留，不改成通过。006新版E仍10通过/7失败，原代词补全与F失败、005两个真实失败仍保留；本轮不勾选006 T031/T034或005 T018，不恢复正式评测。

## 阶段与停止点

T008–T014本轮完成，原A和补充已完成项保持，20项工程任务全部完成。原C仍取消，取消不计通过。B是007计划最终工程交付，用户可以检查实际函数、schema、映射和证据；没有自动下一实施阶段。若用户以后要求真实复测或其他工作，另按其明确范围处理。**报告后暂停，等待用户验收。**
