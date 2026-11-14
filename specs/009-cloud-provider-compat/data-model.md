# Phase 1 Data Model: 云兼容端点的结构化输出兼容

本功能不引入持久化数据、数据库迁移或索引格式变化。以下“实体”是运行时契约对象与状态取值，用于固定行为与可观测字段。

## E1. 结构化输出模式（StructuredOutputMode）

一次模型调用要求的结构化约束形式。

| 取值 | 含义 | 使用条件 |
|---|---|---|
| `json_schema` | 严格模式：由端点按给定 JSON Schema 约束输出 | 当次调用带 `response_schema` 且端点未拒绝时的首选 |
| `json_object` | 通用模式：端点仅保证返回合法 JSON，字段结构由提示词要求 | 严格模式被端点以“类型不可用”类错误拒绝后的回退 |
| `none` | 未要求结构化输出 | 不带 `response_schema` 的调用（工具循环、终态回答） |

**Validation**: 取值必须来自上表；回退只允许 `json_schema → json_object` 单向发生一次。

## E2. 模型调用尝试（ModelAttempt）

一次逻辑调用下的一次实际请求。

| 字段 | 类型 | 说明 |
|---|---|---|
| `mode` | StructuredOutputMode | 本次尝试使用的结构化模式 |
| `fallback_from` | string \| null | 若本次是回退，记录被拒绝的先前模式 |
| `attempt_index` | 1 或 2 | 同一逻辑调用内的序号 |
| `outcome` | `ok` / `rejected_by_endpoint` / `failed` | 端点拒绝与传输/超时失败分开 |

**Validation**: `attempt_index <= 2`；`attempt_index = 2` 时 `fallback_from` 必须非空。

## E3. 结构化模式记录（随模型轨迹输出）

写入既有模型轨迹与执行事件 `details` 的新增键。

| 键 | 类型 | 说明 |
|---|---|---|
| `structured_mode` | StructuredOutputMode | 该次调用最终生效的模式 |
| `structured_fallback` | boolean | 是否发生回退 |

**Validation**: 不带 `response_schema` 的调用 `structured_mode = none`、`structured_fallback = false`；不得包含提示词正文、密钥或推理内容。

## E4. 失败归类（FailureTaxonomy）

| 情形 | 归类 | 不得归类为 |
|---|---|---|
| 端点在严格与通用模式均拒绝该 `response_format` | 提供商不可用（既有 `model_unavailable` 语义） | 输出非法 |
| 模型返回内容无法通过 schema 校验 | 输出非法（既有 `invalid_model_output` 语义） | 提供商不可用 |
| 整次等待超时 | 超时（既有 `timeout` 语义） | 提供商不可用或输出非法 |
| 远端传输/解压失败 | 提供商不可用 | 输出非法 |

**Validation**: 同一请求的失败原因必须唯一且落在上表左列。

## E5. 既有对象的影响面

| 对象 | 是否变化 | 说明 |
|---|---|---|
| `ModelResult` | 追加两个带默认值字段 | 保持既有构造调用兼容 |
| `ChatProvider` 协议 | 签名不变 | 不新增必需参数 |
| `Settings` | 不变化 | 不新增配置项、不改数值 |
| 索引清单 `manifest.json` | 不变化 | 与嵌入、解析、分块无关 |
| SSE 顶层事件字段 | 不变化 | 只在 `details` 内追加键 |
| 知识库 JSON 与文档目录 | 不变化 | 本功能不读不写业务数据 |
