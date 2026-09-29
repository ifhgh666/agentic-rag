# 数据模型：PDF RAG 知识库问答

## 总览

V1 数据模型由后端负责并采用文件存储。JSON 元数据是文档和分块记录的事实
来源；FAISS 是可以重建的派生产物。除特别说明外，所有标识符均使用不透明 UUID。

## 实体

### 管理员会话

| 字段 | 类型 | 规则 |
|---|---|---|
| `token_subject` | 字符串 | 必须标识配置中的管理员 |
| `issued_at` | 时间 | JWT 签发时间 |
| `expires_at` | 时间 | 必须晚于 `issued_at` |
| `token_id` | 字符串 | 每个签发令牌唯一 |

会话通过签名 JWT 表示，而不是持久化的用户表。配置中的用户名和密码哈希从
环境变量加载。

### 知识文档

| 字段 | 类型 | 规则 |
|---|---|---|
| `document_id` | UUID | 主标识 |
| `filename` | 字符串 | 原始文件名；不区分大小写时必须以 `.pdf` 结尾 |
| `status` | 枚举 | `processing`、`ready` 或 `failed` |
| `size_bytes` | 整数 | 接受的上传文件必须大于 0 |
| `uploaded_at` | 时间 | UTC 时间戳 |
| `processed_at` | 时间或空 | 处理完成时写入 |
| `parent_count` | 整数 | 非负；`ready` 状态必须大于 0 |
| `child_count` | 整数 | 非负；`ready` 状态必须大于 0 |
| `error_reason` | 字符串或空 | `failed` 时必填，`ready` 时为空 |
| `source_path` | 路径 | 私有原始 PDF 路径 |
| `markdown_path` | 路径或空 | 私有提取文本路径 |

重名文件通过不同的文档 ID 分别保存，并在界面上显示为不同记录。存储文件名
不能未经安全的基础名校验直接作为路径使用。

### 父级上下文单元

| 字段 | 类型 | 规则 |
|---|---|---|
| `parent_id` | UUID | 主标识 |
| `document_id` | UUID | 必须引用已存在的文档 |
| `section_title` | 字符串 | 没有标题时允许为空 |
| `page_start` / `page_end` | 整数或空 | 已知时使用包含首尾页的页码范围 |
| `text` | 字符串 | 非空的规范化上下文 |
| `char_count` | 整数 | 必须等于存储文本长度 |
| `ordinal` | 整数 | 文档内稳定顺序 |

### 可检索子级单元

| 字段 | 类型 | 规则 |
|---|---|---|
| `child_id` | UUID | 主标识 |
| `parent_id` | UUID | 只能有一个父级，且父级必须存在 |
| `document_id` | UUID | 冗余保存，用于过滤和审计 |
| `section_title` | 字符串 | 创建时从父级复制 |
| `text` | 字符串 | 非空的可检索文本 |
| `char_count` | 整数 | 必须等于存储文本长度 |
| `ordinal` | 整数 | 父级内稳定顺序 |
| `vector_position` | 整数或空 | 建立索引后对应 FAISS 行号 |

子级元数据侧车文件的顺序必须与 FAISS 向量完全一致。元数据数量和索引数量不
一致时，启动健康检查必须失败，并在搜索前触发重建。

### 检索结果

| 字段 | 类型 | 规则 |
|---|---|---|
| `child_id` | UUID | 必须对应已建立索引的子级 |
| `parent_id` | UUID | 用于加载完整上下文 |
| `document_id` | UUID | 用于返回来源信息 |
| `filename` | 字符串 | 来源文件名快照 |
| `section_title` | 字符串 | 来源章节 |
| `score` | 浮点数 | 相似度分数，响应中降序排列 |
| `content_preview` | 字符串 | 提供给界面的有界预览 |

### 问题请求

| 字段 | 类型 | 规则 |
|---|---|---|
| `request_id` | UUID | 请求收到时创建，所有环节共享 |
| `question` | 字符串 | 必填，并限制输入长度 |
| `created_at` | 时间 | UTC 时间戳 |
| `status` | 枚举 | `received`、`running`、`completed` 或 `failed` |
| `retrieval_results` | 列表 | 按顺序排列的 `RetrievalResult` |
| `sources` | 列表 | 去重后的文档/章节来源 |
| `answer` | 字符串或空 | 生成答案或证据不足回复 |
| `evaluation` | 对象或空 | 评估完成时写入 `EvaluationResult` |

### 流水线阶段事件

| 字段 | 类型 | 规则 |
|---|---|---|
| `request_id` | UUID | 与问题请求相同 |
| `stage` | 枚举 | `query_receipt`、`query_representation`、`child_retrieval`、`score_filtering`、`parent_retrieval`、`context_building`、`answer_generation`、`answer_evaluation` |
| `status` | 枚举 | `started`、`completed` 或 `failed` |
| `sequence` | 整数 | 请求内单调递增 |
| `started_at` | 时间 | UTC 时间戳 |
| `duration_ms` | 整数或空 | 完成或失败时写入 |
| `detail` | 对象或空 | 阶段专用的安全诊断信息 |
| `error` | 字符串或空 | 脱敏后的失败信息 |

### 评估结果

| 字段 | 类型 | 规则 |
|---|---|---|
| `relevance` | 整数 | 0 到 100 |
| `faithfulness` | 整数 | 0 到 100 |
| `completeness` | 整数 | 0 到 100 |
| `overall` | 整数 | 0 到 100 |
| `reason` | 字符串 | 人类可读的解释 |

V1 只展示评估结果；不会因为 `overall` 较低而启动第二次检索循环。

### 系统日志条目

| 字段 | 类型 | 规则 |
|---|---|---|
| `timestamp` | 时间 | UTC，序列化为 ISO 8601 |
| `level` | 枚举 | `DEBUG`、`INFO`、`WARNING` 或 `ERROR` |
| `module` | 字符串 | 稳定的模块名 |
| `request_id` | UUID 或空 | 请求相关日志必须存在 |
| `message` | 字符串 | 人类可读的事件摘要 |
| `duration_ms` | 整数或空 | 可选耗时 |
| `error` | 对象或空 | 类型、消息和安全的错误详情 |

## 关系

```text
KnowledgeDocument 1 ─── * ParentContextUnit 1 ─── * SearchableChildUnit
QuestionRequest   1 ─── * RetrievalResult
QuestionRequest   1 ─── * PipelineStepEvent
QuestionRequest   1 ─── 0..1 EvaluationResult
QuestionRequest   1 ─── * SystemLogEntry（通过 request_id）
```

## 状态转换

### 文档

```text
new -> processing -> ready
                 \-> failed
```

只有 `ready` 文档参与检索。失败上传可以作为新文档重新上传，不得改变其他
ready 文档。删除操作适用于任意状态，并且只有在剩余索引重建完成后才能报告成功。

### 问题请求

```text
received -> running -> completed
                    \-> failed
```

请求收到时发送第一条进度事件；每个请求只发送一次最终 `completed` 或 `failed`。

## 不变量

1. 每个子级必须且只能关联一个已存在的父级和文档。
2. 每个 ready 文档必须拥有正数的父级和子级数量。
3. 每一行 FAISS 向量必须在相同位置对应一条子级元数据。
4. 搜索不得返回属于非 ready 或已删除文档的子级。
5. 问题请求、进度事件、答案、评估结果和日志必须共享一个 `request_id`。
6. 文件路径由生成的 ID 推导，不得直接由用户提供的文件名拼接。

