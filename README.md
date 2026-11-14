# 文脉 · PDF 知识工作台

上传 PDF，用自然语言提问。文脉会从文档里找相关段落，在答案旁列出来源，方便回看原文、继续追问。

**本地知识库** · OpenAI 兼容接口 · Qdrant 混合检索 · LangGraph 问答编排

[功能](#功能) · [技术栈](#技术栈) · [工作流程](#工作流程) · [Agent Loop](#agent-loop) · [项目结构](#项目结构) · [快速开始](#快速开始) · [项目文档](#项目文档)

![文脉问答台显示关于测试装置的回答、PDF 来源，以及查看原文和执行过程的入口](docs/assets/wenmai-chat.png)

*问答台实录。演示使用隔离环境中的合成测试 PDF。*

<details>
<summary>查看知识库界面</summary>

![文脉知识库支持拖放上传、按名称与状态筛选，并显示文档处理状态](docs/assets/wenmai-library.png)

</details>

## 功能

| 能力 | 在工作台里可以做什么 |
| --- | --- |
| PDF 知识库 | 拖放上传文本型 PDF，按名称或状态筛选，查看文档是否已就绪。 |
| 多轮问答 | 普通对话直接回复。文档问题需要补充型号、对象或条件时，可以在同一会话继续说明。 |
| 证据回看 | 查看命中的文件、章节和原文片段。索引记录包含页码时，来源会带上页码。 |
| 执行过程 | 展开查看实际的模型调用和检索步骤，便于理解答案依据。 |

## 技术栈

| 层 | 使用的技术 | 用途 |
| --- | --- | --- |
| 前端应用 | **React 18 · TypeScript · Vite 6** | 登录、连续对话和知识库页面。 |
| 界面与交互 | **Tailwind CSS 4 · Base UI · Motion · Lucide** | 样式、可访问组件、动效和图标。 |
| 状态与答案渲染 | **Zustand · react-markdown · remark-gfm** | 会话状态、流式答案、Markdown 表格与代码。 |
| 后端 API | **Python 3.11+ · FastAPI · Uvicorn · Pydantic** | REST 接口、数据校验和 SSE 实时事件。 |
| Agent 编排 | **LangGraph · LangChain Core** | 模型判断工具需求，组织澄清、检索、多轮研究与答案汇总。 |
| PDF 处理 | **PyMuPDF · PyMuPDF4LLM** | 提取文本与文档结构，转换为 Markdown，供父子分块使用。 |
| 本地嵌入 | **fastembed · ONNX · 多语言 MiniLM** | 默认使用 `paraphrase-multilingual-MiniLM-L12-v2`，生成 384 维向量。 |
| 混合检索 | **Qdrant · Dense 向量 · BM25** | 在本地持久化索引，通过 DBSF 融合两路召回结果。 |
| 模型接入 | **OpenAI 兼容 API · langchain-openai** | 接入配置的问答模型，支持结构化输出和工具调用。 |
| 认证与测试 | **PyJWT · pwdlib · pytest · Vitest · jsdom** | 登录认证、密码哈希，以及后端与前端自动化验证。 |

## 工作流程

```mermaid
flowchart LR
    PDF["文本 PDF"] --> Chunks["解析与父子分块"]
    Chunks --> Index["Qdrant 混合索引"]
    Ask["用户提问"] --> Loop["Agent Loop"]
    Loop <-->|按需检索| Index
    Loop --> Answer["答案与来源"]
```

## Agent Loop

文脉使用 **LangGraph 主图 + 研究子图**。模型负责工具需求判断、问题分析、研究和作答，程序负责分发子问题、执行工具、维护状态及检查研究边界。

### 主图：消息分流与任务编排

```mermaid
flowchart TD
    Message["用户消息与会话上下文"] --> Select["select_tool<br/>模型判断是否需要知识库"]
    Select --> History["summarize_history<br/>按需摘要历史，重置本轮分支答案"]
    History --> Needs{"需要知识库？"}
    Needs -->|否| Direct["answer_direct<br/>模型直接回答"]
    Needs -->|是| Rewrite["rewrite_query<br/>改写、拆分子问题并判断信息充分性"]
    Rewrite --> Clear{"信息充分？"}
    Clear -->|否| Pending["request_clarification 前暂停<br/>checkpoint 保存原问题与补充"]
    Pending -->|用户补充后恢复| Rewrite
    Pending -.->|开始新问题，清除待办| Select
    Pending -->|取消| Cancel["清除待办并结束<br/>不调用模型"]
    Clear -->|是| Dispatch["Send 并行分发<br/>每个子问题独立研究"]
    Dispatch --> Research["agent · 研究子图<br/>模型与工具循环，见下图"]
    Research --> Aggregate["aggregate_answers<br/>等待分支完成，按子问题顺序统一聚合"]
    Direct --> Output["SSE 交付答案与来源"]
    Aggregate --> Output
```

待补充消息在同一会话恢复问题分析；显式开始新问题时重新进行工具需求判断。直接回答的来源为空，单个子问题的研究结果也会经过最终聚合。

### 研究子图：模型与工具循环

```mermaid
flowchart TD
    Question["单个子问题与独立分支状态"] --> Orchestrator["orchestrator<br/>模型选择继续研究或作答"]
    Orchestrator --> Calls{"返回工具调用？"}
    Calls -->|无| Collect["collect_answer<br/>收集分支答案及已检索上下文"]
    Calls -->|有| Budget{"迭代已达 10 次<br/>或累计工具请求超过 8 次？"}
    Budget -->|是| Fallback["fallback_response<br/>模型基于已有资料生成收尾答案"]
    Fallback --> Collect
    Budget -->|否| Tools["tools · ToolNode<br/>search_child_chunks<br/>retrieve_parent_chunks"]
    Tools --> Check{"should_compress_context<br/>上下文超过动态阈值？"}
    Check -->|否，继续研究| Orchestrator
    Check -->|是| Compress["compress_context<br/>模型压缩，保留检索标识并清理旧消息"]
    Compress --> Orchestrator
    Collect --> Return["回传主图，参与 aggregate_answers"]
```

- **两种检索工具**：`search_child_chunks` 通过 Dense + BM25 搜索子块；`retrieve_parent_chunks` 读取完整父块，补充章节上下文。研究提示要求首轮先搜索子块，后续由模型决定继续搜索、读取父块或回答。
- **两类摘要**：主图整理会话历史；研究子图在工具执行后检查上下文容量，超过动态阈值时压缩研究记录，再回到模型继续决策。
- **分支边界**：计数包含当前模型回复中的工具请求。触及上图边界时，本批工具不执行，转为收尾；没有工具请求时直接收集答案。摘要、压缩、收尾和聚合的模型调用另行发生。

图与当前实现对应：[图装配](backend/app/rag/graph.py)、[节点](backend/app/rag/nodes.py)、[条件路由](backend/app/rag/edges.py)、[工具](backend/app/rag/tools.py)和[会话恢复](backend/app/core/reference_session.py)。

## 项目结构

```text
agentic-rag/
├── start.py            # 一键启动前后端
├── backend/
│   ├── app/
│   │   ├── api/         # 登录、文档管理、聊天 SSE
│   │   ├── core/        # 模型适配、会话与事件投影
│   │   ├── knowledge/   # PDF 解析、分块、索引与检索
│   │   └── rag/         # LangGraph、节点、提示与工具
│   ├── scripts/        # 冒烟验证与索引维护
│   └── tests/          # 单元、集成、契约与安全测试
├── frontend/src/       # 登录、问答台与知识库
├── docs/               # 架构、运行指南与开发进度
└── specs/              # 功能规格与阶段报告
```

## 快速开始

需要 **Python 3.11+** 和 **Node.js 22+**。

### 一键启动

```powershell
git clone https://github.com/ifhgh666/agentic-rag.git
cd agentic-rag
python start.py
```

已有仓库时，在仓库根目录运行 `python start.py` 即可。启动器会自动准备依赖和本地嵌入模型，启动前后端。按 `Ctrl+C` 停止。

### 首次配置模型接口

第一次运行会创建 `backend/.env`。填写下面三项，再运行 `python start.py`。已有模型配置可直接复用。

| 配置 | 填写内容 |
| --- | --- |
| `LLM_BASE_URL` | OpenAI 兼容 API 地址 |
| `LLM_API_KEY` | 接口密钥 |
| `LLM_MODEL` | 服务商提供的模型名称 |

### 登录工作台

打开 [http://127.0.0.1:5173/](http://127.0.0.1:5173/)，使用本机演示账号 **`admin / 123456`** 登录。上传文本型 PDF（单文件上限 25 MB），等状态变为「已就绪」，再到问答台提问。

## 项目文档

- [架构与源码导航](docs/repository-guide.md) · 主图、检索、会话状态及公开事件
- [测试与运行操作](docs/testing-and-operations.md) · 回归命令、配置与索引维护
- [真实前后端联调记录](specs/017-frontend-nova-workspace/phase-e-report.md) · 上传、问答、来源与退出
- [当前进度](docs/CURRENT_STATUS.md) · 阶段交接、已知失败与历史记录

当前版本面向单管理员与文本型 PDF。扫描件需要先转成含文本层的 PDF。会话历史、摘要与待补充状态保存在进程内，重启后清空。
