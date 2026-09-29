---

description: "PDF RAG 知识库问答功能的实现任务"
---

# 任务：PDF RAG 知识库问答

**输入**：`specs/001-pdf-rag-qa/` 中的设计文档

**前置文档**：`plan.md`、`spec.md`、`research.md`、`data-model.md`、
`contracts/api.md` 和 `quickstart.md`

**测试**：由于规格说明定义了独立验收测试，且项目宪章要求行为可观察、可验证，
因此任务中包含测试。

**组织方式**：任务按用户故事分组。三个 P1 用户故事构成 MVP；P2 用户故事补充
可观测性、评估和可追踪能力。

## 格式说明

- `[P]` 表示任务可以和相邻任务并行执行，因为它只涉及不同文件且没有未完成依赖。
- `[US1]` 至 `[US6]` 表示任务所属的用户故事。
- 每个任务都包含连续编号，并写明要创建或修改的具体文件路径。

## 阶段 1：项目初始化（共享基础设施）

**目的**：创建前后端应用骨架和开发工具。

- [x] T001 按 `specs/001-pdf-rag-qa/plan.md` 创建 `backend/app/` 后端包目录和 `backend/tests/` 测试目录。
- [x] T002 [P] 在 `backend/requirements.txt` 和 `backend/.env.example` 中创建后端依赖清单和环境变量模板。
- [x] T003 [P] 在 `frontend/package.json`、`frontend/tsconfig.json`、`frontend/vite.config.ts` 和 `frontend/src/main.tsx` 中创建 Vite/React TypeScript 外壳。
- [x] T004 [P] 在 `.gitignore` 中忽略 `backend/.env`、`backend/data/`、Python 缓存、Node 模块和构建产物。
- [x] T005 [P] 在 `backend/README.md` 和 `frontend/README.md` 中补充本地运行命令和最小使用说明。

**检查点**：两个项目都有可安装的依赖清单和入口目录，源码中没有密钥或运行时数据。

## 阶段 2：基础设施（阻塞性前置条件）

**目的**：实现共享配置、数据模型、安全、错误处理、日志和应用装配。本阶段完成
前不得开始任何用户故事开发。

- [x] T006 在 `backend/app/config.py` 中实现环境配置、路径创建、默认检索限制和模型提供商配置。
- [x] T007 [P] 在 `backend/app/schemas/errors.py` 和 `backend/app/api/errors.py` 中实现共享错误码、脱敏 API 错误结构和异常处理器。
- [x] T008 [P] 在 `backend/app/schemas/common.py` 中实现通用 ID、时间戳、分页和校验辅助方法。
- [x] T009 在 `backend/app/observability/logger.py` 中实现 JSONL 结构化日志，包括级别、模块、请求 ID、耗时和安全错误详情。
- [x] T010 [P] 在 `backend/app/observability/events.py` 中实现流水线阶段名称、事件状态模型和请求级事件结构。
- [x] T011 在 `backend/app/auth/security.py` 和 `backend/app/auth/service.py` 中实现密码哈希、JWT 创建/验证、Bearer 依赖和单管理员校验。
- [x] T012 [P] 在 `backend/app/schemas/documents.py`、`backend/app/schemas/chat.py` 和 `backend/app/schemas/logs.py` 中实现文档、聊天、检索、评估和日志模型。
- [x] T013 在 `backend/app/dependencies.py` 中实现配置、认证、存储和服务的依赖提供器。
- [x] T014 在 `backend/app/main.py` 中实现 FastAPI 应用、CORS、健康响应、路由注册和启动时索引校验。
- [x] T015 [P] 在 `frontend/src/api/client.ts`、`frontend/src/api/types.ts` 和 `frontend/src/auth/session.ts` 中实现已认证 API 客户端、令牌存储和类型化 API 错误。
- [x] T016 [P] 在 `frontend/src/App.tsx`、`frontend/src/components/ProtectedRoute.tsx` 和 `frontend/src/components/StateView.tsx` 中实现前端路由外壳、受保护路由、导航以及共享的加载/空数据/错误组件。
- [x] T017 [P] 在 `backend/tests/conftest.py` 中增加临时数据根目录、假的管理员配置和 TestClient 测试夹具。
- [x] T018 [P] 在 `frontend/vitest.config.ts` 和 `frontend/src/App.test.tsx` 中增加前端测试/构建配置和冒烟测试入口。

