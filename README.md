# Agentic RAG —— 本地优先的 PDF 知识库问答系统

2026-11-02 / 017 E：真实浏览器、隔离后端、当前deepseek-flash及真实ONNX/BM25联调通过；登录/上传到就绪、跨页两轮、来源、删除/退出均验证。两题首答均正确（72小时/45天），8次模型、2次搜索，provider Token6479。正式数据与配置未操作；临时账号与自有实例结束。见[报告](specs/017-frontend-nova-workspace/phase-e-report.md)与[原答对照](specs/017-frontend-nova-workspace/phase-e-answer-comparison-20261102.md)。报告后暂停，等待用户验收。

2026-11-02 / 017 D：三页最终收尾完成，移除无消费旧样式；88项前端测试、31项受控浏览器检查、构建/依赖审计通过。CSS由77.98降至51.86kB，六组页面计算样式保持。A–D工程任务已交付，真实后端/模型未联调；见[阶段报告](specs/017-frontend-nova-workspace/phase-d-report.md)。报告后暂停，等待用户验收。

2026-10-29 / 017 C：知识库Nova改版完成，支持单PDF选择/拖入、名称与状态交集、真实响应状态轮询和统一删除确认。88项前端测试、22项受控浏览器检查、构建/依赖审计通过；真实后端与正式文档未操作，D未执行。见[阶段报告](specs/017-frontend-nova-workspace/phase-c-report.md)。报告后暂停，等待用户验收。

2026-10-29 / 017 B：连续对话、Enter发送/Shift换行/输入法保护、底部输入、轮内折叠过程与Markdown来源已实现；前端日志页及入口移除，后台保留。78项测试、23项受控浏览器场景、构建/依赖审计与108项保护核对通过；真实后端/模型未联调，C/D未执行。见[阶段报告](specs/017-frontend-nova-workspace/phase-b-report.md)。报告后暂停，等待用户验收。

2026-10-29 / 017 A：完整Nova前端改版计划与四图已落盘；本轮完成居中登录、Nova基础组件、公共导航/移动Sheet、真实健康状态和依赖约束。前端56项测试、22项受控浏览器检查、构建与依赖审计通过。问答/知识库/日志页面改版仍留B/C，真实模型与正式数据未操作。见[计划](specs/017-frontend-nova-workspace/plan.md)和[A报告](specs/017-frontend-nova-workspace/phase-a-report.md)。报告后暂停，等待用户验收。

2026-10-28 / 016 E 全量真实测试：按用户要求失败继续，15场景/19轮全部执行，**11通过、4部分正确未通过、0未运行**。模型79次、真实搜索20次；主要问题为Q3/Q15的错误文档缺失断言、Q9恢复流程与自检表述、Q14数值推理。产品和正式数据保持，旧失败不改判。见[模型原答与正确答案逐题对照](specs/016-reference-agent-semantics/phase-e-answer-comparison-20261028.md)及[E总报告](specs/016-reference-agent-semantics/phase-e-full-gold-20261028-report.md)，报告后暂停，等待用户验收。

2026-10-28 / 016 D 真实 PDF 测试：使用当前 deepseek-flash、真实 ONNX+BM25 和已批准 gold-1.0 题集的首批 Q1–Q4。Q1 链路完成但遗漏已检索到的“合格的万用表”，**0通过/1失败/3未运行**，按规则停止、无重试。模型 5 次、搜索 2 次、14.547 秒；产品、配置及正式数据保持。见 [D 报告](specs/016-reference-agent-semantics/phase-d-real-pdf-20261028-report.md)，报告后暂停，等待用户验收。

2026-10-27 / 016 B 续测：剩余澄清、直接补充、长上下文压缩、多问聚合四个真实场景全部通过；本轮模型 21 次、工具 7 次，317 项保护指纹无差异。与 R 的已通过首题核对同一源码/模型，五类所需场景均有通过证据，T001–T023 采集/工程任务完成待用户验收；原首次失败保留。澄清为英文，Parent/正式 PDF/ONNX/浏览器尚未实测。见 [续测报告](specs/016-reference-agent-semantics/phase-b-resume-20261027-report.md)。报告后暂停，等待用户验收。

