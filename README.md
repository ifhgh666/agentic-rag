# 文脉 · PDF 知识工作台

上传 PDF，用自然语言提问。文脉会从文档里找相关段落，在答案旁列出来源，方便回看原文、继续追问。

**本地优先** · Ollama 推理 · Qdrant 混合检索 · LangGraph 问答编排

[功能](#功能) · [工作流程](#工作流程) · [项目结构](#项目结构) · [快速开始](#快速开始) · [项目文档](#项目文档)

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

## 工作流程

```mermaid
flowchart LR
    PDF["文本 PDF"] --> Chunks["解析与父子分块"]
    Chunks --> Index["Qdrant 混合索引"]
    Ask["用户提问"] --> Route{"需要查询知识库？"}
    Route -->|否| Direct["直接回答"]
    Route -->|是| Clarify{"检索条件足够？"}
    Clarify -->|不足| Follow["请用户补充"]
    Follow --> Clarify
    Clarify -->|足够| Search["向量 + BM25 检索"]
    Index --> Search
    Search --> Answer["生成答案并附来源"]
```

后端使用 **Python、FastAPI、LangGraph**，前端使用 **React、TypeScript、Vite**。PDF 经 PyMuPDF4LLM 解析后，使用 fastembed 的本地 ONNX 模型和 BM25 编码。模型默认由 Ollama 提供，也可显式接入 OpenAI 兼容服务。

## 项目结构

```text
agentic-rag/
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

需要 **Python 3.11+**、**Node.js 22+** 和已运行的 [Ollama](https://ollama.com/)。以下命令以 Windows PowerShell 为例。首次准备会下载模型资源。

### 1. 下载项目和本地模型

```powershell
git clone https://github.com/ifhgh666/agentic-rag.git
cd agentic-rag
ollama pull granite4.1:8b
```

### 2. 配置并启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
```

在 `backend/.env` 中设置 `ADMIN_PASSWORD_HASH` 和 `JWT_SECRET`。下面第一条命令交互式读取密码并生成哈希，第二条生成随机 JWT 密钥。登录用户名使用 `ADMIN_USERNAME`，示例为 `admin`。

```powershell
python -c "from getpass import getpass; from app.auth.security import hash_password; print(hash_password(getpass('Admin password: ')))"
python -c "import secrets; print(secrets.token_hex(32))"
```

首次运行先准备 Dense 嵌入模型，再启动 API。

```powershell
python -c "from fastembed import TextEmbedding; model = TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='data/models'); print(len(next(model.embed(['test']))))"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

<details>
<summary>使用 OpenAI 兼容服务</summary>

将 `LLM_PROVIDER` 设为 `openai_compatible`，并在本地 `backend/.env` 填写 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`。这种配置可以跳过下载 Ollama 模型，嵌入和索引仍在本地运行。配置字段见 [环境变量示例](backend/.env.example)。

</details>

### 3. 启动前端

另开一个终端，从仓库根目录运行。

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

打开 [工作台](http://127.0.0.1:5173/)，用配置的管理员账号登录。上传一份有可选中文字的 PDF（单文件上限 25 MB），等状态变为「已就绪」，再到问答台提问。后端状态可在 [健康检查](http://127.0.0.1:8000/api/health)查看。

## 项目文档

- [架构与源码导航](docs/repository-guide.md) · 主图、检索、会话状态及公开事件
- [测试与运行操作](docs/testing-and-operations.md) · 回归命令、配置与索引维护
- [真实前后端联调记录](specs/017-frontend-nova-workspace/phase-e-report.md) · 上传、问答、来源与退出
- [当前进度](docs/CURRENT_STATUS.md) · 阶段交接、已知失败与历史记录

当前版本面向单管理员与文本型 PDF。扫描件需要先转成含文本层的 PDF。会话历史、摘要与待补充状态保存在进程内，重启后清空。