**检查点**：服务可以启动，`/api/health` 能够响应，受保护依赖已经存在，配置不会
从源码读取密钥，测试框架已经可用。

## 阶段 3：用户故事 1——管理员登录（优先级：P1，MVP）

**目标**：使用一个配置中的管理员账号保护文档、聊天、诊断和日志操作，并提供可用的
登录/退出流程。

**独立测试**：有效凭据返回令牌并进入聊天页；无效或缺失凭据得到明确拒绝；退出后
客户端不再具有访问权限。

### 用户故事 1 的测试

- [x] T019 [P] [US1] 在 `backend/tests/contract/test_auth_api.py` 中增加有效登录、无效登录、缺失 Bearer 令牌和退出响应的契约测试。
- [x] T020 [P] [US1] 在 `frontend/src/pages/Login.test.tsx` 和 `frontend/src/auth/session.test.ts` 中增加登录、受保护路由跳转和退出测试。

### 用户故事 1 的实现

- [x] T021 [US1] 在 `backend/app/schemas/auth.py` 中实现登录和退出的请求/响应模型。
- [x] T022 [US1] 在 `backend/app/api/auth.py` 中实现密码哈希校验、JWT 签发、登录接口和退出接口。
- [x] T023 [US1] 在 `backend/app/main.py` 和 `backend/app/dependencies.py` 中为受保护路由应用 Bearer 身份认证。
- [x] T024 [US1] 在 `frontend/src/pages/Login.tsx` 中实现登录页、凭据校验、加载状态和可读错误状态。
- [x] T025 [US1] 在 `frontend/src/components/AppLayout.tsx` 和 `frontend/src/App.tsx` 中实现受保护导航和退出操作。

**检查点**：用户故事 1 可以独立通过；没有认证的管理员不能通过界面或 API 打开四个
受保护区域。

## 阶段 4：用户故事 2——管理员管理 PDF 知识文档（优先级：P1，MVP）

**目标**：上传、解析、分块、列表展示和删除文本型 PDF；某次操作失败时不能破坏其他
ready 文档。

**独立测试**：上传文本 PDF，观察状态从 `processing` 变为 `ready`，确认父子数量为正数，
查看元数据，删除文档，并验证之后不能检索到它。

### 用户故事 2 的测试

- [x] T026 [P] [US2] 在 `backend/tests/unit/test_pdf_parser.py` 中增加有效文本 PDF、非 PDF、空文件、损坏 PDF 和无文本 PDF 的解析测试。
- [x] T027 [P] [US2] 在 `backend/tests/unit/test_chunker.py` 中增加父子关联、章节元数据、尺寸限制和空内容拒绝测试。
- [x] T028 [P] [US2] 在 `backend/tests/contract/test_knowledge_api.py` 中增加多部分上传、状态列表、失败原因、重名文件和认证删除的文档接口契约测试。
- [x] T029 [P] [US2] 在 `backend/tests/integration/test_document_lifecycle.py` 中增加上传到 ready 再到删除的集成测试，并验证无关 ready 文档保持可用。

### 用户故事 2 的实现

- [x] T030 [P] [US2] 在 `backend/app/knowledge/models.py` 中定义文档、父级、子级和处理状态模型及序列化方法。
- [x] T031 [US2] 在 `backend/app/knowledge/manager.py` 和 `backend/app/knowledge/stores.py` 中实现安全上传存储、元数据持久化、状态转换和删除协调。
- [x] T032 [US2] 在 `backend/app/knowledge/pdf_parser.py` 中实现带页码元数据的文本提取和用户可读失败原因。
- [x] T033 [US2] 在 `backend/app/knowledge/chunker.py` 中实现按标题创建父级内容，并使用有上限的递归方法切分子级内容。
- [x] T034 [US2] 在 `backend/app/api/knowledge.py` 中实现认证文档列表、多部分上传和删除接口。
- [x] T035 [US2] 在 `frontend/src/pages/Knowledge.tsx` 中实现知识库上传表单、文档表格、处理状态、数量、删除确认以及全部加载/空数据/错误状态。
- [x] T036 [US2] 在 `frontend/src/api/knowledge.ts` 中增加类型化文档 API 方法和上传进度处理。