2026-10-27 / 016 R 修复：正常参考图的当前 `openai_compatible/deepseek-flash` 实例现默认关闭思考，避免结构化入口和后续工具往返的兼容问题；其他模型/Ollama/legacy 保持。51 项定向工程检查通过，直接使用产品工厂、无临时 override 的真实首题完成：模型 4 次、搜索 1 次，正确回答 72 小时并附来源。代码策略对新建实例生效，本轮未重启服务；原 B 失败与四个未测场景保留。见 [R 报告](specs/016-reference-agent-semantics/phase-r-report.md)。报告后暂停，等待用户验收。

2026-10-27 / 016 真实诊断：用户明确要求直接用真实模型。原入口复现 HTTP 400，原因是思考模式不支持结构化入口的指定工具选择；同一 `deepseek-flash` 在诊断请求中关闭思考后，完整首题完成，模型 4 次、搜索 1 次，正确回答 72 小时并附实际来源。产品源码和 `.env` 未修改，原 B 失败不改判、其余四场景未运行。见[诊断报告](specs/016-reference-agent-semantics/phase-b-diagnosis-20261027-report.md)。报告后暂停，等待用户验收。

2026-10-27 / 016 B 首次真实验收未通过：沿用当前实际配置 `openai_compatible / deepseek-flash`、温度 0、种子 42，使用独立合成知识库。首题在 rewrite_query 调用以 `OpenAIInvalidRequestError` 失败，约 0.448 秒；模型尝试计数 1、工具 0、无答案。按预先冻结规则停止：**0 通过 / 1 失败 / 0 待定 / 4 未运行**，无重试。异常具体参数尚未确定，原 A 工程结论及历史质量失败保留。见 [B 报告](specs/016-reference-agent-semantics/phase-b-report.md)与[当前 016 失败](specs/016-reference-agent-semantics/CURRENT_FAILURES.md)。308 项保护指纹保持，正式知识库和配置未改。报告后暂停，等待用户验收。

2026-10-27 / 016 A：参考 Agent 执行语义及工程收尾完成，待用户验收。主图整理历史、改写/澄清、分支研究并统一聚合；研究恢复模型压缩、完整 Parent 和参考路由。待办默认续答，在线核验卡已移除，用量只统计。独立审查发现的重复原题补充清理、SSE 断开读线程泄漏已修复。完整隔离回归 **720 passed / 2 既有失败 / 24 skipped / 2 deselected**，前端 **40 passed**、构建退出 0；真实模型和 B 未运行。见 [016 A 总报告](specs/016-reference-agent-semantics/phase-a-report.md)。报告后暂停，等待用户验收。下列日期化记录保留当时事实。

2026-10-22 / 015 A：按职责重新组织八文件 Agent 核心。`backend/app/rag/` 实际保留图、节点、模型循环、原文准入、状态和提示/schema；模型协议、调用治理、问题分析、生成核验、会话与请求交付分别位于 `backend/app/core/`，编码、索引和检索位于 `backend/app/knowledge/`。这次迁移保留原有算法与独立旧接口，不把搬移行数当作减码。当前范围及验证见 [015 阶段 A 报告](specs/015-rag-responsibility-clarity/phase-a-report.md)：完整隔离回归 820 通过、两项既有提示断言失败，24 跳过、2 排除；报告后暂停，等待用户验收。下列日期化记录保留当时事实。

2026-10-22：RAG 实现已收敛为 `backend/app/rag/` 中八个实际源文件：`__init__.py`、`edges.py`、`graph.py`、`graph_state.py`、`nodes.py`、`prompts.py`、`schemas.py`、`tools.py`。图装配与请求交付在 graph，分析/循环/生成/核验在 nodes，模型调用治理与检索索引在 tools，会话状态与存储在 graph_state；原内部类与函数能力保留。旧模块导入路径已迁移，无转发文件。当前验证结果与限制以 [014 阶段报告](specs/014-eight-file-rag/phase-a-report.md)为准；下列日期化记录保留历史事实。

