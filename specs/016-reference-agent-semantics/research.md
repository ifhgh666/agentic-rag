# 016 研究与决策

**固定来源**: GiovanniPasq/agentic-rag-for-dummies / `394c4f7519e41923d695af1efa75b6afec76c553`，本地副本、Git blob 清单和 LICENSE 位于 [reference016 夹具](../../backend/tests/fixtures/reference016/manifest.json)。
**复核日期**: 2026-10-27；本次只读现有源码/日志和本机安装库，不调用真实模型、不下载资源、不升级依赖。

## 决策一：参考业务控制流与外围适配分开

Decision：恢复参考主图、六节点研究子图、两类摘要、聚合和路由；不只搬目录。保留当前知识检索基础设施、认证、互斥和公开投影。

Rationale：源码可与固定参考分别加载后对照；`tests/fakes/reference_baseline.py` 在独立测试命名空间改导入、替换日志装饰，不是第二套生产 Agent。该对照共享 scripted 模型/工具，并不证明真实模型语义质量。

Alternatives considered：保留旧 ModelAgentLoop 改名、给新入口加旧图开关均不符合 016；复制参考 PDF/嵌入/向量库基础设施会超出范围。

## 决策二：准确保留计数和摘要边界

Decision：`rag/edges.py` 先判断无工具直接 collect；有工具且迭代 `>=10` 或累计请求 `>8` 才 fallback。计数含当前返回的尚未执行批次，整批超界不执行。递归 50 是图步数，非总模型调用配额。

Rationale：`rag/nodes.py` 每次 orchestrator 累加工具数及一次迭代；历史摘要、压缩、fallback、聚合不占这个研究迭代计数。近期消息 4 的实现是在回答前保留 3 条普通消息，再加入答案；新轮重置 agent_answers。

Alternatives considered：执行第九次工具后才判断、把总调用限制为 8/12、强制 BranchAnswer 或引用修复均改变参考语义。

## 决策三：provider 适配不强求统一入口协议

Decision：`core/reference_model.py` 的兼容端点包装显式 `with_structured_output(schema, method='function_calling')`；Ollama 返回原生 ChatOllama，节点无 method 调用沿用 SDK 默认 `json_schema`。研究阶段两者均 bind_tools，不追加旧 schema 文本。

Rationale：当前安装库 `langchain_ollama/chat_models.py` 的入口默认 method 为 json_schema；只写“全部 function calling”不符合当前代码。原兼容服务拒绝严格 response_format 的历史记录解释了兼容端点选择，但不能证明本轮原生工具兼容通过。

Alternatives considered：把 Ollama 也改 function calling 是额外产品行为变更，本次不做；恢复旧 json_object 回退或换 provider 不在范围。

发行包元数据：langgraph 1.2.12、langchain-core 1.6.4、langchain-openai 1.6.5、langchain-ollama 1.1.0、tiktoken 0.14.0；底层 openai 3.19.2、ollama 0.6.2、httpx 0.28.1。旧计划的“openai 1.6.5 / ollama 1.1.0”省略了适配包前缀，现修正名称，不改变依赖。

## 决策四：取消旧应用时限后不虚构替代上限

Decision：正常工厂不传旧 llm_timeout_seconds、llm_max_output_tokens、max_context_tokens。兼容端点显式 max_retries=0；没有业务重试。保留 SDK/服务自身异常行为，不承诺新的墙钟上限。

Rationale：本机 langchain_openai 的 request_timeout 默认 None 并传入客户端；本地 ollama 客户端默认 timeout=None。裸 openai SDK 的 600 秒默认不等于本调用链有 600 秒保证；异步每 chunk 超时也不能替代当前同步图的请求期限。

Alternatives considered：文档写“取消 300/120 秒但仍有 SDK 600 秒保护”不符合实际参数；新加截止/回退需独立授权设计。

## 决策五：保留宽松三字段与提示边界

Decision：参考 schema 仅三个必填类型，没有旧 anyOf、strict、禁止额外字段或联动空串校验；最多三问来自原 prompt。首轮搜索和避免重复工具均保留提示引导，无工具时路由仍可 collect。

Rationale：给 schema 加本地硬三问、数字替换或代词兜底会偏离原始参考。Parent 实际只校验 UUID、存储/文档 ready，不要求本请求曾搜索；子块保留现有 query/limit/min_score/ready 适配并明确记账。

Alternatives considered：借文档补全重新引入旧拒绝逻辑、把提示建议解释为代码闸门均不采用。

## 决策六：压缩、来源和观测

Decision：工具后严格 `tokens(messages)+tokens(summary) > 2000+int(tokens(summary)*0.9)` 才模型压缩；保留首问、追加检索标识、删除其余旧研究消息。artifact 只供本次来源/界面，来源采用精确文件名交集，公开观察采用白名单。

