# Quickstart: 007最终函数检查与工程验证

2026-10-20：检查唯一实现 [prompts.py](../../backend/app/rag/prompts.py)、[QueryAnalysis](../../backend/app/rag/schemas.py) 和 [Agent图](../../backend/app/rag/graph.py)，全文与消费映射见[审阅文档](prompt-review.md)。所有RAG生产实现均位于`app/rag`；真实质量结论不因目录迁移改变。A3验证结果和限制见[单包收敛报告](phase-single-rag-package-20261018-report.md)：117项定向检查通过，完整后端588通过/3失败，两项历史提示措辞断言保留，一项全量运行时截止时间失败在单独复跑时通过。

## 实际调用分工

改写入口的业务规则来自get_rewrite_query_prompt，输出schema由QueryAnalysis独立维护并直接绑定json_schema。当前固定提示函数用于摘要、Loop、修正、基础答案、grounded、汇总和旧检索改写；证据侧只用`context_compression.py`计算动态 Token 阈值，不调用模型、不生成证据摘要或摘录。摘要传原summary_max_chars，Loop传实际native/structured协议，修正传原反馈。会话历史摘要仍单独保留。

## 已执行的隔离验证

根目录执行 `D:/newsoft/python.exe -I -B output/check_prompt007_stage_b.py`：11实际绑定及15逐字等价场景通过，无模型调用。

backend执行 `D:/newsoft/python.exe -B -m pytest -q tests/unit/test_prompt_consumers.py --basetemp=../output/prompt007/implementation-20261013-b/pytest-after -o cache_dir=../output/prompt007/implementation-20261013-b/cache-after`：12项通过。

backend执行 `D:/newsoft/python.exe -B -m pytest -q tests/unit tests/contract tests/integration tests/security --basetemp=../output/prompt007/implementation-20261013-b/pytest-backend -o cache_dir=../output/prompt007/implementation-20261013-b/cache-backend`：566项通过，包含入口schema/缓存、动作、Loop、汇总、预算、期限、API及隐私。

这些是已经执行的命令，原日志保留；以后验证使用新的basetemp和cache_dir，不能复用本轮目录。测试使用scripted/fake、假传输、确定性嵌入和临时索引，不能据此宣称真实模型7项E失败已修复。

## 交付与停止点

[阶段B报告](phase-b-report.md)及[交付指纹](../../output/prompt007/implementation-20261013-b/delivery.json)记录实际命令、退出码和调用映射。没有启动/重启服务、改变模型/.env或正式数据；在运行的旧进程是否加载新代码未验证。前端未改，不运行前端构建。报告后暂停，等待用户验收，计划结束；不恢复C、006 F、005或30题。

## 用户授权补充M：同款模型

本节另于2026-10-13授权，原B的零真实模型调用记录保持。目标 `OLLAMA_MODEL=granite4.1:8b`，使用现有Ollama；首次安装可用 `ollama pull granite4.1:8b`，本机CLI不在PATH时使用Ollama流式pull API。

仅修改已有.env的模型行，温度0、种子42、预算和窗口保持。根目录可用 `D:/newsoft/python.exe -B output/model_alignment_007.py pull` 记录本轮下载；该工具写独立证据文件，已运行后不要重复使用同一输出目录。

核对安装清单和新进程Settings，使用实际项目提供方进行独立schema与原生工具的最小合成探测；不运行正式题集。后端未启动时下一次正常启动加载新模型，配置探测不等于平台问答验收。实际命令、首次结果和停止点另见补充M报告。

本轮实际交付见[模型补充报告](phase-model-alignment-report.md)：安装与配置生效通过，88项工程检查通过；结构化首测失败、原生工具首测通过。原始首次结果已保存，不能复用同一输出目录重测；后续真实补测或prompt/schema修复需另行明确范围。

## 补充T：用户已授权入口测试

沿用已补齐17题，当前prompt/schema/Granite8B另起首次批次。根目录以 `D:/newsoft/python.exe -B output/test_prompt007_entrance.py engineering` 执行采集器隔离检查，再以 `D:/newsoft/python.exe -B output/test_prompt007_entrance.py capture` 调用现有capture_run；独立输出 `output/prompt007/entrance-20261013/run`，记录后不要复用该目录。

有效结构经Codex逐题审阅文件确认后继续，结构失败直接记failed并按已批准继续规则执行下一题；没有用户实时补充、模型重试或Judge。入口调用无需启动FastAPI/Qdrant。真实成绩与旧题集、M探测和工程检查分开；报告后暂停，端到端另行授权。

实际结果见[入口测试报告](phase-entrance-20261013-report.md)：28项隔离检查通过，17题真实首答全测为0通过/17失败。首答均触发现有字段联动校验，另有RW13–RW15业务问题；原始文件不复用、失败不改判，未开展端到端。

## 2026-10-13 补充R：字段状态生成约束修复

根目录运行 `D:/newsoft/python.exe -B output/fix_query_schema_007.py targeted` 和 `... regression`，记录独立output/prompt007/schema-fix-20261013日志。先用新schema检查清楚/待澄清、非空占位符/矛盾状态；再使用该helper的probe命令最多提交两次首次合成问题。每个命令输出专属文件，已运行的阶段不要复用。旧17题不重判，不开展端到端，见修复报告，报告后暂停，等待用户验收。

R交付：相关工程133项/后端完整585项通过，真实合成结构2/2有效、预期状态1/2通过（无历史代词误判保留）；旧17题不改判，未开展题集或端到端。见[修复报告](phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充T2：字段联动修复后的真实入口复测

根目录按序运行 `D:/newsoft/python.exe -B output/retest_prompt007_entrance_20261014.py prepare`、`... design`、`... capture`。status只读查看首答与当前待审题；review-submissions/RWxx.json在首答保存后填写status/reviewer/rationale，再继续下一题。此为Codex审阅，不冒充用户验收。已采题不重试、旧目录不复用；标准答案不发送模型。完成后报告并暂停。

T2实际交付：14通过、3失败、0待定、0未运行，17/17条首答结构有效，零重试；采集/审阅工作完成不表示质量全通过。模型与产品配置/代码、旧首答/报告及正式数据保持。见[入口复测报告](phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充P：改写业务规则的顺序与通用示例

根目录按序运行output/repair_prompt007_business_20261014.py的prepare、design、engineering、capture diagnostic、capture regression子命令（D:/newsoft/python.exe -B）。每批review-submissions在首答保存后由Codex提交status/reviewer/rationale；文件独占，不复用旧目录。工程/preflight为scripted，无真实模型；两批每题首答一次，失败继续，完成后报告暂停。

P候选修改/验证/记录工作已交付，质量未通过：145项工程通过；真实诊断6题4通过/2失败/0待定/0未运行、原17题回归12通过/5失败/0待定/0未运行，各批独立计分。v4新增误澄清/历史混入退步，已仅撤回本轮候选，当前prompt字节恢复测试前v3；候选全文/原始失败保存，schema修复保持。T041勾选表示候选编写与试验完成，不表示最终采纳。旧失败不改判，见[候选报告](phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

## 2026-10-14 补充L：轻量英文入口prompt候选

根目录顺序执行 `D:/newsoft/python.exe -B output/try_light_prompt_20261014.py prepare`、`design`、`engineering`、`capture`。capture在每题raw保存后等待`review-submissions/<ID>.json`，由Codex提交status/reviewer/rationale；完成后只生成报告，暂不跑17题。
