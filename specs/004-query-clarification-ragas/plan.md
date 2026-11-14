# 实施计划：问题理解、澄清与 RAGAS 标准答案评估

**分支**：`main`｜**设计日期**：2026-09-30｜**规格**：[spec.md](spec.md)  
**输入**：用户要求按 Spec Kit 制定“每条问题先交给本地模型分析、正确处理澄清、制作可复核标准答案集并离线运行 RAGAS”的计划。  
**状态（2026-10-07 首批结束）**：A、B 已实施，C 的 15 题已由用户批准为 `gold-1.0`。D 首批真实采集与离线评估已执行，达到 80 次 Judge 上限，22 项有有效分数；完整评分、实际回答人工签收及 E 总验收未完成。见[本批报告](formal-ragas-report.md)，本批结束后暂停，不追加调用。

**校准切片（2026-10-08）**：用户要求先校准题集。本轮交付 [candidate-2.0](gold-cases-v2.json)、[语义量规](gold-cases-v2-rubrics.json)、[隔离待办夹具](clarification-state-fixtures-v2.json)、[审核稿](gold-cases-v2-review.md)与[报告](dataset-calibration-report.md)，共 23 个场景、11 个知识组；不改业务逻辑、采集器、Judge 或正式库。后续须先审核新版，再单独对齐离线流程门槛、选择运行子集并批准新预算；不自动执行。原批报告和分数保留，Q2 仅凭未复述保护动作不能证明阈值回答错误或裁判漏判，解释以校准报告为准。

## 摘要

把当前由多处正则和字符串拼接承担的问题语义判断，改为每条新消息一次有界的结构化本地模型分析；把待澄清问题、普通历史和摘要纳入统一线程状态，允许补充、换题、取消；从现有 PDF 制作人工逐条核对的标准答案集合，以独立的离线 RAGAS/人工复核评估真实回答与实际证据。在线页面不再展示固定“总体可信度”，只报告可以核验的证据状态。分阶段实施，沿用现有检索与生成链路，不修改正式知识库。

## 技术背景

**语言与版本**：Python 3.12.4；Node.js 22.23.2；前端 TypeScript/React。  
**主要依赖**：现有 FastAPI、Pydantic、LangGraph、Ollama、PyMuPDF、Qdrant/fastembed、React；RAGAS 0.4.3 和兼容的 LangChain/Instructor/OpenAI 版本仅安装于评估虚拟环境，见 `backend/requirements-eval.txt`。禁止把该清单并入生产依赖，或用评估环境启动后端。
**存储**：进程内 `ConversationMemory/ThreadState` 是唯一跨轮状态；主图不另保存跨轮 checkpoint；知识库 PDF、Parent Store 与索引保持不变；题集、评估结果为版本化本地文件。  
**测试**：后端 pytest 单元/契约/集成，前端 Vitest/build；既有 V3-5 冒烟与正式库 Q1–Q5 回归；离线题集、人工核对与 Judge 重跑。  
**目标平台**：当前 Windows 本地工作台；单管理员。  
**项目类型**：FastAPI 后端＋React 前端＋本地离线评估工具。  
**性能目标**：普通在线问答最多一次入口分析＋一次答案生成；摘要/重试等额外调用须单独受预算约束并可审计；记录逐题 Token 和延迟，对比 V3-5 五题合计 9,377 Token、约 225 秒。Judge 不进入在线请求。  
**约束**：默认本地模型与 0 云端调用；当前简单问题 2 次、复杂问题 4 次调用上限；不修改正式 PDF/索引/登录配置；每阶段交付后暂停。  
**规模**：先基于现有单份测试 PDF 建立至少 15 个经过核对的题目（Q1–Q5＋至少 10 个变体/异常场景），真实业务 PDF 另行授权。  
**研究结论**：[research.md](research.md) 已确定关键取舍与替代方案，无阻断性的待澄清产品决策；实际 Judge 模型与包版本属于实施验证关卡。

## 宪章检查

*设计前关卡与设计后复核：依据项目宪章 1.0.0。*

