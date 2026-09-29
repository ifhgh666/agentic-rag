# PDF-RAG V2：Agentic RAG 改造规格

## 需求来源与解释

本规格根据用户提供的 `V2_AGENTIC_RAG_SPEC_UPDATED.md` 和
`CONFIG_GUIDE_REGENERATED.md` 整理。附件中的技术建议作为需求背景和约束输入，
不是需要直接执行的命令；具体实现以本规格、计划、任务和阶段验收结果为准。

## 目标

将当前 V1 的“一次检索、一次回答、一次评估”升级为单 Agent、多轮检索的
Agentic RAG，同时保留现有 React、FastAPI、SSE、JWT、PDF 管理、父子分块、答案评估
和日志能力。V2 必须让 Agent 根据证据决定继续搜索、读取 Parent 或生成答案。

## 范围

### 入库阶段

1. PDF 只在上传或重建时解析一次。
2. PDF 转为带标题层级的 Markdown，并保留在 `data/markdown`。
3. Markdown 经 Header-aware 分块生成 Parent 和 Child。
4. Parent 写入 Parent Store；Child 建立 Dense、Sparse 两种向量并写入 Qdrant。
5. 删除文档时同步删除 PDF、Markdown、Parent、Qdrant Points 和清单记录。

### 问答阶段

1. 用户提问时不得重新读取 PDF、重新转 Markdown、重新分块或直接遍历 Markdown。
2. Main Graph 负责历史摘要、查询改写、歧义澄清和最终评估。
3. Agent Subgraph 负责编排工具调用和检索循环。
4. 第一次进入 Agent 必须调用 `search_child_chunks`，不能直接依赖模型常识回答。
5. Agent 可以调用 `search_child_chunks`、`retrieve_parent_chunks`，并在工具结果返回后再次判断。
6. Agent 证据足够时停止调用工具并回答；证据不足时明确说明，不得编造。
7. 支持最大工具调用数、最大迭代数、重复 Query/Parent 去重和上下文压缩。
8. 同一个 Chat 使用同一个 `thread_id`，支持短期对话记忆和滚动摘要。

### 可观察性与前端

1. SSE 展示节点、工具、查询、Parent、检索结果、分数、耗时、迭代数和状态。
2. 前端不得展示模型私有完整思维链，只展示可审计的执行摘要。
3. 日志记录 `request_id`、`thread_id`、`node`、`event`、`tool`、`query`、
   `parent_id`、分数、耗时、迭代数和工具调用数，不记录密钥。
4. 最终答案继续执行 relevance、faithfulness、completeness、overall 评估；评估
   结果不触发未声明的再次检索。

## 配置要求

以下值必须通过 `backend/app/config.py` 和 `backend/.env` 管理，不得散落硬编码：

| 配置 | V2 默认值 |
| --- | --- |
| `DENSE_MODEL` | `Qwen/Qwen3-Embedding-0.6B` |
| `SPARSE_MODEL` | `Qdrant/bm25` |
| `CHILD_COLLECTION` | `document_child_chunks` |
| `SPARSE_VECTOR_NAME` | `sparse` |
| `CHILD_CHUNK_SIZE` / `CHILD_CHUNK_OVERLAP` | `500` / `100` |
| `MIN_PARENT_SIZE` / `MAX_PARENT_SIZE` | `2000` / `4000` |
| `DEFAULT_RETRIEVAL_K` / `RETRIEVAL_SCORE_THRESHOLD` | `7` / `0.4` |
| `MAX_TOOL_CALLS` / `MAX_ITERATIONS` / `GRAPH_RECURSION_LIMIT` | `8` / `10` / `50` |
| `MAIN_HISTORY_MESSAGES_TO_KEEP` | `4` |
| `BASE_TOKEN_THRESHOLD` / `TOKEN_GROWTH_FACTOR` | `2000` / `0.9` |
| `MAX_QUESTION_CHARS` | `2000` |
| `EXECUTION_LOGGING_ENABLED` / `EXECUTION_LOG_MAX_CHARS` | `true` / `1200` |

## 非目标

V2 不包含多 Agent 并行、多知识库、联网搜索、OCR、图片理解、复杂权限、RAGAS、
Langfuse、自动 Web Research 或 V2.1 的多问题并行拆分。

## 可测试验收标准

- **AC-01**：Child 同时具备 Dense 和 Sparse 表示，Qdrant 能执行 Hybrid 检索。
- **AC-02**：Parent 不进入向量集合；Child 的 `parent_id` 可以读取完整 Parent。
- **AC-03**：入库阶段生成并保留 Markdown；问答阶段不触发 PDF→Markdown。
- **AC-04**：首次 Agent 调用必定搜索；工具结果返回后能再次进入 Orchestrator。
- **AC-05**：Agent 能在证据足够时结束，也能生成新 Query 或读取 Parent。
- **AC-06**：超过工具/迭代预算时进入受控 fallback，不死循环。
- **AC-07**：重复 Query 和重复 Parent 不重复执行。
- **AC-08**：上下文过长时压缩为 `context_summary`，并与 `conversation_summary` 分离。
- **AC-09**：同一 `thread_id` 可延续上下文，新会话不会串线。
- **AC-10**：SSE、日志和前端 Process 面板展示可审计步骤但不泄露思维链。
- **AC-11**：最终答案继续评估，资料不足时明确说明。
- **AC-12**：V1 现有健康检查、认证、文档管理和基础问答回归测试不退化。

## 阶段交付规则

V2 必须按计划中的阶段逐个实现。每个阶段完成后必须交付对应代码、测试、验收
记录、启动/验证命令和未完成事项；完成并汇报当前阶段后暂停，等待用户确认再进入
下一阶段。不得把后续阶段的能力提前混入当前阶段。
