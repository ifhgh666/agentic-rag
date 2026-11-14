# 验收快速指南

**状态（2026-10-07 首批结束）**：阶段 A、B 已实施；15 题已由用户批准为 `gold-1.0`。D 首批真实采集/评分已执行，并达到 80 次 Judge 上限，22 项评分、只有 Q7 五项齐全；完整评分和人工签收未完成，详见[本批报告](formal-ragas-report.md)。历史工程交接见[收尾报告](phase-e-report.md)。以下命令是复现说明，重新运行需追加确认，不代表正式总验收通过。

## 前提

- 使用当前 Windows 工作区 `C:\Users\ifhgz\Desktop\agentic-rag`，Python 与前端依赖保持现有配置；本地 Ollama 已按项目设置可用。
- 正式知识库保持当前状态；评估前记录文档 ID、PDF SHA-256 和索引版本。测试题集只基于该版本，版本不一致应停止正式评分。
- 工作台登录沿用现有用户自行登录流程；不要把密码、Token、密钥写入题集或报告。
- 下载第二 Judge 模型、启用云端服务、导入/重建 PDF 均须另行确认，不属于本指南的默认步骤。

## 阶段 A：冻结现状与题集规范

在 `backend` 目录运行现有基线：

```powershell
python -m pytest -q
python -m scripts.smoke_v3_5_regression
```

记录运行时间、请求数、模型调用、Token、Q1～Q5 答案和引文。人工复现：一条代词含糊题、一条待澄清时切换新题、一条 Q3 操作流程题；对照 [V3 后续质量计划](../003-v3-ollama-rag-quality/v3-post-acceptance-plan.md) 保存证据。预期此阶段能确认当前缺陷，而不是“已通过修复”。建立至少 5 个标准答案草案，注明来源页和人工待核状态。

## 阶段 B：入口与澄清验收（已实施）

1. 用工作台提问清楚独立题、同线程指代追问、明确双问题。预期每条消息有一次可追踪的入口分析；清楚题不无故澄清，拆分题两部分都回答。
2. 对“过流后怎么恢复？”这类缺型号题，检查系统保存待澄清状态并只问具体问题；补充“PX-200”后再检索。
3. 在同一待澄清线程改问“运行记录保留多久？”、选择取消、输入含糊回复，分别验证旧题不会拼接、新题能正常处理、取消后旧待办消失、含糊时出现明确选项。
4. 模拟模型不可用或结构化输出无效，预期有明确失败/降级提示，日志可按 `request_id` 追踪，待办不丢失。核对简单题调用仍在 2 次预算内，额外摘要不能暗中突破上限。

后端自动化仍以 `python -m pytest -q` 运行；新增测试位置与事件格式以[接口契约](contracts/chat-and-evaluation.md)为准。

入口与澄清专项（在 `backend` 目录）：

```powershell
python -m pytest -q tests/unit/test_v4_query_analysis.py tests/unit/test_v4_thread_state.py tests/unit/test_v4_conversation_summary.py tests/integration/test_v4_clarification_flow.py
python -m scripts.smoke_v4_query_analysis
python -m scripts.smoke_v4_clarification
```

两个冒烟脚本只使用合成会话并调用已配置的本机 Ollama，不打开正式索引、不修改真实会话；输出逐例结果、Token 和耗时，不代表完整 PDF 问答验收。取消不调用模型，忙碌请求不覆盖状态。摘要只用剩余预算；预算满或输出无效时保留原文，历史及澄清输入过长会明确提示新会话。服务重启会清空进程内会话。

前端在 `frontend` 目录运行：

```powershell
npm test
npm run build
```

## 阶段 C：标准答案集验收（已批准）

1. 从当前 PDF 建立 Q1～Q5 及至少 10 个不同类别场景。每题按[数据模型](data-model.md)核对来源文件、页码、逐字引文、必答点、禁止误答和预期拒答。
2. 逐题复核全部 15 题的来源定位。Q3 必须依次覆盖断开负载、等待完全放电、检查负载端是否短路、确认负载正常、按确认键清除告警和重新执行上电流程；“确认负载正常”是清除告警的前提。
3. 修改或替换测试 PDF 的副本指纹进行失配演练，预期题集不再被标为可正式评分；**不得**在正式知识库上做此演练。
4. 只有 `reviewed` 且文档指纹匹配的题进入正式统计；报告列出未审核或失配题目，不把它们暗中排除后仍宣称“全量通过”。

在 `backend` 目录执行只读检查，不启动模型、不读取向量索引：

```powershell
python -m scripts.validate_v4_gold_dataset --json
python -m pytest -q tests/unit/test_v4_gold_dataset.py
python -m scripts.validate_v4_gold_dataset --json --require-reviewed
```

当前三条均应通过：`gold-1.0` 共 15 题，26/26 条引文匹配，全部 `reviewed`。审核者、带时区的登记时间和 `review_kind=human` 来自用户明确确认，详见[审核与授权记录](gold-review-approval.md)；自动检查不替代人工批准。仅 10 道普通可回答题进入五项事实问答指标，4 道交互题和 1 道无答案题另行验收。题集获批不等于本次系统回答已经人工复核通过。

## 阶段 D：离线 RAGAS 与在线展示验收（首批运行，完整复核未完成）