| 原则 | 设计前检查 | 设计后结论 |
|---|---|---|
| 阶段边界交付 | 新功能目录 `004`，不回写已完成的 V3-0～V3-5；各阶段独立验收 | 通过；下文规定每阶段汇报后暂停 |
| RAG 单一职责 | 问题分析、线程状态、生成、在线核验、离线评估各有独立契约 | 通过；参见[数据模型](data-model.md)与[接口契约](contracts/chat-and-evaluation.md) |
| 基于证据回答 | 摘要只辅助理解，不成为 PDF 引文；缺证据要拒答 | 通过；Q3 安全步骤按原文和人工复核检查 |
| 安全一致的数据处理 | 不重建索引、不导出密钥；题集引用 PDF 指纹与页码，版本变化必须重新核对 | 通过；无破坏性数据操作 |
| 可观察可验证 | 保留 request_id、SSE、Token/耗时记录，增加测试与离线重跑 | 通过；验收步骤见[quickstart.md](quickstart.md) |
| Spec Kit 事实来源 | 当前功能有 `spec.md/plan.md/tasks.md` 与设计、阶段报告 | A、B 已实施；C 人工批准完成；D 首批评估结束、完整评分及人审未完成；E 工程交接完成、正式总验收未完成 |

**复杂度跟踪**：本方案没有宪章例外。RAGAS 仅离线使用；独立 Judge 若需新增下载，应单独确认，不构成默认在线依赖。

## 目标流程与设计

```text
ChatRequest（原始消息、thread_id、可选显式动作）
  → 读取唯一线程状态（普通近期消息、摘要、pending）
  → 一次结构化模型分析
      ├─ 清楚：≤3 个独立问题 → 现有 Child/Parent 检索 → 生成 → 在线可核验状态
      ├─ 不清楚：保存 pending → 发出一个具体澄清问题 → 停止本轮检索
      └─ 待办＋新题/取消：原子切换或清除待办，再处理新消息
  → 超过窗口才更新摘要；摘要不作 PDF 证据

离线：经核对的题集 → 固定知识库版本下实际问答和上下文
    → 五维 RAGAS Judge ＋ 安全步骤/拒答人工复核 → 逐题报告与成本对比
```

1. **入口分析**：扩展 `backend/app/rag/model_schema.py` 的结构化结果，调整 `query_analysis.py` 与 `conversation_memory.py`；删除正则对语义路由的决定权，保留格式/数值/型号的确定性核验。模型失败不能返回“假定清楚”。输入上限、缓存键和预算继续统一管理。显式用户动作优先于模型猜测。
2. **澄清与摘要**：`graph_state.py` 与 `ConversationMemory` 只保留一个权威待办来源；普通问答、澄清回复、内部工具消息有不同类型。待办状态的补充、新题、取消、不确定转移见[数据模型](data-model.md)。摘要按阈值更新，并计入明确预算；不能为省 Token 截断关键设备信息。
3. **标准答案集**：阶段 A 先确认现有 PDF 文件身份和哈希；阶段 C 逐题核对 Q1–Q5，再扩展追问、换题、并列问题、无证据、数值冲突、步骤遗漏等题。每题记录 `source_quote`、页码、`required_facts`、`forbidden_claims`、审核状态；未审核题不能进入正式统计。无答案/交互题与普通事实问答分开评分。
4. **离线评估**：遵循[参考项目 Notebook](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/notebooks/evaluation.ipynb)的五项指标，但锁定适用的 RAGAS 版本与本地 Judge 后才运行。`user_input/reference/response/retrieved_contexts` 必须来自真实题集和真实请求；保留检索原始排序与送入生成器的证据两个层次，避免“评估了另一份上下文”。不适用指标记原因，不填虚构分数。Judge 与人工意见冲突时以原文复核记录为准。
5. **在线契约**：`POST /chat/stream` 可增加显式动作；SSE 用新版本的 `verification` 事件表示证据核验，前端 `ScoreCard` 迁移为状态卡。旧 `evaluation` 固定数值事件退役，不做伪分数双写；接口迁移和前端同步验收，详见[接口契约](contracts/chat-and-evaluation.md)。

## 分阶段实施与产物

