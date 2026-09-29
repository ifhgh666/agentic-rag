# Agentic RAG —— 本地优先的 PDF 知识库问答系统

基于本地大模型与混合检索的 Agentic RAG 问答系统：上传 PDF 文档，经结构化解析、
父子分块、Dense+Sparse 混合检索和 LangGraph 多阶段编排，让本地 Ollama 模型
**仅基于检索到的原文证据**回答问题，并给出可核对的来源引用。

默认全程本地运行：本地 Qdrant 索引、本地 ONNX 嵌入、本地 Ollama 推理，云端调用为 0；
仅当显式设置 `LLM_PROVIDER=openai_compatible` 时才会使用云端兼容接口，且不会自动回退切换。

## 核心特性

### 知识库与检索
- **结构化 PDF 解析**：PyMuPDF4LLM 将文本 PDF 解析为带标题层级、表格和页码的 Markdown（扫描件 OCR 暂不支持）
- **父子分块**：Parent 按标题层级划分、用于回答时还原上下文；Child 在 Parent 内细分为检索单元
- **混合检索**：Qdrant 本地持久化 Dense（fastembed 多语言 MiniLM，384 维 ONNX）+ Sparse（BM25）双路召回
- **索引清单校验**：解析/分块版本、嵌入配置或源 PDF 内容不匹配时拒绝使用陈旧索引，`/api/health` 明确返回 `index_ready=false`

### Agentic 编排（LangGraph）
- Main Graph + Agent Subgraph：查询分析 → 检索规划 → 并行子代理检索 → 证据缺口改写 → 上下文压缩 → 证据生成 → 答案评估
- 多轮追问记忆；明确的多事实问题直接并行处理，真正指代不明的问题才主动澄清
- 检索无结果或证据不足时明确说明信息不足，不编造答案

### 答案质量保障
- 引文逐字核验：答案标注的引用必须能在证据原文中找到
- 数值校验：答案中的数值必须受证据支持
- 答案质量评估分数随回答返回，前端同步展示
- 上下文自动压缩到 Token 预算内，压缩后仍保留关键数值与来源

### 成本控制与可观测性
- 请求级模型调用预算：简单问题默认最多 2 次、复杂/多问题最多 4 次；查询分析、改写、压缩、回答各有独立上限，并行子代理共享同一总预算，预算耗尽后只列证据或说明不足
- `usage` SSE 事件与 `rag.usage` 结构化日志：实测/估算 Token、各节点调用次数、缓存命中、模型与请求耗时；不记录提示词正文、私有推理或密钥
- 有界内存缓存（默认 300 秒 / 256 条）：查询分析、证据缺口改写、检索结果按索引清单版本自动失效
- 前端过程面板展示实际执行轨迹与用量预算；日志页可按请求审计全链路

### 安全
- JWT 管理员登录，密码仅存哈希（pwdlib 推荐算法，缺失时 pbkdf2 回退）
- 失败原因脱敏，异常信息不泄露文档内容
- Ollama 模式不读取云端 `LLM_BASE_URL`/`LLM_API_KEY`，本地服务不可用也不会偷偷切云端

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · LangGraph · Qdrant（本地模式）· fastembed（ONNX）· PyMuPDF4LLM |
| 前端 | React 18 · TypeScript · Vite · Vitest |
| 模型 | Ollama（本机使用 `qwen3:4b-instruct`）· fastembed 多语言本地嵌入 |

## 目录结构

```
backend/
  app/
    api/            # REST/SSE 接口（auth、chat、knowledge、logs、debug）
    auth/           # JWT 认证与密码哈希
    knowledge/      # PDF 解析、父子分块、文档与索引管理
    rag/            # LangGraph 编排、检索、生成、评估、成本控制、缓存
    observability/  # 执行日志与 SSE 事件
    schemas/        # Pydantic 模型
  scripts/          # 冒烟测试与索引迁移脚本
  tests/            # 单元 / 契约 / 集成 / 安全测试
frontend/
  src/              # React 页面、组件、API 客户端、SSE
specs/              # V1–V3 规格、计划与各阶段验收报告（Spec Kit）
```

## 快速开始

### 前置条件

- Python 3.11+、Node.js 18+
- [Ollama](https://ollama.com) 及一个指令模型：

```powershell
ollama pull qwen3:4b-instruct
```

### 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 首次运行：复制 .env.example 为 .env，至少完成三项配置
copy .env.example .env
# 1) ADMIN_PASSWORD_HASH —— 生成管理员密码哈希并填入：
python -c "from app.auth.security import hash_password; print(hash_password('你的密码'))"
# 2) JWT_SECRET —— 替换为随机长字符串
# 3) OLLAMA_MODEL —— 设为你已拉取的模型名

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

嵌入模型为本地 ONNX（不依赖 PyTorch），首次准备时下载一次，之后只读本地缓存：

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

| 变量 | 说明 | 默认 |
|---|---|---|
| `LLM_PROVIDER` | `ollama`（默认本地） / `openai_compatible`（云端，需另配三项） / `fake`（测试） | `ollama` |
| `OLLAMA_MODEL` | 本地模型名 | — |
| `MAX_SIMPLE_LLM_CALLS` / `MAX_LLM_CALLS_PER_REQUEST` | 简单题 / 总体每请求模型调用上限 | 2 / 4 |
| `MAX_CONTEXT_TOKENS` | 上下文 Token 预算 | 4000 |
| `RETRIEVAL_TOP_K` / `RETRIEVAL_MIN_SCORE` | 检索数量与分数阈值 | 7 / 0.4 |
| `RAG_CACHE_TTL_SECONDS` / `RAG_CACHE_MAX_ENTRIES` | 缓存时长与容量 | 300 / 256 |
| `SPARSE_OFFLINE_FALLBACK` | 网络不可用时使用本地 BM25 兼容编码 | `true` |

完整变量见 `backend/.env.example`。

## 测试与回归

```powershell
# 后端全量测试（离线：fake LLM + 独立测试索引目录）
cd backend; python -m pytest -q

# 前端测试与构建
cd frontend; npm test -- --run; npm run build

# 统一回归（需 Ollama 运行中；全部在临时数据目录运行，不触碰正式索引）
cd backend; python -m scripts.smoke_v3_5_regression
```

统一回归覆盖八类场景：四道真实 PDF 基线题、无证据、同线程追问、多事实、冲突证据，并校验调用次数、Token 与云端调用为 0。

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

每个阶段都有对应验收报告（`specs/*/v*-report.md`），记录当时的测试结论与已知边界。

## 已知边界

- 仅支持文本 PDF；OCR、多模态、多用户权限、生产部署不在当前范围内
- 缓存为单进程内存缓存，重启即清空，多进程部署不共享
- 图执行为同步运行，SSE 在图完成后回放实际轨迹，而非逐节点实时推送
- 操作类问题（如设备维护流程）的回答不能替代原始设备手册与人工复核；证据不足以确认关键步骤时，系统应明确提示而非给出看似完整的指导