1. 用一题通过 RAGAS 与本地 Judge 兼容性冒烟，记录所用模型、包版本、单题调用/Token/耗时。若需要下载新模型，先停下征得同意。
2. 在固定题集和知识库版本上采集**真实系统答案、检索候选排序及实际送入生成器的上下文**。执行离线五项指标，保存逐题原始结果、失败原因和人工复核，不只保存均值。
3. 对无证据、待澄清等不适用题目检查 `not_applicable`；故意缺失 Q3 安全前置步骤的答案必须被人工必答点检查拦下，不可仅凭 RAGAS 高分放行。
4. 在线工作台检查证据、引文、数值和未验证状态；不再看到固定 84/100 或“总体可信度”。普通在线请求没有新增 Judge 调用。

以下命令在 `backend` 目录执行。评估包与生产 LangGraph/模型提供商需要不同 LangChain 版本，必须使用专用虚拟环境；不要激活它启动后端，也不要向生产 `requirements.txt` 追加这份清单。

```powershell
python -m venv tmp\v4-eval-clean-env
tmp\v4-eval-clean-env\Scripts\python.exe -m pip install -r requirements-eval.txt
tmp\v4-eval-clean-env\Scripts\python.exe -m pip check
tmp\v4-eval-clean-env\Scripts\python.exe -m scripts.evaluate_v4_ragas --smoke --judge-model qwen3:4b-instruct --timeout 60 --max-calls 16
```

`--smoke` 仅使用内置合成来源，不读取正式 PDF、题集或索引；实际生成一条回答再评估，使用现有本地模型，不自动下载。它不执行应用的入口分析和检索链路，不替代正式问答验收。回答和 Judge 同模型，结果标为探索性；五项指标可能调用多次模型，本次一题 Judge 共 8 次。完整原始输出保存于 `backend/tmp/v4-evaluations/`，返回码非零表示失败或至少一项指标失败，而不是有效 0 分。

正式模式的关卡演练无需安装 RAGAS：

```powershell
python -m scripts.evaluate_v4_ragas
```

当前不带输入的命令预期失败、报告 `actual_capture_required`：题集已获批，但仍须提供完整真实采集快照；不调用 Judge。若未来题集改回草案或指纹失配，仍会被审核/版本关卡拒绝。

T020 已完成。新增批量采集入口 `python -m scripts.capture_v4_formal --capture-local`，使用当前业务 Graph 与正式索引只读隔离快照，按[快照契约](contracts/chat-and-evaluation.md)保存实际答案、双层上下文和逐轮交互；不是 UI 点击验收。不能拿标准答案或来源引文代替真实输出。正式评估只读该快照，须显式提供版本、模型和批准预算。默认 16 是整批上限，不是每题上限；本批批准 80 次，失败后不自动追加。

本批使用已有干净评估环境，命令如下（再次执行需追加运行确认）：

```powershell
tmp\v4-eval-clean-env\Scripts\python.exe -m scripts.evaluate_v4_ragas --dataset ..\specs\004-query-clarification-ragas\gold-cases-v1.json --inputs tmp\v4-captures\graph-860dcae4-1818-4bd4-a002-03f9fc3b6708.json --index-manifest data\index\manifest.json --judge-model qwen3:4b-instruct --timeout 60 --max-calls 80 --progress
```

首批采集的 15 题已通过输入/版本/上下文验证，但退出时临时索引关闭出错，顶层原始状态仍保留 `capture_failed`。错误发生在所有答案保存及验证之后；已修复关闭客户端的方法，没有重跑回答。详见本批报告，不能隐去这次工具失败。

结果中检索指标保持工具原始排序，支撑度使用实际生成上下文。数值高低不是设备操作安全结论；RAGAS 未提供理由的项保持 `null`，人工必答点、顺序、无答案与交互复核单独记录。正式验收须完成 T026，不能凭合成冒烟标为通过。

## 阶段 E：工程交接完成，正式库总验收仍待完成

在同一正式索引上重跑 Q1～Q5 与扩展题；Q3 至少连续 3 次完整覆盖安全前置步骤并引用详细原文。与 V3-5 的 9,377 Token/约 225 秒对比逐题成本。所有未完成的旧 V3-6～V3-8 Q3 修复须明确列为依赖或遗留问题，不得用评估流程替代修复。

收尾新增的离线检查，在 `backend` 目录运行：

```powershell
python -m pytest -q tests/integration/test_v4_formal_regression.py
```

该文件共 23 项：15 个候选场景使用脚本化分析器与临时空索引检查 SSE/状态，另审计已保存的五题真实 UI 输出、Q3 三次不同请求的同版本证据及审核边界。它不重新调用模型，也不证明扩展题的真实回答质量。

2026-10-07 收尾实测后端 318 项、前端 20 项通过，构建成功。V3-8 既有正式 UI 五题共 10 次本地调用、12,216 实测 Token、248.995 秒；这是复用记录，不是本次新增用量。Q2 旧记录未包含候选必答点“立即断开主回路”，SC-004 仍未按完整候选口径通过；不得用旧五题通过或引文已核验替代新版完整性验收。

当前 T020 已完成，15 题实际采集已保存，本批评分和安全/交互复核见[本批运行记录](formal-ragas-report.md)。T026/T027/T028 尚未完整完成；不能因题集获批或部分指标有分数而标为全量验收通过。首批结束或预算耗尽即汇报暂停，后续修复或追加评分需用户确认。

每一阶段产出 `phase-*-report.md` 后暂停并向用户汇报；未获下一阶段确认不继续执行。
