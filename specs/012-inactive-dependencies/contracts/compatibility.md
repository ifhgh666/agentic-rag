# P3 装配与公开调用兼容契约

状态：A/B 已按本契约实施并完成隔离工程核对，待用户验收；实际成绩及未测范围见 [B 报告](../phase-b-report.md)。对应 FR-002–FR-008、SC-002–SC-005；不新增产品端点、协议字段或 UI。本文列出要保留的边界，也明确被解除的隐式关系。

## 正常图装配

AgentGraphService 原构造参数顺序、名称及默认值保留，尤其 query_generator、memory、query_analyzer。构造时 generator 的 fake 适配与原共享预算/请求缓存装配保持。

正常图调用同文件私有 `_build_model_subgraph(*, settings, tools, generator, budget, request_cache)`；五项为实际依赖。Settings 选择保持 AnswerGenerator.settings 优先、其他情况图 settings；不在此处创建 budget/cache 副本或重置期限。正常 ctor/run 不创建旧 QueryGenerator、rewrite 专用缓存或 EvidenceSelector，不调用旧 generate/select。

analysis_cache、检索缓存和请求工具缓存仍活动；目标“0 构造”仅针对旧装配，不等于全图无缓存。

## 旧 build_agent_subgraph

现有签名保持：

```text
build_agent_subgraph(tools, context_builder, generator, selector,
                     retrieval_top_k=7, max_tool_calls=16,
                     max_iterations=10, parent_threshold_chars=240,
                     query_generator=None)
```

- 原合法位置/关键字调用和返回可 invoke 的编译子图保持。
- 解析 settings：AnswerGenerator 用 generator.settings，否则 selector.settings；budget 用 generator 已有预算，否则原工厂；request_cache 用 selector.request_cache。
- 解析后调用唯一精简 builder，不复制节点逻辑、不新增 class/registry/module。
- 依赖在构建时解析，运行中缓存内容和计数仍共享原对象；构建后重新绑定 selector.request_cache 等属性不是热更新协议，不保证改变已编译子图。
- context_builder、retrieval_top_k、max_tool_calls、max_iterations、parent_threshold_chars、query_generator 在该旧入口仍为兼容接收，不新增业务作用。实际限制来自既有 Settings/预算/工具，不据这些参数覆盖。
- 正常 AgentGraphService 不再使用旧入口；它只为独立旧调用保留。无效输入组合不扩大为新的受支持能力。

## query_generator 与 evidence_selector 属性

两者仍可读取和赋值。默认值仅在首次显式读取时构造、缓存，并发读取得到同一对象；一个实例锁足够，无全局状态。赋值后返回所赋值，包括 None，不因为值为 None 重新创建。

query_generator ctor 参数继续按原 `query_generator or default` 的选择含义处理。原规则选中 ModelQueryGenerator 注入时保持对象身份及原 budget/request_cache 绑定，不替换 provider/cache/index_version，不为它分配额外未用 rewrite cache。

默认 RuleBased/Model 选择、原依赖/provider 引用和缓存 TTL/容量标量在 ctor 捕获，后续第一次访问不改为捕获“运行后才初始化”的另一个 provider 或后来修改的缓存策略。Model 默认缓存仅在显式读取时创建，保留原策略和 index_version 取值关系；普通属性读取不调用模型。

setter 仅保存对象，沿用原普通赋值的含义，不新增自动 budget/cache 绑定或调用。evidence_selector 默认使用原 settings/document_store/request_cache 构造，独立 select 能力保持。

这些兼容对象不再是当前图的运行期配置入口。外部修改其内部 settings/cache，或替换兼容属性，不应改变已显式装配的当前图。旧 selector.request_cache 动态突变曾可能间接影响子图，这种未记载的联动是本次明确解除的关系；若有实际外部依赖，应先记录并处理，不能宣称其任意突变完全兼容。

## procedure、独立能力与旧配置

| 接口/字段 | 保留契约 |
|---|---|
| AnalysisOutcome.requires_procedure | 字段、默认 False、dataclass 形状和缓存命中属性保持；不恢复入口分类 |
| QueryAnalysis schema | 仍三字段，额外 requires_procedure 继续拒绝；不改模型 prompt/schema |
| generate_grounded_with_result | 保留 procedure_required=False、include_fact_citations=False；当前两个参数不控制生成或引文选择；原三元组、空证据零调用、有限修复与 P2 scope 保持 |
| MainState/AgentState procedure 声明 | 可选类型声明保留，明确仅兼容；正常图不再主动写入/转发，无公开产品字段承诺 |
| EvidenceSelector.select / procedure_evidence | 独立 procedure 处理真实生效，保持方法、段落恢复及来源行为，不恢复为主图策略 |
| QueryGenerator / ModelQueryGenerator | 独立候选、去重、缓存、结果形状和 P2 调用治理保持，不接回主循环 |
| agent_parent_threshold_chars | Settings 名称、环境变量 AGENT_PARENT_THRESHOLD_CHARS、默认 240 和解析保持；注明当前主图不受它控制，不恢复自动读取 Parent |
| BUDGET_FALLBACK_PREFIX | 保留原符号和值，本期延期清理，不作为主图策略 |

不为兼容参数新增运行期 warning，避免额外日志/SSE 或性能副作用。文档只说明现有不生效含义，不承诺未来删字段日期。

## 交付与治理不变项

model_call、context_admission、provider、budget、memory、diagnostics 的执行规则保持。模型工具选择、原文/Parent 实读、批次配对、部分回答、引用修复、缓存重检、缺失/旧 lease 拒绝、同一 deadline 和迟到恢复继续有效。

ChatRequest、GraphRunResult、SSE 名称/终态/来源/用量语义和诊断白名单不变；单终态、私有首答范围、queued 不等于 saved、故障不改问答继续验证。既有失败、原始首答和阶段报告不删除。

验收同时包含行为、构造计数和旧接口契约；不能只检查新 helper 被调用或仅作 AST 无引用证明。具体场景与命令见 [quickstart.md](../quickstart.md)。