**检查点**：用户故事 1 和 2 可以联动运行；失败文档可见且带原因，ready 文档保持可用，
删除操作清除所有文档派生文件。

## 阶段 5：用户故事 3——管理员提出知识库问答（优先级：P1，MVP）

**目标**：从 ready 文档中检索证据，生成带来源的答案，或明确返回知识不足。

**独立测试**：有一个 ready PDF 时，支持的问题返回答案和来源；不支持的问题不生成虚假
来源；知识库为空时提示先上传文档。

### 用户故事 3 的测试

- [x] T037 [P] [US3] 在 `backend/tests/unit/test_embeddings.py` 中使用假的模型增加嵌入适配器、归一化向量形状和提供商失败测试。
- [x] T038 [P] [US3] 在 `backend/tests/unit/test_index_store.py` 中增加 FAISS/索引存储的侧车对齐、top-k 排序、阈值过滤、重建和删除隔离测试。
- [x] T039 [P] [US3] 在 `backend/tests/unit/test_retriever.py` 和 `backend/tests/unit/test_context_builder.py` 中增加父级去重、来源标注和 12,000 字符上限测试。
- [x] T040 [P] [US3] 在 `backend/tests/unit/test_generator.py` 中增加只使用上下文的提示词、证据不足、提供商错误和来源保留测试。
- [x] T041 [P] [US3] 在 `backend/tests/contract/test_rag_api.py` 中增加检索诊断和聊天契约测试。
- [x] T042 [P] [US3] 在 `backend/tests/integration/test_question_answering.py` 中使用假的嵌入器/生成器增加端到端问答测试。

### 用户故事 3 的实现

- [x] T043 [P] [US3] 在 `backend/app/rag/embeddings.py` 中实现延迟加载嵌入模型和可注入的归一化嵌入接口。
- [x] T044 [US3] 在 `backend/app/rag/index_store.py` 中实现 FAISS 索引持久化、有序子级元数据侧车文件、原子重建和对齐校验。
- [x] T045 [US3] 在 `backend/app/rag/retriever.py` 中实现带阈值的 top-k 子级检索和父级去重。
- [x] T046 [US3] 在 `backend/app/rag/context_builder.py` 中实现有长度上限、带来源标注的上下文组装。
- [x] T047 [US3] 在 `backend/app/rag/generator.py` 中实现 OpenAI 兼容的只使用上下文答案生成和明确的证据不足处理。
- [x] T048 [US3] 在 `backend/app/api/debug.py` 中连接文档 ready 状态与索引重建，并实现检索诊断接口。
- [x] T049 [US3] 在 `backend/app/api/chat.py` 和 `backend/app/schemas/chat.py` 中实现单轮聊天服务、请求模型以及供流式适配器使用的非流式领域结果。
- [x] T050 [US3] 在 `frontend/src/pages/Chat.tsx` 中实现聊天问题表单、答案面板、来源列表、无证据提示和界面错误状态。
- [x] T051 [US3] 在 `frontend/src/api/chat.ts` 中增加类型化检索/诊断 API 方法和答案/来源状态处理。

**检查点**：MVP 可以上传 PDF、检索证据、回答有依据的问题，并明确拒绝没有证据的
问题，不启动第二次检索循环。

## 阶段 6：用户故事 4——管理员观察一次 RAG 执行（优先级：P2）

**目标**：在最终答案返回前及返回过程中，流式展示八个主要流水线阶段、耗时和检索详情。

**独立测试**：问题完成前先收到 received 事件；成功后显示全部八个阶段；保留的子级匹配
展示分数、来源、父级 ID 和内容预览。

### 用户故事 4 的测试

- [x] T052 [P] [US4] 在 `backend/tests/unit/test_pipeline_events.py` 中增加事件顺序、耗时、阶段失败和单请求 ID 测试。
- [x] T053 [P] [US4] 在 `backend/tests/contract/test_chat_stream_api.py` 中增加 received、step、retrieval、answer、error 和 complete 事件的 SSE 契约测试。
- [x] T054 [P] [US4] 在 `frontend/src/components/ProcessPanel.test.tsx` 和 `frontend/src/api/sse.test.ts` 中增加前端流解析和过程面板渲染测试。

