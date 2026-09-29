# 后端

## 本地运行

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

首次使用前，请复制 `.env.example` 为 `.env`，并配置管理员密码哈希。

V2-4 使用本地持久化 Qdrant Dense+Sparse 混合索引，并通过 LangGraph Main Graph 与 Agent
Subgraph 编排受控多轮检索；默认目录为 `backend/data/qdrant`。服务运行时
同一目录只能由一个 Qdrant 本地客户端打开；运行测试时测试夹具会自动使用独立目录。
旧版 `backend/data/index/vectors.npy` 和 `children.json` 在无 Qdrant Point 时仍可迁移，
但 V3 的版本校验会阻止未重新解析的旧索引参与检索。Sparse 模型名默认为 `Qdrant/bm25`；当前开发配置已缓存
官方模型。网络不可用时可开启 `SPARSE_OFFLINE_FALLBACK=true`，使用本地 BM25 兼容编码。

## 测试

```powershell
python -m pytest
```

## V3-1：结构化解析、真实 Dense 与索引迁移

上传的可选中文本 PDF 通过 PyMuPDF4LLM 生成带标题、表格和页码的 Markdown；
Parent 按标题层级划分，Child 在 Parent 内分块。扫描件 OCR 暂不支持。

默认 `EMBEDDING_BACKEND=fastembed`，使用本地 ONNX 多语言模型
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`（384 维），不依赖
PyTorch；模型缺失会明确报错，不会暗中回退到哈希向量。模型仅在首次手动准备时下载，
问答和上传流程只读取本地缓存。可从 `backend` 目录执行：

```powershell
python -c "from fastembed import TextEmbedding; m=TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='data/models'); print(len(list(m.embed(['中文测试']))[0]))"
```

如果只运行离线单元测试，设置 `EMBEDDING_BACKEND=deterministic`；此模式不能作为
真实中文语义检索的验收依据。旧版 `USE_TRANSFORMER_EMBEDDING=false` 仍兼容，
但若明确设置了 `EMBEDDING_BACKEND`，以后者为准。

V3-1 的索引清单会校验解析/分块版本、嵌入配置、源 PDF 内容和 Qdrant Point。
旧索引不匹配时 `/api/health` 返回 `index_ready=false`，不会继续使用陈旧内容。
已有文档迁移步骤（**先停止后端**）：

```powershell
cd C:\Users\ifhgz\Desktop\agentic-rag\backend
python -m scripts.reindex_v3
python -m scripts.reindex_v3 --apply
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

第一条只预览；`--apply` 会先在 `backend/data/backups/` 备份文档记录与旧 Qdrant，
再重解析所有 ready 文档并重建索引。不要在后端仍占用本地 Qdrant 时运行。
当前项目的测试 PDF 已完成此迁移；不必重复执行。V3-1 只验证检索证据，
最终回答质量留给后续 V3-4 阶段。

## V3-2：本地 Ollama 问答

`LLM_PROVIDER=ollama` 是默认值。安装 Ollama、下载模型后，把 `backend/.env` 中的
`OLLAMA_MODEL` 设置为实际模型名；本机示例为 `qwen3:4b-instruct`。模型地址只能是本机 HTTP
地址，Ollama 模式不会读取原有 `LLM_BASE_URL` 或 `LLM_API_KEY`，本地服务不可用时也
不会自动切到云端。需要主动使用云端兼容接口时，明确设置
`LLM_PROVIDER=openai_compatible` 并配置上述三个云端字段。

```powershell
ollama pull qwen3:4b-instruct
cd C:\Users\ifhgz\Desktop\agentic-rag\backend
python -m scripts.smoke_ollama
python -m scripts.smoke_ollama_api
```

若旧 PowerShell 窗口提示找不到 `ollama`，先新开终端；本机安装路径是
`C:\Users\ifhgz\AppData\Local\Programs\Ollama\ollama.exe`，也可直接用完整路径执行。

`smoke_ollama` 使用合成证据验证中文问答、工具调用与模型用量，不读取正式 PDF。
`smoke_ollama_api` 在独立临时目录上传合成 PDF，走完整问答接口并检查执行日志；
不会占用或重建正式 Qdrant 索引。
本机实测 `qwen3:4b` thinking 版会把分析过程混入正文，因此默认选择独立的
`qwen3:4b-instruct` 权重，并保留输出标签清理作为防护。
日志 `/api/logs` 的 `model_call` 事件记录节点、耗时、输入/输出 Token 估算，若提供商
返回真实用量还会记录对应计数；不会记录提示词正文或 API 密钥。确定性测试显式使用
`LLM_PROVIDER=fake`，离线运行时不需要 Ollama。V3-3 才会把查询分析 Schema 接入实际编排。

## 最近一次验证

V3-4 已在隔离重建的真实样例 PDF 索引中完成四题 4/4 回答验收。

## V3-5：模型成本与质量闸门

- 简单问题默认最多调用本地模型 2 次，复杂/多问题最多 4 次；查询分析、重写、压缩和最终回答各有独立上限。达到上限时，只展示已检索的原文和来源，或者明确说明证据不足，不再调用模型补写答案。
- `/api/chat/stream` 的 `usage` 事件和 `rag.usage` 结构化日志记录输入、输出、总 Token，实际值优先，缺失时标明估算；还记录模型调用次数、缓存命中和耗时。不记录提示词、私有推理或密钥。
- 查询分析和检索重写使用线程、问题、索引版本等作为缓存键；检索结果缓存随索引清单版本变化失效，内存缓存默认 5 分钟、最多 256 条。答案缓存未启用，避免旧证据被重复引用。
- 可在 `backend/.env` 中按 `.env.example` 调整 `MAX_LLM_CALLS_PER_REQUEST`、`MAX_SIMPLE_LLM_CALLS`、各节点上限、`MAX_CONTEXT_TOKENS` 和缓存参数。Ollama 模式不会向云端模型发起请求。
- 统一回归命令：`python -m scripts.smoke_v3_5_regression`，包含四道真实 PDF 问题、无证据、追问、多事实和冲突证据，全部在临时数据目录运行，不修改正式知识库索引。运行前须启动 Ollama 并准备已配置的模型。

正式库若还在使用旧索引，请先参照 V3-1 的预览和备份重建步骤，再检验你自己的 PDF。
