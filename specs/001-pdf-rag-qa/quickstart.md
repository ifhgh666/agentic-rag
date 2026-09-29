# 快速开始：PDF RAG 知识库问答

本快速开始面向 Windows 本地开发环境。后端和前端分别运行，通过后端的文件存储
目录共享知识库状态。

## 前置条件

- Python 3.11 或更高版本
- Node.js 20 或更高版本以及 npm
- 一个用于验收测试的文本型 PDF
- 一个 OpenAI 兼容模型接口和嵌入模型配置；如果启用了明确的开发适配器，则本地
  冒烟测试可以不配置真实模型

## 配置

在仓库根目录执行：

```powershell
Copy-Item backend/.env.example backend/.env
```

在 `backend/.env` 中至少设置以下内容：

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<password-hash>
JWT_SECRET=<random-development-secret>
LLM_BASE_URL=<openai-compatible-base-url>
LLM_API_KEY=<provider-key>
LLM_MODEL=<chat-model>
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
```

密码必须以哈希形式保存，不能把明文密码提交到源码。应用启动时会创建
`backend/data/`，用于保存 PDF、Markdown、元数据、FAISS 文件和 JSONL 日志。

## 启动后端

```powershell
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

检查服务是否启动：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

预期状态为 `ok`。在文档处理完成前，健康响应中的 `index_ready` 可能为 `false`。

## 启动前端

在第二个终端执行：

```powershell
Set-Location frontend
npm install
npm run dev
```

打开终端显示的 Vite 地址，通常是 `http://localhost:5173`。

## 首次验收流程

1. 使用配置好的管理员账号登录。
2. 打开知识库，上传文本型 PDF，等待状态变为 `ready`，并确认父级和子级数量均大于 0。
3. 打开聊天界面，提交一个答案确实存在于 PDF 中的问题。
4. 确认过程面板展示全部八个流水线阶段、按顺序排列的检索证据、来源文件名/章节、
   答案和 0–100 评估分数。
5. 复制显示的 `request_id`，打开日志界面并按该 ID 过滤，确认整条流水线可追踪。
6. 删除 PDF，等待操作完成，再次提问并确认不会检索到该文件的内容。

## API 冒烟检查

登录后，把返回的 Bearer 令牌用于受保护接口：

```powershell
$token = '<access-token>'
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Headers $headers -Uri http://127.0.0.1:8000/api/knowledge/documents
Invoke-RestMethod -Headers $headers -Method Post `
  -ContentType 'application/json' `
  -Body '{"query":"保存期限是多久？"}' `
  -Uri http://127.0.0.1:8000/api/debug/retrieve
```

多部分上传和 SSE 聊天以浏览器界面为支持路径。后端测试使用假的嵌入器和生成器，
因此单元测试与契约测试不需要真实服务密钥或下载模型。

## 验证命令

在仓库根目录执行：

```powershell
Set-Location backend
python -m pytest
Set-Location ..\frontend
npm run build
```

当测试通过、前端构建成功、健康检查可用，并且首次验收流程完成，同时日志和 API
响应中没有出现模型密钥时，即可进行本地演示。
