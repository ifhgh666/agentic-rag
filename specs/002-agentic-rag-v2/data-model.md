# V2 数据模型

## 1. Document

现有文档实体，代表用户上传的 PDF。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `document_id` | string | 全局唯一，所有派生文件和 Qdrant Payload 使用它关联 |
| `filename` | string | 原始文件名，展示用，禁止用于路径拼接 |
| `source_path` | path | 服务端内部路径，不通过公开 API 返回 |
| `status` | enum | `uploaded`、`processing`、`ready`、`failed`、`deleted` |
| `created_at` | datetime | 必填 |
| `error` | string/null | 处理失败时的脱敏错误信息 |

## 2. MarkdownArtifact

入库阶段由 PDF 生成的中间结构化文件。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `document_id` | string | 唯一关联 Document |
| `path` | path | `data/markdown/{document_id}.md`，不进入问答实时检索 |
| `parser` | string | `pymupdf4llm` 或兼容实现标识 |
| `content_hash` | string | 用于重建和调试 |
| `page_count` | integer | 大于等于 1 |
| `created_at` | datetime | 必填 |

生命周期：上传/重建时创建，删除文档时删除；问答时只允许作为调试和重建来源。

## 3. ParentChunk

Parent 是完整上下文单元，不进入 Qdrant。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `parent_id` | string | 在文档内唯一，建议 `{document_id}_p{n}` |
| `document_id` | string | 必填 |
| `source` | string | 原始 PDF 名称 |
| `content` | string | 非空，最终由 Parent Store 返回 |
| `page_start` / `page_end` | integer | 页码范围 |
| `headers` | object | `H1`、`H2`、`H3` 标题层级 |
| `char_count` | integer | 用于 Parent size 平衡 |

## 4. ChildChunk 与 Qdrant Point

Child 是精确检索单元，每个 Child 对应一个 Qdrant Point。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `child_id` | string | Qdrant point ID，稳定且可重复构建 |
| `document_id` | string | 用于按文档删除 |
| `parent_id` | string | 用于 Parent Retrieval |
| `content` | string | 非空，写入 payload |
| `source` | string | 原始文件名 |
| `page_start` / `page_end` | integer/null | 来源页码 |
| `headers` | object | `H1`、`H2`、`H3` |
| `dense` | vector | V2-1 起存在 |
| `sparse` | sparse vector | V2-2 起存在，名字固定为 `sparse` |

Qdrant collection 的 payload 至少包含 `document_id`、`source`、`parent_id`、
`page_content`、页码和标题层级。删除使用 `document_id` filter，不重建其他文档。

## 5. MainState

代表一次主图运行状态。

```text
messages: list[Message]
conversation_summary: str
original_query: str
rewritten_query: str
question_is_clear: bool
pending_query: str
final_answer: str
evaluation: object
thread_id: str
```

规则：`conversation_summary` 只记录对话历史，不记录本轮检索证据；`thread_id` 是
会话隔离键。

## 6. AgentState

代表 Agent Subgraph 的研究状态。

```text
messages: list[Message]
question: str
final_answer: str
context_summary: str
context_messages: list[RetrievalResultMessage]
retrieval_keys: set[str]
retrieved_contexts: list[Evidence]
tool_call_count: int
iteration_count: int
```

规则：

- `retrieval_keys` 使用 `search::{normalized_query}` 和 `parent::{parent_id}`，防止重复。
- `retrieved_contexts` 记录当前问题的证据，用于压缩、评估、Debug 和 SSE。
- `context_messages` 为每条检索结果建立一个 `retrieval_result` 记录，包含记录标识、来源、
  内容和 Token 估算，用于按记录计算上下文预算。
- `tool_call_count <= MAX_TOOL_CALLS`，`iteration_count <= MAX_ITERATIONS`。
- `context_summary` 只记录本轮研究结论和缺口，不能替代原始证据元数据。

`RetrievalResultMessage` 至少包含：`role="retrieval_result"`、`record_id`、`source`、
`content` 和 `tokens`；压缩后可以在同一记录上标记 `compressed=true` 并更新内容片段。

## 7. Evidence

工具返回的最小可审计证据。

```text
child_id: string
parent_id: string
document_id: string
source: string
section: object
content: string
score: float
retrieval_mode: "dense" | "hybrid"
```

前端可展示上述字段的摘要；不得携带模型私有 reasoning。

## 8. ExecutionEvent

SSE 和 JSONL 日志共享的最小事件。

```text
request_id: string
thread_id: string
node: string
event: string
tool: string|null
query: string|null
parent_id: string|null
duration_ms: integer|null
iteration: integer|null
tool_call_count: integer|null
details: object
```

`details` 必须经过长度限制和敏感信息过滤。

## 状态关系

```text
Document
  ├── MarkdownArtifact (1)
  ├── ParentChunk (1..N) -> Parent Store
  └── ChildChunk (1..N) -> Qdrant Point
                         └── parent_id -> ParentChunk
```