### 用户故事 4 的实现

- [x] T055 [US4] 在 `backend/app/rag/pipeline.py` 中实现请求级 RAG 流水线编排、阶段计时、检索载荷和最终状态。
- [x] T056 [US4] 在 `backend/app/api/chat.py` 中实现 SSE 序列化、断开连接清理和受保护的 `/api/chat/stream` 接口。
- [x] T057 [US4] 在 `frontend/src/api/sse.ts` 和 `frontend/src/components/ProcessPanel.tsx` 中实现前端 SSE 客户端、请求 ID 跟踪、阶段时间线、耗时显示和检索详情展开。
- [x] T058 [US4] 在 `frontend/src/pages/Chat.tsx` 中把过程面板接入聊天界面，并保留已完成请求的证据。

**检查点**：一次完整问题可以从收到请求到生成答案全程检查；索引或模型提供商失败时，
界面显示带有关联 ID 的最终错误。

## 阶段 7：用户故事 5——管理员查看答案质量（优先级：P2）

**目标**：评估每个生成答案并展示相关性、忠实性、完整性、总体分数和原因，不因为低分
启动新的检索循环。

**独立测试**：完成的答案展示四个 0–100 分数和可读原因；低分会被展示但不会触发新搜索。

### 用户故事 5 的测试

- [x] T059 [P] [US5] 在 `backend/tests/unit/test_evaluator.py` 中增加结构化分数、范围校验、原因保留和模型输出错误测试。
- [x] T060 [P] [US5] 在 `backend/tests/contract/test_evaluation_api.py` 中增加评估事件/响应契约测试。
- [x] T061 [P] [US5] 在 `frontend/src/components/ScoreCard.test.tsx` 中增加高分、低分和评估失败状态的分数卡片渲染测试。

### 用户故事 5 的实现

- [x] T062 [US5] 在 `backend/app/rag/evaluator.py` 中实现相关性、忠实性、完整性、总体分数和原因的结构化评估适配器。
- [x] T063 [US5] 在 `backend/app/rag/pipeline.py` 中将评估作为最终阶段加入流水线，明确禁止重试/检索循环。
- [x] T064 [US5] 在 `frontend/src/components/ScoreCard.tsx` 和 `frontend/src/pages/Chat.tsx` 中实现类型化评估事件处理和分数展示。

**检查点**：质量评估显示在同一个请求中，并且只是对答案的只读评价。

## 阶段 8：用户故事 6——管理员追踪系统活动（优先级：P2）

**目标**：在结构化日志中关联问题的所有阶段，并支持按级别、模块、请求 ID 和数量过滤。

**独立测试**：复制完成请求的 ID，在日志界面按该 ID 过滤，查看包含时间、模块、消息和
安全错误详情的流水线记录。

### 用户故事 6 的测试

- [x] T065 [P] [US6] 在 `backend/tests/unit/test_logger.py` 中增加 JSONL 日志和请求关联测试。
- [x] T066 [P] [US6] 在 `backend/tests/contract/test_logs_api.py` 中增加级别、模块、请求 ID、数量、无效过滤条件和认证测试。
- [x] T067 [P] [US6] 在 `backend/tests/integration/test_request_trace.py` 中增加从请求到日志的完整链路集成测试。
- [x] T068 [P] [US6] 在 `frontend/src/pages/Logs.test.tsx` 中增加日志过滤、表格、空数据和错误状态渲染测试。

### 用户故事 6 的实现

- [x] T069 [US6] 在 `backend/app/observability/logger.py` 中实现日志读取和级别/模块/请求 ID/数量过滤校验。
- [x] T070 [US6] 在 `backend/app/api/logs.py` 和 `backend/app/schemas/logs.py` 中实现认证日志接口和响应模型。
- [x] T071 [US6] 在 `frontend/src/api/logs.ts` 中增加日志查询方法和请求 ID 传递。
- [x] T072 [US6] 在 `frontend/src/pages/Logs.tsx` 中实现日志过滤器、表格、时间戳、错误详情以及加载/空数据/失败状态。

**检查点**：每个完成请求都能通过一个 ID 从第一条流水线事件追踪到评估结果，并且
可以排除无关日志。

## 阶段 9：收尾和跨领域工作

