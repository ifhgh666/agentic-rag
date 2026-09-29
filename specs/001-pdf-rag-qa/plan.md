# 实现计划：PDF RAG 知识库问答

**分支**：`001-pdf-rag-qa` | **日期**：2026-09-22 | **规格说明**：[spec.md](spec.md)

**输入**：`specs/001-pdf-rag-qa/spec.md` 中的功能规格，以及 `PROJECT_SPEC.md`
中的项目要求。

## 摘要

构建一个本地优先的全栈应用：上传文本型 PDF，提取并切分为父子单元，使用
FAISS 为子级单元建立索引，检索证据，通过 OpenAI 兼容模型生成基于上下文的答案，
评估答案质量，并将每个流水线阶段实时推送给已认证管理员。V1 使用文件存储元数据
和 JSONL 日志，保持实现简单、可检查，同时通过适配器隔离解析、嵌入、生成和评估
模块与 API、界面之间的耦合。

## 技术背景

**语言/版本**：后端使用 Python 3.11+；前端使用 TypeScript 5.x 和 Node.js 20+

**主要依赖**：FastAPI、Pydantic、Uvicorn、PyMuPDF、LangChain 文本分割器、
sentence-transformers、FAISS CPU（不可用时使用 NumPy 降级）、OpenAI 兼容 Python 客户端、PyJWT、pwdlib、
python-multipart、python-dotenv；前端使用 React、Vite、Axios、自定义 CSS、
React Router，以及 SSE 客户端或原生 `EventSource` 兼容封装

**存储**：`backend/data/` 下的原始 PDF、提取 Markdown、父子 JSON 元数据、带有
有序元数据侧车文件的 FAISS 索引和追加式 JSONL 日志；凭据和密钥使用环境变量

**测试**：后端使用 pytest、FastAPI TestClient/httpx 以及假的模型提供商适配器，
覆盖单元、契约和集成测试；前端执行 TypeScript/构建检查，并在可行处增加组件测试；
使用快速开始流程验证端到端行为

**目标平台**：以 Windows 本地开发为主，同时保持 Python/Node 环境的可移植性；
运行一个后端进程和一个浏览器前端

**项目类型**：全栈 Web 应用

**性能目标**：在支持的本地环境中，5 分钟内处理最多 100 页的文本型 PDF；在慢速
处理开始前先发出第一条问题进度事件；默认最多返回 5 条保留的子级匹配；将答案
上下文限制为 12,000 个字符

**约束**：V1 只支持单管理员、单知识库、单轮问题、文本型 PDF；不支持 OCR、联网
搜索、多轮记忆、多代理/检索循环、外部数据库或源码中的密钥；失败上传或模型操作
不能破坏其他 ready 文档

**规模/范围**：小型本地知识库，每个文档约 100 页，单管理员，四个界面区域
（登录、聊天、知识库、日志），以及 `PROJECT_SPEC.md` 规定的七个实现阶段

## 项目宪章检查

*门禁：在第 0 阶段研究前必须通过；第 1 阶段设计后重新检查。*

| 原则 | 研究前门禁 | 设计后复核 | 证据 |
|---|---|---|---|
| 阶段边界交付 | 通过 | 通过 | 工作按项目阶段从骨架、PDF 管理到 RAG、评估、SSE 和日志排序；后续功能保持在范围外 |
| RAG 模块单一职责 | 通过 | 通过 | 解析器、分块器、嵌入器、向量存储、检索器、上下文构建器、生成器、评估器和流水线均有独立适配器/服务 |
| 基于证据回答 | 通过 | 通过 | 检索结果会过滤并排序；上下文有上限且标注来源；证据不足时明确说明 |
| 安全且一致的数据处理 | 通过 | 通过 | JWT 和密码哈希来自环境配置；存储路径由 ID 生成；删除后重建派生索引 |
| 可观察且可验证的行为 | 通过 | 通过 | 有类型的 SSE 阶段事件、关联 JSONL 日志、健康/检索接口和针对性测试 |

不需要申请宪章例外。

## 项目结构

### 本功能的文档

```text
specs/001-pdf-rag-qa/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── tasks.md
```

### 源代码（仓库根目录）

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   ├── chat.py
│   │   └── logs.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── knowledge.py
│   │   ├── chat.py
│   │   ├── debug.py
│   │   └── logs.py
│   ├── auth/
│   │   ├── service.py
│   │   └── security.py
│   ├── knowledge/
│   │   ├── models.py
│   │   ├── manager.py
│   │   ├── pdf_parser.py
│   │   ├── chunker.py
│   │   └── stores.py
│   ├── rag/
│   │   ├── embeddings.py
│   │   ├── index_store.py
│   │   ├── retriever.py
│   │   ├── context_builder.py
│   │   ├── generator.py
│   │   ├── evaluator.py
│   │   └── pipeline.py
│   └── observability/
│       ├── events.py
│       └── logger.py
├── tests/
│   ├── unit/
│   ├── contract/
│   └── integration/
├── data/
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── api/
│   ├── auth/
│   ├── components/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Chat.tsx
│   │   ├── Knowledge.tsx
│   │   └── Logs.tsx
│   ├── types/
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
└── tsconfig.json
```

**结构选择**：采用前后端分离的 Web 应用结构。`backend/app` 负责领域流水线和
受保护 API；`frontend/src` 负责四个界面和展示状态。后端测试按单元、契约、集成
范围分组，使每个用户故事都有独立验证入口。`backend/data` 是运行时数据，除安全
测试夹具外必须加入版本控制忽略列表。

## 实现阶段

任务清单将项目阶段映射到可独立测试的用户故事：

1. **项目骨架和基础设施**：FastAPI/Vite 启动、配置、认证中间件、错误处理、日志、
   公共模型和测试夹具。
2. **PDF 管理**：受保护的上传/列表/删除接口和文档状态界面。
3. **解析和分块**：文本提取、父子元数据和数量统计。
4. **嵌入和检索**：嵌入适配器、FAISS 侧车文件、阈值 top-k 检索、去重和诊断接口。
5. **答案生成**：有上限的上下文、标注来源的答案、证据不足处理和聊天界面。
6. **评估**：结构化质量评估和分数卡片。
7. **SSE 和日志**：带关联 ID 的进度流、过程面板、日志接口/过滤界面、端到端可观测性。

## 设计说明

- 依赖注入使假的解析器、嵌入器、生成器和评估器可以用于测试，而不需要下载模型
  或调用真实服务。
- 向量索引由 ready 子级记录派生。删除或修复操作根据剩余记录重建索引，并在开放
  搜索前验证侧车文件与向量对齐。
- 流水线负责创建唯一 `request_id` 并按顺序发送阶段事件。API 处理器只负责把领域
  失败转换为稳定的错误契约，不实现 RAG 逻辑。
- 所有界面明确展示加载中、空数据、失败和成功状态。聊天界面将来源证据和评估结果
  绑定到同一个已完成请求。

## 复杂度记录

没有违反宪章。前后端拆分和适配器模块是模块职责与可观测性原则要求的结构，仍然
属于一个可本地部署的应用，而不是多个产品。

## 实现复核

当前实现已完成 V1 的本地验收路径：认证、PDF 上传/解析/删除、父子分块、检索、
有依据回答、SSE 阶段、答案评估和日志过滤。真实嵌入模型与 OpenAI 兼容模型需要
在 `backend/.env` 中配置；未配置时使用确定性的本地嵌入和开发答案生成器。OCR、
联网搜索、多轮记忆和多管理员仍按产品边界延后。