Rationale：压缩是摘要，不是输入准入。tiktoken 编码获取失败使用参考长度回退，但获取资源本身可能触网；A 的离线保障由 guard 禁网络及编码下载实现。SDK实际token化与长度回退的对照证据应分开报告。

Alternatives considered：把 artifact 注入额外模型决策、恢复 citation registry/在线核验卡，或宣称 try/except 本身保证离线，均不采用。

研究结论没有尚待产品决定的 A 设计歧义；真实 provider 兼容和回答质量仍属未授权 B。现存运行失败/缺少统一复验属于工程未闭合，不被本研究结论消除。

## 2026-10-27 B 操作设计与首次结果追加

用户在 A 总报告后明确继续 B。Decision：沿用当前实际 deepseek-flash 兼容端点和原 SDK；临时真实 Qdrant 只使用合成规程、deterministic Dense/local BM25，Token 估算用参考字符回退；不下载模型或加载正式知识。Rationale：验证真实模型/图/工具协作，同时维持正式数据与配置边界；不能外推语义检索或实际 tokenizer 质量。Alternatives considered：改用 Ollama、修改模型身份、导入正式 PDF、临时更换提示或恢复旧总截止，均超出本轮验收范围。

B01 首次尝试以 OpenAIInvalidRequestError 失败，后续四项按冻结规则未运行；没有取得模型答复，不推断具体不兼容参数。工程采集检查与临时索引预检通过不能覆盖此失败。见 [B 协议](phase-b-protocol.md)和 [当前失败](CURRENT_FAILURES.md)，原 A 研究/历史证据保持。
# R 补充：DeepSeek Flash 非思考传输

2026-10-27。Decision：精确 `openai_compatible/deepseek-flash` 在正常参考图工厂中显式关闭思考，复用相同模型和 SDK。Rationale：真实诊断已复现 `Thinking mode does not support this tool_choice`，且关闭思考的完整 B01 成功；[DeepSeek 官方说明](https://api-docs.deepseek.com/guides/thinking_mode/)给出默认思考、extra_body 开关及携带工具时 reasoning_content 回传要求。本机 ChatOpenAI 源码明确不保留第三方 reasoning_content，因此只关闭入口不能保证后续工具往返兼容。

Alternatives：只入口关闭会留下工具回传兼容问题；改 tool_choice=auto 不能保证原结构化接口返回；新增 ChatDeepSeek 或保存私有推理扩大范围；全体兼容模型注入非标准字段会误改其他提供商。仅对已真实验证的模型标识修复，其他标识以后单独验证。此处是传输兼容策略，不保证语义质量或服务端权重固定。

# B 续测补充（2026-10-27）

Decision：复用原 capture.py，续测包装只保留原 B02–B05；先核对全部产品 Python 和身份与 R 的真实 B01 相同，再引用已通过证据。Rationale：无需再次请求已通过首题，同线程 B02/B03 由原 collector 的同一服务承接，减少采集实现差异。Alternatives：重跑五题会增加不必要请求；拼接不同模型/代码结果会掩盖条件差异，因此对身份、源码、旧结果和协议均做冻结/哈希核对。没有新增技术未知项或研究代理任务。

## D 真实 PDF/ONNX 操作核对（2026-10-28）

Decision：按用户“开始真实测试”使用 gold-1.0 Q1–Q4、正式库的只读隔离快照和真实 ONNX/BM25，保持当前 deepseek-flash 和正常工厂。Rationale：补齐前次合成/确定性检索未覆盖的真实检索质量；旧 capture_v4_formal.py 消费退役接口，不能直接作为新图入口。侧车复用 B 的公开事件记录，无新增产品接口或技术选型。Alternatives：重复合成 B 不能覆盖真实 Dense；更换模型、过滤重复文档、把标准答案传给模型会改变被测条件，均不采用。

实际准备发现原默认 BM25 临时缓存不再存在；从官方 Qdrant/bm25 资源获取 english.txt，SHA256 与历史正式采集记录完全一致（019F104B…B6451）。保留原 LocalEntryNotFoundError/采集器快照后仅恢复资源准备，未发出模型请求，不更换 stemmer 或空词表。完整操作和边界见 [D 协议](phase-d-real-pdf-20261028-protocol.md)。

## E 全量失败继续设计（2026-10-28）

Decision：按用户新要求完整重新运行 Q1–Q15/19 轮，前题失败不阻断后题，全部采集后比较原答与标准答案。Rationale：D 的质量 gate 无法形成全题集问题分布；原 capture_one 硬编码 auto，E 侧车须透传各 flow_step 的原 action。保留 D helper/真实资源，仅新建采集侧车与隔离数据。Alternatives：继续沿用停止规则或只测余题均不符合“全部一遍”；自动重试择优、期间修提示或使用模型 Judge 改变成本/条件，均不采用。没有新的产品选型或研究代理任务，细则见 [E 协议](phase-e-full-gold-20261028-protocol.md)。