| 阶段 | 工作与交付物 | 验收门槛 | 停止点 |
|---|---|---|---|
| A：基线和标准答案规范 | 固定当前正则误判、澄清换题、Q3 漏步骤仍获高分案例；确认 PDF 版本；建立题目格式与人工核对流程；形成 `phase-a-report.md` | 至少 5 个原题有原文定位、必答事实草案；能复现三个已知问题；不改正式索引 | 报告后暂停 |
| B：入口分析和澄清 | 一次模型优先分析、统一待办状态、用户显式动作、摘要和降级；后端/必要的前端契约测试；`phase-b-report.md` | 清楚题不误澄清，换题不拼接，线程隔离、失败可追踪；预算与成本逐题可审计 | 报告后暂停 |
| C：完成标准答案集 | 将 5 个原题扩展为至少 15 题，逐条对照 PDF 审核；区分可回答、应拒答和交互场景；`phase-c-report.md` | 题集 100% 已审核且来源可核对；Q3 安全步骤完整；PDF 版本变化会使题目失效 | 报告后暂停 |
| D：离线 RAGAS 与在线状态 | Judge 兼容性冒烟、五维指标、逐题结果/人工复核、版本化报告；移除前端固定分数；`phase-d-report.md` | 可重复运行；不把不适用指标记为 0；故意缺步骤或无证据不显示“可信/完整”；在线请求无额外 Judge 调用 | 报告后暂停 |
| E：正式库回归与既有质量修复对齐 | Q1–Q5、至少 10 个扩展场景复测；与既有 V3-6～V3-8 的 Q3 证据/答案修复合并验收；`phase-e-report.md` | 原五题完整正确，Q3 连续 3 次含安全前置步骤；逐题 Token/耗时与基线对比；无未授权云端调用/索引变更 | 报告后暂停 |

上述阶段名是此功能的交付切片，不是立即执行指令。旧 [V3 后续质量修复计划](../003-v3-ollama-rag-quality/v3-post-acceptance-plan.md) 的 Q3 生成修复是阶段 E 的前置依赖；不得因只做评估而宣称 Q3 已修好。每阶段进入前再从当前 `spec.md/plan.md` 生成相应 `tasks.md` 并分析一致性；用户此前要求“一阶段一汇报”，不能一次实施 A～E。

## 风险、闸门与边界

- **成本闸门**：阶段 B 必须将简单题分析＋生成控制在现有 2 次模型调用上限内。若摘要或重试需要第 3 次，先暂停并报告可选方案；不能悄悄提高预算。阶段 D 的离线 Judge 单独统计调用和运行时间。
- **模型能力闸门**：本机 4B 模型若不能稳定返回结构化结果，保留明确失败提示并报告，不为测试通过重新堆语义正则。第二 Judge 模型下载须另得同意。
- **质量闸门**：RAGAS 分数只用于逐题诊断和版本对比；阈值在题集与 Judge 校准后预先登记。Q3 操作安全以原文必答步骤和人工复核为最终依据。
- **数据闸门**：本轮和 A～D 均不导入、删除或重建正式知识库；业务 PDF、OCR、多用户、云服务、持久化多进程记忆不在范围内。
- **进度边界**：正式题集已在 2026-10-07 获用户确认，T020 完成；本批执行 T026，未因采集完成而通过答案复核或 E 总验收。V3-8 既有同版本 Q3 三次隔离稳定性与正式 UI 证据仍仅是历史记录。原批按旧标准记录 Q2 未复述“立即断开主回路”；2026-10-08 校准将动作从阈值题必答点移为可选，不能再单凭该项判阈值漏答。Q8/Q14 的真实回退和澄清入口失败仍待解决；详见[原批记录](formal-ragas-report.md)与[校准解释](dataset-calibration-report.md)。

## 项目结构

### 本功能文档

```text
specs/004-query-clarification-ragas/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/chat-and-evaluation.md
├── quickstart.md
└── tasks.md                 # 已生成，逐阶段记录实际进度
```

### 现有代码与拟改动点

```text
backend/app/rag/
├── conversation_memory.py   # 线程状态与摘要
├── query_analysis.py       # 入口分析
├── model_schema.py         # 分析输出契约
├── graph.py / graph_state.py / pipeline.py
└── evaluator.py            # 在线状态迁移
backend/app/schemas/chat.py  # API/SSE 响应契约
backend/app/api/chat.py
backend/tests/unit/          # 入口/状态/评估单元测试
backend/tests/integration/   # 线程与正式链路集成测试
backend/scripts/             # 计划新增离线题集/评估入口
frontend/src/pages/Chat.tsx
frontend/src/components/ScoreCard.tsx
frontend/src/types/api.ts
```

**结构决定**：沿用现有 `backend/`＋`frontend/` Web 应用结构；离线题集与结果置于版本化测试/评估目录，不嵌入生产请求路径。
