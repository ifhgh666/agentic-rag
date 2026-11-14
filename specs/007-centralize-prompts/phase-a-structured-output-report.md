# 007阶段A补充：独立schema与入口结构化生成

日期：2026-10-13。授权：用户确认GitHub的独立schema/业务prompt/直接绑定做法后要求“那你先补好这个”。本轮只执行入口补充T019–T024，覆盖原T007；不执行其余提示消费点迁移、真实题集或已取消C。依据项目Spec Kit specify/plan/tasks/implement技能复用007并补充US4、FR-012–FR-014；setup-plan/setup-tasks/check-prerequisites均退出0，功能指针和真实Git分支保持，extensions.yml不存在，前后hook均跳过。16/16规格内容门禁重新检查通过。

**补充实现与工程验证完成，待用户验收。** [实际schema](../../backend/app/rag/model_schema.py)独立维护is_clear、questions、clarification_needed；[实际改写函数](../../backend/app/rag/prompt.py)只保留业务规则，完整两份源码见[审阅文档](prompt-review.md)。

## 完成文件和运行行为

- model_schema.py：补字段description；严格bool/list[str]/非null字符串、必填、禁止额外字段、最多三问和原有非空/长度/重复/状态联动validators保持，不新增数字/空格语义拦截。
- prompt.py：删除改写函数的JSON格式段，提示版本rewrite-prompt-v3；其余10函数逐段源码与本轮基线相同。
- query_analysis.py：调用集中提示，传response_schema=QueryAnalysis，按structured_output直接读三个字段；输入窗口保守计入schema，缓存按提示版本/json_schema模式/schema哈希隔离。动作、原题、历史、待办和公开契约保持。
- model_provider.py：Ollama直接with_structured_output(schema, method="json_schema", include_raw=True)，保持raw/usage；显式兼容模式传response_format/json_schema/strict。complete_model保持同一次总等待并返回严格结构化对象；字段联动失败保留raw，入口走原invalid_model_output，拒绝绑定走原model_unavailable，超时走原timeout，无重试/降级/提供方切换。
- 新增test_query_analysis_structured_output.py；必要现有测试替身接受schema参数，并把两处仅用于入口的旧固定替身换为ScriptedQueryProvider。API/SSE契约断言保持，旧提示文字断言适配新集中业务规则；采集器和历史回放脚本不改。
- 当前spec/plan/tasks/research/data-model/契约/quickstart、README和CURRENT_STATUS同步本轮事实；原A、规划、006/005报告、题集与首答均不覆盖。

## 实际命令、退出状态与证据

工作目录除pytest子进程外均为仓库根目录；pytest子进程均在backend。完整命令/路径/退出状态/外层耗时保存在各JSON，不用历史成绩代替本轮结果。

| 命令 | 状态及结果 |
|---|---|
| D:/newsoft/python.exe output/prepare_prompt007_structured.py | 0，保存1108项已有文件、17项正式数据/备份哈希与完整git状态/diff；旧改动不清理 |
| .specify/scripts/powershell/setup-plan.ps1 -Json | 0，复用007既有plan，不覆盖历史报告；返回逻辑功能名不等于切换Git分支 |
| .specify/scripts/powershell/setup-tasks.ps1 -Json | 0，读取模板和现有设计产物后补任务，不创建新feature |
| .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks | 0，定位007；内容门禁16/16 |
| D:/newsoft/python.exe output/run_prompt007_structured.py red -B -m pytest -q tests/unit/test_query_analysis_structured_output.py --basetemp=../output/prompt007/structured-20261013/pytest-red | pytest退出1，10失败/10通过，64.39秒；实现前预期失败。外层80.778秒，输出打印遇GBK编码异常，原log/json保留，随后按windows-chinese-docs修正helper UTF-8；未覆盖首轮结果 |
| D:/newsoft/python.exe output/run_prompt007_structured.py target -B -m pytest -q tests/unit/test_query_analysis_structured_output.py --basetemp=../output/prompt007/structured-20261013/pytest-target -o cache_dir=../output/prompt007/structured-20261013/cache-target | 0，20通过，61.24秒；外层70.664秒 |
| D:/newsoft/python.exe output/run_prompt007_structured.py backend-initial -B -m pytest -q tests/unit tests/contract tests/integration tests/security --basetemp=../output/prompt007/structured-20261013/pytest-backend-initial -o cache_dir=../output/prompt007/structured-20261013/cache-backend-initial | 1，26失败/528通过，145.82秒；外层156.975秒。失败为未接新参数的旧测试替身及一条旧文字断言；记录保留 |
| D:/newsoft/python.exe output/run_prompt007_structured.py backend-final -B -m pytest -q tests/unit tests/contract tests/integration tests/security --basetemp=../output/prompt007/structured-20261013/pytest-backend-final -o cache_dir=../output/prompt007/structured-20261013/cache-backend-final | 0，554通过，156.51秒；外层167.937秒 |
| D:/newsoft/python.exe output/finalize_prompt007_structured.py | 0，同步实际函数/schema、任务及导航，保留原报告 |
| D:/newsoft/python.exe output/audit_prompt007_structured.py | 结果见artifact-audit.json，核对保护指纹、实际源码、任务、UTF-8和链接；仅成功时交付 |

本轮记录：[基线](../../output/prompt007/structured-20261013/baseline.json)、[实现前检查](../../output/prompt007/structured-20261013/red.log)、[20项检查](../../output/prompt007/structured-20261013/target.log)、[首次后端回归](../../output/prompt007/structured-20261013/backend-initial.log)、[最终后端回归](../../output/prompt007/structured-20261013/backend-final.log)、[交付指纹](../../output/prompt007/structured-20261013/delivery.json)、[最终核对](../../output/prompt007/structured-20261013/artifact-audit.json)。未改前端，不运行前端构建。

## 实测范围、失败与限制

20项检查采用真实LangChain结构化包装器与假Ollama传输、mock兼容客户端及scripted首答，验证发送的format/schema、两种状态、严格字段、原始返回/用量、模式拒绝、一次预算、整次等待和缓存。后端回归也是fake/scripted、确定性嵌入与独立测试目录；假的usage数值不是本机真实推理用量。

真实产品模型/检索/云端/Judge请求均0，无真实请求ID或新问答耗时。没有模型下载/切换、.env或正式知识库/索引写入、服务启动/重启、Git提交/推送；不宣称当前运行中的旧进程已自动加载新代码。生成schema不等于保真保障，自定义字段联动validators仍在返回后检查，不自动成为生成语法。006新版E仍10通过/7失败，原RW07与F失败、005两项真实失败及其待办均保持，不宣布修复或验收通过。

## 任务与停止点

T001–T006原A保持完成；本轮T007及T019–T024完成，共20项任务中13完成、7待办。后续仅在用户指示后执行T008–T014，接入摘要/Loop/生成/旧兼容提示并交付B工程报告；已取消C不恢复。本轮报告后暂停，等待用户验收。
