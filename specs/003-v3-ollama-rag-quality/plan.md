# V3 PDF-RAG 质量修复与 Ollama 接入计划

**状态**：V3-0 至 V3-5 已完成；V3-5 验收后停止，不自动进入新阶段。

**阶段记录**：[V3-0 基线](v3-0-baseline.md) · [V3-1 验收](v3-1-report.md) · [V3-2 验收](v3-2-report.md) · [V3-3 验收](v3-3-report.md) · [V3-4 验收](v3-4-report.md) · [V3-5 验收](v3-5-report.md)

**参考项目**：[GiovanniPasq/agentic-rag-for-dummies](https://github.com/GiovanniPasq/agentic-rag-for-dummies)

**当前项目**：`C:\path\agentic-rag`

## 1. 当前结论

以下第 1 至 3 节记录的是 V3 立项时的基线与差距，不代表 V3-5 完成后的现状；当前验收结果见 [V3-5 报告](v3-5-report.md)。

目前 4 个测试问题只有 1 个回答正确，主要不是前端问题，而是问答链路仍然没有达到参考项目的 Agentic RAG 结构。当前实现的主要风险按优先级排序如下：

1. **最终回答质量不足**：没有模型时，`AnswerGenerator` 直接取上下文第一段；即使配置了云模型，送入模型的上下文仍可能包含多个未排序、未压缩、未核验的 Parent 内容。
2. **默认 Dense 嵌入不是语义模型**：当前 `USE_TRANSFORMER_EMBEDDING=false` 时使用确定性哈希向量，Hybrid 检索虽然存在，但 Dense 召回能力有限。
3. **PDF 转文本过于简单**：当前使用 `PyMuPDF page.get_text("text")`，没有像参考项目那样先转换为结构化 Markdown；表格、标题层级和阅读顺序容易丢失。
4. **Query 改写仍是规则版**：当前只对少量代词做判断，并用固定短语追加检索词，无法理解多意图、技术同义词、上下文引用和复杂问题。
5. **编排器不是模型驱动**：当前 `orchestrator` 使用确定性规则判断“有结果就回答、没结果才换 Query”；它不会像参考项目一样由模型判断证据是否足够、是否需要 Parent、是否需要拆分问题。
6. **评估结果不代表真实正确率**：当前 `AnswerEvaluator` 主要根据字符串是否命中上下文给固定分数，不能证明答案事实正确；参考项目另有 RAGAS 评估流程。

因此，下一阶段不能只把当前 `LLM_BASE_URL` 从云端换成 Ollama。必须先修正“解析 → 分块 → 召回 → 证据选择 → 回答”的质量链路，再接入本地模型。

## 2. 与参考 GitHub 项目的差异

| 能力 | 当前项目 | 参考项目 | 对 4 个问题的影响 |
|---|---|---|---|
| PDF 预处理 | PyMuPDF 纯文本提取，直接分块 | `pymupdf4llm.to_markdown`，保留 Markdown 结构 | 标题、表格和段落关系可能丢失 |
| Parent/Child | 有 Parent/Child，但基于当前纯文本和简单重叠切分 | Markdown 标题分层、Parent 合并/再平衡、Child 500 字符/100 重叠 | 正确事实可能被切断或混入错误上下文 |
| Dense 向量 | 默认确定性哈希向量；Transformer 可选且默认关闭 | `Qwen/Qwen3-Embedding-0.6B` | 中文语义问题和文档表述不一致时召回差 |
| Sparse/Hybrid | Qdrant Dense + Sparse Hybrid 已实现 | Qdrant Dense + BM25 Hybrid | 当前结构接近，但 Dense 质量拖累整体召回 |
| 首次搜索 | 规则强制搜索 | 模型工具调用，并在提示词中强制首步搜索 | 当前能搜索，但不会理解搜索结果质量 |
| Query 改写 | `RuleBasedQueryGenerator` 固定追加 3 类短语 | 结构化 LLM 分析，最多拆成 3 个问题 | 多意图、同义词和追问容易检索错误 |
| 澄清 | 仅根据少量中文代词正则判断 | 模型判断是否清晰，并返回结构化澄清信息 | 新术语、型号和复杂问题可能被误判 |
| 多问题处理 | 单 Agent 单问题链路 | `Send` 并行启动多个 Agent，再聚合答案 | 一个问题包含多个事实时只命中一部分 |
| 自纠错 | 主要只在无结果时换 Query | 模型根据证据不足主动重新搜索或读取 Parent | 有“看似相关但不正确”的结果时不会纠正 |
| 上下文压缩 | 确定性摘要和截断 | 由模型生成研究上下文摘要，并记录已执行查询/Parent | 不能理解哪些事实对当前问题最重要 |
| 最终回答 | 当前有模型时调用一次；无模型时取第一段证据 | Agent 回答后再进行最终聚合 | 当前容易把第一条证据误当成答案 |
| 评估 | 固定规则分数 | 独立 RAGAS 评估 Notebook 和 Judge Model | 当前“高分”不等于事实正确 |
| 运行界面 | FastAPI + React + SSE | Gradio 流式界面 | 界面不是主要差异，后端链路才是重点 |
| 观测 | 本地 JSONL/SSE 执行摘要 | Langfuse 追踪 LLM、工具和 Graph | 当前缺少真实 prompt/completion Token 用量 |

参考项目明确采用分层索引、对话记忆、查询澄清、多 Agent Map-Reduce、自纠错、上下文压缩和 Ollama-first 架构；其 README 也建议工具调用和指令遵循优先使用 8B 及以上模型。

## 3. Token 和 API 调用现状判断

当前 `.env` 使用 OpenAI-compatible 云端地址和 `deepseek-chat`。现有主问答路径通常是：

```text
用户问题
  → 规则准备 Query
  → 确定性检索/Parent 读取
  → 上下文压缩（本地规则，不调用模型）
  → AnswerGenerator 调用一次云模型
  → 规则评估
```

所以当前的主要问题更可能是**单次请求输入上下文过大、召回内容不准**，而不是当前代码在每一步都调用了模型。`max_context_chars=12000`、`top_k=7`、Parent 拼接和重复追问会让单次输入变长；当前还没有记录真实 prompt Token、completion Token 和每次调用耗时，因此“调用巨大”目前无法被精确拆分。

参考项目如果完整启用模型驱动流程，单个复杂问题可能包含：查询分析、多个 Agent 编排轮次、上下文压缩、Agent 回答和最终聚合等多次调用。它的能力更完整，但如果不设置预算，调用次数可能比当前更多。

V3 必须同时做到：

- 使用 Ollama 后不再向 DeepSeek 或其他云端发送问答请求；
- 记录每次模型调用的输入估算 Token、输出 Token、耗时、节点和调用原因；
- 简单问题走低调用路径，复杂问题才启用改写、拆分和多轮 Agent；
- 设置总模型调用预算、最大上下文 Token、最大输出 Token 和超时；
- 相同 `thread_id + query + index_version` 的改写结果可以缓存，避免重复调用。

## 4. Ollama 接入原则

Ollama 只负责 Chat LLM，不替代 Dense Embedding 和 Sparse BM25：

- `ChatOllama`：Query Analysis、澄清、Agent 工具决策、上下文压缩、最终回答；
- Dense Embedding：优先使用本地 `Qwen/Qwen3-Embedding-0.6B` 或已验证的本地嵌入模型；
- Sparse Embedding：继续使用 BM25；
- Qdrant：继续只保存 Child，Parent 仍由 Parent Store 读取；
- 所有模型通过配置切换，不把模型名称、Ollama 地址和预算写死在业务代码中。

计划中的配置项：

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=<待根据本机显存确认>
LLM_TEMPERATURE=0
LLM_SEED=42
LLM_TIMEOUT_SECONDS=120
LLM_MAX_OUTPUT_TOKENS=<待测试确定>
MAX_LLM_CALLS_PER_REQUEST=4
MAX_CONTEXT_TOKENS=<待测试确定>
```

模型候选不在本计划中直接下载；执行阶段先检查本机 Ollama 服务、已安装模型、显存/内存和工具调用能力，再确定默认模型。参考项目示例使用 `granite4.1:8b`，但不能直接假设它适合当前机器。

## 5. 分阶段执行计划

### V3-0：建立 4 问题基线，不改代码

交付物：

- 记录 4 个原始问题、期望答案、期望来源页/章节和必须出现的事实词；
- 对每个问题记录 Top-K Child、分数、Parent、最终上下文和实际答案；
- 统计 `fitz` 文本长度、有效章节数、Parent 数、Child 数；
- 记录当前每次问答的模型调用次数和输入/输出 Token 估算。

通过条件：能够区分“解析失败、召回失败、上下文拼错、回答生成失败、评估误判”五类问题。

### V3-1：恢复 PDF 结构和索引质量

交付物：


- 采用结构化 Markdown 提取方案，并增加中文字体、表格、标题和页码解析测试；
- 用标题层级生成 Parent，增加小 Parent 合并、大 Parent 再平衡和 Child 边界测试；
- 默认启用真实 Dense Embedding，保留确定性 Embedding 作为离线测试模式；
- 增加索引版本和重建检查，防止旧索引继续使用错误的 PDF 内容。

通过条件：4 个问题的期望事实均能在 Top-5 Child 或对应 Parent 中找到；解析文本不为空且关键词无乱码。

### V3-2：接入 Ollama 模型适配层

交付物：

- 新增 `ChatOllama` 适配器和 provider 配置；
- 统一模型调用接口，隔离 Ollama、OpenAI-compatible 云模型和测试 Fake LLM；
- 增加结构化输出 Schema：`is_clear`、`questions`、`clarification_needed`；
- 增加 Ollama 连通性、工具调用、中文输出和超时测试；
- 默认禁止在 Ollama 配置下调用云端 API。

通过条件：可以用 Ollama 完成一次最小问答；日志能显示调用节点和 Token 估算；关闭 Ollama 时不会破坏确定性单元测试。

### V3-3：按参考项目补齐 Query Analysis 和多问题编排

交付物：

- 用模型替换规则版 Query 改写，但保留规则预过滤以降低简单问题成本；
- 复杂问题最多拆成 3 个独立检索问题；
- 每个子问题独立执行 Child Search → Parent Retrieval → Self-Correction；
- 通过 Map-Reduce 聚合各子问题答案；
- 澄清问题暂停检索，用户补充后继续原 thread。

通过条件：一个包含两个独立事实的问题能分别召回两组证据并合并回答；同一 Parent 或 Query 不重复调用。

### V3-4：重做证据选择、上下文压缩和最终回答

交付物：

- 不再用上下文第一段作为最终答案；
- 最终回答必须引用已检索的事实和来源，证据不足时明确说明；
- 上下文压缩只在超过 Token 阈值时调用 Ollama；
- 压缩结果保留事实、数值、型号、来源文件和缺口；
- 添加低相关度、冲突证据和无证据三类测试。

通过条件：4 个基线问题全部答对；答案中的数值和结论都能映射到来源片段；无证据问题不会编造。

### V3-5：API 成本和质量闸门

交付物：

- 增加 prompt/completion/总 Token、模型调用次数、命中缓存次数和耗时日志；
- 增加每请求的总调用预算和每节点预算；
- 增加 Query Rewrite 缓存、检索结果缓存和可选答案缓存；
- 增加 RAG 回归集，至少包含 4 个问题、无证据问题、追问、多问题和冲突问题；
- 前端显示真实执行阶段和失败原因，不显示 Prompt 或私有推理。

通过条件：默认简单问题最多 2 次模型调用，复杂问题最多 4 次；超预算后走明确的证据型 fallback；云端调用为 0；4 个基线问题准确率达到 4/4。

## 6. 暂不做的事项

- 本次不修复当前 4 个问题；
- 不立即下载 Ollama 模型；
- 不删除当前 Qdrant 数据；
- 不切换生产配置；
- 不把 RAGAS 评估接入每次在线问答，先作为离线回归评估；
- 不把 PDF OCR、图片理解和多用户权限混入 V3。

## 7. 下一次执行顺序

用户确认后，严格按以下顺序一次执行一个阶段：

1. V3-0：建立 4 问题基线并汇报；
2. V3-1：修复解析、分块和召回质量并汇报；
3. V3-2：接入 Ollama 适配层并汇报；
4. V3-3：补齐模型 Query Analysis 和多问题 Agent；
5. V3-4：重做证据回答和压缩；
6. V3-5：完成 Token/API 成本闸门和最终回归。

每个阶段完成后停止，不自动进入下一阶段。