2026-10-20 Agent 架构已收敛到唯一的 `backend/app/rag/` 包：图、节点、边、状态、提示、schema、工具以及检索和模型服务都按职责组织在同一目录。所有生产提示和模型消息模板集中在 [prompts.py](backend/app/rag/prompts.py)，入口版本为 `rewrite-prompt-v6-zh`。A3 单包阶段的 117 项定向检查通过；完整后端回归为 588 通过、3 失败，其中两项是既有 v4 提示措辞断言，一项截止时间测试在全量套件中超时但单独复跑通过。详见[单包收敛报告](specs/007-centralize-prompts/phase-single-rag-package-20261018-report.md)，报告后暂停，等待用户验收。

2026-10-15唯一对象代词代码兜底已实现并复测：模型对RW07仍原始误澄清，但代码识别历史唯一PN8733并改写为“PN8733的恢复条件是什么？”，真实入口**1通过、0失败、0待定、0未运行**。新增多对象保守性单测通过；见[唯一对象兜底报告](specs/007-centralize-prompts/phase-reference-fallback-20261015-report.md)，报告后暂停，等待用户验收。

2026-10-15唯一对象代词RW07复测：历史包含PN8733、当前问“它的恢复条件是什么？”，`rewrite-prompt-v6-zh` 真实入口首答结构有效但仍误澄清，**0通过、1失败、0待定、0未运行**。无工具、检索、云端、Judge或重试；见[RW07代词复测报告](specs/007-centralize-prompts/phase-pronoun-rw07-20261015-report.md)，报告后暂停，等待用户验收。