**目的**：在不扩大 V1 范围的前提下，验证完整流程并补齐可靠性、安全性和可用性问题。

- [x] T073 [P] 在 `backend/tests/security/test_boundaries.py` 中增加路径穿越、超大输入、响应/日志泄露密钥和过期索引预防的回归测试。
- [x] T074 [P] 在 `frontend/src/styles/app.css` 和 `frontend/src/components/StateView.tsx` 中补充响应式布局、统一错误文案和空状态样式。
- [x] T075 [P] 在 `backend/tests/fixtures/sample.pdf` 和 `backend/tests/fakes/providers.py` 中增加安全的示例 PDF 和可重复的模型提供商假实现。
- [x] T076 执行后端单元/契约/集成测试，并将结果记录在 `backend/README.md`。
- [x] T077 执行前端构建和测试命令，并将结果记录在 `frontend/README.md`。
- [x] T078 按 `specs/001-pdf-rag-qa/quickstart.md` 验证所有命令和验收场景，包括删除隔离和请求 ID 日志追踪。
- [x] T079 对照 FR-001 至 FR-028 和项目宪章复核实现，并将延后事项记录在 `specs/001-pdf-rag-qa/plan.md`。

## 依赖关系和执行顺序

### 阶段依赖

- **初始化阶段（阶段 1）**：无依赖；T001 建立目录树后，T002–T005 可以并行。
- **基础设施阶段（阶段 2）**：依赖初始化阶段；T006–T018 阻塞所有用户故事。
- **US1（阶段 3）**：依赖基础设施，是所有受保护用户故事验收测试的认证前置条件。
- **US2（阶段 4）**：依赖 US1 的受保护 API 验证；其解析和分块是 US3 检索部分的前置条件。
- **US3（阶段 5）**：依赖 US2 生成的 ready 父子数据和文档生命周期。
- **US4（阶段 6）**：依赖 US3 的领域流水线和答案结果。
- **US5（阶段 7）**：依赖 US4 的请求级流水线和答案事件。
- **US6（阶段 8）**：依赖 US4/US5 的阶段日志和评估日志。
- **收尾阶段（阶段 9）**：依赖需要交付的所有用户故事；T073–T075 在相关模块存在后可以并行。

### 用户故事依赖

- **US1（P1）**：只依赖基础设施，独立交付身份认证。
- **US2（P1）**：使用 US1 的认证，独立交付文档管理。
- **US3（P1）**：使用 US1 和 US2 的数据，独立交付有依据的问答。
- **US4（P2）**：使用 US3 的流水线，增加进度展示但不改变检索规则。
- **US5（P2）**：使用 US4 的请求流程，增加评估但不增加重试循环。
- **US6（P2）**：使用流水线和评估事件，增加可查询的执行追踪。

### 并行机会

- T001 完成后，初始化任务 T002–T005 可以并行。
- 基础设施阶段中，公共模型、可观测性、前端外壳和测试夹具任务可以在不修改同一
  文件的前提下并行。
- 每个用户故事中，标记 `[P]` 的独立测试可以先并行编写，然后再开始实现任务。
- 基础事件契约确定后，US4 的过程面板和 US5 的分数卡片可以分别由后端/前端开发者并行完成。

## 实现策略

### 先完成 MVP

1. 完成初始化和基础设施阶段。
2. 完成 US1，并独立验证身份认证。
3. 完成 US2，并独立验证 PDF 生命周期。
4. 完成 US3，并验证有依据的答案和证据不足处理。
5. 在加入 P2 可观测性功能前暂停，先进行 MVP 演示。

### 增量交付

1. 增加 US4，使一次 RAG 执行可以被观察。
2. 增加 US5，使答案质量可见。
3. 增加 US6，使执行链路可以检索。
4. 按快速开始文档和全部验收场景执行阶段 9 验证。

### 任务完成规则

- 每个用户故事先编写针对性测试，并确认缺少该行为时测试失败，再开始实现。
- 所有模型提供商调用必须位于可注入适配器之后，保证验收测试在本地、可重复运行。
- 文档只有在父子产物和派生索引一致后才能标记为 ready。
- 请求只有在使用同一个 `request_id` 发出最终答案/评估或最终错误后才能标记完成。