2026-10-14 中文轻量入口prompt三题复测：当前工作区使用 `rewrite-prompt-v6-zh`；D13/RW13、D14/RW14、D15/RW15 三次真实入口调用均结构有效但语义失败，**0通过、3失败、0待定、0未运行**。D14已恢复中文输出，D13共享条件和D15容量澄清仍失败；无重试、工具、检索、云端或Judge调用。见[中文prompt复测报告](specs/007-centralize-prompts/phase-chinese-prompt-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-14 轻量英文prompt三题复测：当前工作区暂用用户提供的 `rewrite-prompt-v5` 候选；D13/RW13、D14/RW14、D15/RW15 三次真实入口调用均结构有效但语义失败，**0通过、3失败、0待定、0未运行**。没有重试、工具、检索、云端或Judge调用；v5尚未接受为稳定版本，也未自动回滚。见[三题复测报告](specs/007-centralize-prompts/phase-light-prompt-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-14 P业务prompt候选未通过质量验收：v4的145项相关工程检查通过；真实诊断6题4通过/2失败/0待定/0未运行，原17题回归12通过/5失败/0待定/0未运行。两批分别保存首答，错误继续、零重试；新增完整问误澄清/历史混入退步，已撤回v4候选并恢复当时测试前的v3；schema修复与其他配置保持。候选/首答和旧成绩均保留。见[业务提示候选报告](specs/007-centralize-prompts/phase-business-prompt-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-14：字段联动修复后的真实入口17题复测T2已完成，**14通过、3失败、0待定、0未运行**；17/17条首答结构有效。每题首答1次、失败继续，未重试。模型/prompt/schema/配置/题集冻结，旧失败记录保持。这是Codex逐题审阅，待用户验收；完整输入题集不证明原代词/省略补全或端到端质量。见[入口复测报告](specs/007-centralize-prompts/phase-entrance-retest-20261014-report.md)，报告后暂停，等待用户验收。

2026-10-13用户授权字段联动生成约束修复R：独立schema已增加清楚/待澄清两个完整anyOf分支，不改prompt或清空‘无／否’。133项相关工程检查与585项完整后端回归通过；两次真实合成首答结构2/2有效、预期状态1/2通过（无历史代词仍误判清楚）。原17题0通过/17失败记录保留，未重跑题集或端到端。见[字段联动修复报告](specs/007-centralize-prompts/phase-schema-fix-20261013-report.md)，报告后暂停，等待用户验收。

基于本地大模型与混合检索的 Agentic RAG 问答系统：上传 PDF 文档，经结构化解析、
父子分块、Dense+Sparse 混合检索和 LangGraph 多阶段编排，让本地 Ollama 模型
**仅基于检索到的原文证据**回答问题，并给出可核对的来源引用。

默认使用本地 Qdrant 索引、本地 ONNX 嵌入与本地 Ollama 推理，不自动切换云端模型；
仅当显式设置 `LLM_PROVIDER=openai_compatible` 时才会使用另行配置的兼容接口。
模型与资源首次准备可能需要下载；当前 BM25 默认初始化仍可能访问资源元数据，不等于完全断网启动。

2026-10-13当前版本真实入口测试已结束：沿用完整输入17题，Granite8B与rewrite-prompt-v3/独立schema，**0通过、17失败、0未运行**，未重试。全部因清楚状态的澄清字段非空而被既有联动校验拒绝；恢复共享条件、额外比较分支、四需求容量仍有业务问题。28项采集器隔离检查通过，产品prompt/schema和正式数据保持。见[当前入口测试报告](specs/007-centralize-prompts/phase-entrance-20261013-report.md)，报告后暂停，端到端尚未测。

2026-10-13用户另行授权模型对齐：本机已下载并改用上游[实际配置](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/config.py)相同的 `granite4.1:8b`，温度0、种子42。88项针对性工程检查通过；真实合成原生工具探测通过，结构化首测因清楚状态仍返回澄清文字“无”而失败。后端8000当前不可连接，下次启动读取新配置。见[模型补充报告](specs/007-centralize-prompts/phase-model-alignment-report.md)，旧题集质量状态保留，报告后暂停。

随后用户授权删除旧模型：`qwen3:4b-instruct` 已从本机Ollama移除，当前安装清单仅保留 `granite4.1:8b`，配置保持。见[旧模型清理记录](specs/007-centralize-prompts/model-removal-20261013-report.md)。

当前前端功能为 [017：Nova知识工作台](specs/017-frontend-nova-workspace/plan.md)，A–E工程已交付，真实隔离联调已通过，待用户验收；Agent执行语义仍以 [016：恢复参考 Agent 执行语义](specs/016-reference-agent-semantics/plan.md)，保留 015 的职责目录。参考原始提示和三字段 schema 位于 `rag/prompts.py`、`rag/schemas.py`；旧 `rewrite-prompt-v6-zh` 及严格 schema 冻结在 `core/legacy_*`，供独立旧接口使用。研究工具后超过 `2000 + int(summary_tokens * 0.9)` 时模型压缩；来源由最终 Sources 与本次真实工具记录的文件名交集生成。工程结果不改判历史真实问答失败。

[006：问题补全、改写与拆分 V1](specs/006-query-rewrite-split/plan.md)的历史记录：2026-10-11，A–D 工程工作已完成。原E在用户接受RW03普通空格变化后续测，累计6通过、1失败、10未运行，RW07代词补全失败；[E续测报告](specs/006-query-rewrite-split/phase-e-resume-20261011-report.md)保留。最新完整输入题集结果见下段。原F首批Q16恢复子问缺共同条件、完整答案未验收通过，C-UV与比较题未运行。见[006 任务清单](specs/006-query-rewrite-split/tasks.md)。005的两道真实失败题仍未验收通过。

用户随后要求将需要补充的测试题写完整，并要求E遇错继续。[新版 E 题集](backend/tests/fixtures/query_rewrite_v1_completed_cases.json)17题已全部采集首次输出：**10通过、7失败、0未运行**，质量验收未通过。错误涉及误澄清、遗漏共享型号/条件、型号或数字失真、额外比较检索及超过三问。最新交付为[完整E报告](specs/006-query-rewrite-split/phase-e-completed-all-20261011-report.md)；仅采集工具增加继续模式，产品prompt未改，旧失败保留，不执行F。

## 核心特性

### 知识库与检索
- **结构化 PDF 解析**：PyMuPDF4LLM 将文本 PDF 解析为带标题层级、表格和页码的 Markdown（扫描件 OCR 暂不支持）
- **父子分块**：Parent 按标题层级划分、用于回答时还原上下文；Child 在 Parent 内细分为检索单元
- **混合检索**：Qdrant 本地持久化 Dense（fastembed 多语言 MiniLM，384 维 ONNX）+ Sparse（BM25）双路召回
- **索引清单校验**：解析/分块版本、嵌入配置或源 PDF 内容不匹配时拒绝使用陈旧索引，`/api/health` 明确返回 `index_ready=false`

### Agentic 编排（LangGraph）
- 主图：整理历史 → 改写/澄清 → 分支研究 → 统一聚合；单问也执行聚合
- 入口为清晰度、问题列表和澄清文字三个字段，最多三问由参考提示引导；兼容端点显式 function calling，Ollama 沿用当前 SDK 默认 JSON Schema
- 有待办时直接发送即可补充，保留显式继续、新题和取消；取消无模型调用
- checkpoint 统一保存进程内历史、摘要和 pending，同线程互斥；重启后会话丢失
- 检索无结果或证据不足时明确说明信息不足，不编造答案

### 答案质量保障
- 参考提示要求基于资料回答；只把聚合节点的输出展示为答案
- 来源使用本次工具记录与最终 Sources 的精确文件名交集，页码来自真实元数据
- 在线流程不生成核验卡；来源匹配不证明数值推导、操作步骤或语义完整性，原真实质量失败保持
- 历史滚动摘要与研究上下文压缩各自调用模型；研究压缩保留首问和已执行检索标识
- RAGAS 仅用于离线诊断，不增加在线 Judge 调用；15 题已由用户批准为 `gold-1.0`，首批实际评估已结束，完整评分与回答人工验收尚未完成

### 成本控制与可观测性
- 每分支保留 8 个工具请求、10 次研究迭代，图递归 50；无工具先收尾，越界整批不执行并由模型 fallback。摘要、压缩和聚合不属于研究计数
- 正常参考入口取消旧 8/12 总调用、5/4/3 配额、300/120 秒应用截止和旧输入/输出上限；SDK/服务可能失败或等待，没有替代墙钟上限承诺
- `usage` SSE 事件与 `rag.usage` 结构化日志：实测/估算 Token、各节点调用次数、缓存命中、模型与请求耗时；不记录提示词正文、私有推理或密钥
- 旧分析/治理缓存保留供独立旧接口；当前图不经旧主图或治理回退
- 前端过程面板展示实际节点、工具正文和用量次数；`model_call_limit=null` 时仅显示实际调用次数。后台日志可按请求审计

### 安全
- JWT 管理员登录，密码仅存哈希（pwdlib 推荐算法，缺失时 pbkdf2 回退）
- 失败原因脱敏，异常信息不泄露文档内容
- Ollama 模式不读取云端 `LLM_BASE_URL`/`LLM_API_KEY`，本地服务不可用也不会偷偷切云端

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · LangGraph · Qdrant（本地模式）· fastembed（ONNX）· PyMuPDF4LLM |
| 前端 | React 18 · TypeScript · Vite · Vitest |
| 模型 | 代码默认 Ollama，支持显式配置 OpenAI 兼容服务。017 E 联调使用 `openai_compatible / deepseek-flash`，嵌入使用本地 fastembed |

## 目录结构

```
backend/
  app/
    api/            # REST/SSE 接口（auth、chat、knowledge、logs、debug）
    auth/           # JWT 认证与密码哈希
    core/           # 模型协议/调用治理、分析、生成核验、会话、请求交付与独立旧接口
    knowledge/      # PDF、父子分块、文档生命周期、Dense/Sparse 编码、索引和检索
    rag/            # 八文件 Agent 核心：图、节点/模型循环、边、状态、提示、schema、工具准入
    observability/  # 执行日志与 SSE 事件
    schemas/        # Pydantic 模型
  scripts/          # 冒烟测试与索引迁移脚本
  tests/            # 单元 / 契约 / 集成 / 安全测试
frontend/
  src/              # React 页面、组件、API 客户端、SSE
specs/              # 功能规格、计划、任务和阶段报告（Spec Kit）
```

## 快速开始

### 前置条件

- Python 3.11+、Node.js 22+（Nova基础依赖cn要求）
- [Ollama](https://ollama.com) 及一个指令模型：

```powershell
ollama pull granite4.1:8b
```

### 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 仅首次运行且 .env 不存在时复制；已有配置不要覆盖
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
# 1) ADMIN_PASSWORD_HASH —— 生成管理员密码哈希并填入：
python -c "from app.auth.security import hash_password; print(hash_password('你的密码'))"
# 2) JWT_SECRET —— 替换为随机长字符串
# 3) OLLAMA_MODEL —— 设为你已拉取的模型名

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Dense 嵌入为本地 ONNX（不依赖 PyTorch），生产加载只读取本地缓存；首次准备可用以下命令下载。此步骤不保证 BM25 资源也已离线就绪：

```powershell
python -c "from fastembed import TextEmbedding; m=TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='data/models'); print(len(list(m.embed(['中文测试']))[0]))"
```

离线跑单元测试时可设 `EMBEDDING_BACKEND=deterministic`，该模式不能作为真实语义检索的验收依据。

### 前端

```powershell
cd frontend
npm install
npm run dev
```

开发服务器运行在 `http://localhost:5173`，`/api` 自动代理到后端 8000 端口。
浏览器打开后用配置的管理员账号登录，即可上传 PDF（单文件 ≤ 25 MB）并开始提问。

### 常用配置（`backend/.env`）

下表保留现有配置兼容字段。016 正常图不读取旧总模型额度、节点额度、请求/单调用截止、输入准入及分析历史预算；参考常量与 provider 行为以 [016 计划](specs/016-reference-agent-semantics/plan.md)为准。

| 变量 | 说明 | 默认 |
|---|---|---|
| `LLM_PROVIDER` | `ollama`（默认本地） / `openai_compatible`（云端，需另配三项） / `fake`（测试） | `ollama` |
| `OLLAMA_MODEL` | 本地模型名 | — |
| `MAX_SIMPLE_LLM_CALLS` / `MAX_LLM_CALLS_PER_REQUEST` | 单分支 / 多分支每请求模型调用上限 | 8 / 12 |
| `MAX_QUERY_ANALYSIS_CALLS` / `MAX_TOOL_CALLS` | 入口模型调用 / 整次请求工具调用上限 | 1 / 16 |
| `REQUEST_TIMEOUT_SECONDS` / `LLM_TIMEOUT_SECONDS` | 整请求 / 单次模型等待秒数 | 300 / 120 |
| `MAX_CONTEXT_TOKENS` | 模型输入 Token 预算 | 3072 |
| `RETRIEVAL_TOP_K` / `RETRIEVAL_MIN_SCORE` | 检索数量与分数阈值 | 7 / 0.4 |
| `RAG_CACHE_TTL_SECONDS` / `RAG_CACHE_MAX_ENTRIES` | 缓存时长与容量 | 300 / 256 |
| `SPARSE_OFFLINE_FALLBACK` | 显式使用本地 BM25 兼容编码，须与现有索引配置一致 | 代码默认 `false`；示例配置为 `true` |
| `MAIN_HISTORY_MESSAGES_TO_KEEP` / `MAIN_HISTORY_INPUT_TOKEN_LIMIT` | 普通近期消息窗口 / 分析历史输入估算 Token 上限 | 4 / 4000 |

完整变量见 `backend/.env.example`。

## 测试与回归

016 A 的完整隔离入口及实际结果见 [验证指南](specs/016-reference-agent-semantics/quickstart.md)和 [A 报告](specs/016-reference-agent-semantics/phase-a-report.md)。下列 V3/V4 脚本为历史回归入口，不能替代 016 验收；真实模型运行仍需明确授权。

```powershell
# 后端工程回归（fake LLM + 独立测试索引目录；不代表真实质量）
cd backend; python -m pytest -q tests/unit tests/contract tests/integration tests/security

# 前端测试与构建
cd frontend; npm test -- --run; npm run build

# 统一回归（需 Ollama 运行中；全部在临时数据目录运行，不触碰正式索引）
cd backend; python -m scripts.smoke_v3_5_regression
```

统一回归覆盖八类场景：四道真实 PDF 基线题、无证据、同线程追问、多事实、冲突证据，并校验调用次数、Token 与云端调用为 0。

004 的历史离线检查在 `backend` 目录执行：

```powershell
python -m pytest -q tests/integration/test_v4_formal_regression.py
python -m scripts.validate_v4_gold_dataset --json
```

前者覆盖 15 个候选场景的协议与状态，并审计已保存的 V3-8 真机结果，不代表 15 题真实模型答题全通过。正式题集以所选数据集及对应审核记录为准；004 已有 `gold-1.0` 批准记录，不能以旧草稿检查的结果代替当前题集状态。006 的真实入口和端到端验收分别属于 E/F，需逐阶段授权。

其他脚本（均在 `backend` 目录运行）：

- `smoke_ollama` / `smoke_ollama_api`：合成证据问答 / 临时索引全链路冒烟
- `smoke_v3_4_baseline`：强制压缩预算下的回答接地验证
- `smoke_v3_4_conflict`：冲突证据场景
- `reindex_v3`：旧索引迁移。先预览、确认后加 `--apply`（自动备份到 `backend/data/backups/`）；**必须先停止后端**，避免本地 Qdrant 被占用

## 迭代历史

| 版本 | 内容 | 规格 |
|---|---|---|
| V1 | FastAPI + FAISS + 本地 ONNX 嵌入的基础问答系统，SSE 过程展示、答案质量评估、请求级日志追踪 | `specs/001-pdf-rag-qa` |
| V2 | Qdrant Dense+Sparse 混合索引，LangGraph 主图 + 子代理编排的多轮受控检索 | `specs/002-agentic-rag-v2` |
| V3 | 结构化解析与父子分块、本地 Ollama 问答、证据接地与反幻觉、上下文压缩、模型成本闸门与用量审计 | `specs/003-v3-ollama-rag-quality` |
| 004 后续功能 | 模型优先的问题分析、统一澄清状态与摘要、已批准标准答案集、离线 RAGAS 工具、诚实在线核验 | `specs/004-query-clarification-ragas` |
| 005 模型循环 | 模型决定查询、工具、继续检索及回答；程序负责预算、引用、隔离和截止时间；C 的真实验收未通过 | `specs/005-model-driven-agent-loop` |
| 006 问题补全与拆分 | A–D工程完成；新版E已全测，10通过、7失败；原补全及F失败保留 | `specs/006-query-rewrite-split` |

每个阶段都有对应验收报告（`specs/*/v*-report.md`），记录当时的测试结论与已知边界。
工程交接见历史[收尾报告](specs/004-query-clarification-ragas/phase-e-report.md)；2026-10-07 后续题集批准与首批真实评估见[运行记录](specs/004-query-clarification-ragas/formal-ragas-report.md)。题集审核已完成，正式全量验收仍未通过。

## 已知边界

- 仅支持文本 PDF；OCR、多模态、多用户权限、生产部署不在当前范围内
- 缓存为单进程内存缓存，重启即清空，多进程部署不共享
- 近期消息、摘要及待澄清状态也只保存在后端进程内，重启会丢失；摘要仅辅助理解，不是 PDF 答案证据
- 参考图在 worker 中同步执行，SSE 实时传递实际图事件和累计聚合答案；断开可释放队列消费者，当前 SDK 调用仍可能等待返回
- 006工程测试使用fake/scripted provider和确定性嵌入；原E续测工程检查97 passed，本次继续模式26 passed。新版完整输入17题全测为10通过、7失败、0未运行；不能与原题集补全成绩混合。原F首次Q16数字及核心结论正确，但恢复子问缺共同条件、引文issue_found，另两题未运行；入口和端到端真实质量均尚未通过
- V3-8 的原五题结果不能直接等同于更严格的候选题集验收；例如 Q2 已有回答包含阈值与持续时间，但缺少候选必答点“立即断开主回路”
- 操作类问题（如设备维护流程）的回答不能替代原始设备手册与人工复核；证据不足以确认关键步骤时，系统应明确提示而非给出看似完整的指导
