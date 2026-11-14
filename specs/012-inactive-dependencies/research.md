# P3 技术决策与取舍

日期：2026-10-22。依据当前源码、012 规格及两个只读研究代理的结果；没有运行应用/测试/模型，没有新增依赖或查阅外部服务。本文件记录设计选择，不是工程通过证据。

## R1：显式核心与原签名适配

**Decision**：graph.py 增加唯一私有 `_build_model_subgraph`，只接收 settings/tools/generator/budget/request_cache。AgentGraphService 直接使用它；已有 build_agent_subgraph 原签名保留，仅解析旧合法参数并委托该实现。

**Rationale**：[当前 builder](../../backend/app/rag/graph.py#L36)有 6 个未读参数，仓库唯一生产调用在 133 行。selector 实际只提供 settings/cache。只解除正常图依赖，同时给旧直接调用一个明确兼容边界，比扩大旧函数到两套可选参数模式更易判断必需依赖。

**Alternatives considered**：直接缩减公开签名会破坏未知外部使用；一个函数同时接收旧位置参数与新 keyword-only settings/budget/cache 虽少一个 helper，却要解释两套优先级、空值和缺参组合；拆兼容模块则增加无价值路径。本方案付出同文件小适配函数的代价，保留一份图构建逻辑。

## R2：默认旧服务移出主图，显式兼容访问按需构造

**Decision**：正常初始化不创建 QueryGenerator、rewrite cache 或 EvidenceSelector，运行也不访问它们。保留 query_generator ctor 参数及 query_generator/evidence_selector 可读写属性；默认值首次显式读取才创建并缓存。用普通 property、私有哨兵和一个实例锁协调首次读取/赋值，不增加注册表或全局工厂。

**Rationale**：仓库没有图外读取这两个属性的代码，但之前存在普通可读写属性，直接删除是额外外部破坏。显式属性访问是兼容操作，正常问答无需承担它的资源成本。analysis_cache 仍活动，不能把所有缓存都当成旧 rewrite cache。

**Alternatives considered**：将属性改为 None 简单但破坏旧直接访问；继续 eager 构造无法达成 FR-002；按需属性不缓存会改变身份且反复分配；通用容器/描述符框架和新模块超范围。

## R3：精确限定保留的兼容行为

**Decision**：保留 ctor 的 query_generator 原 `or` 选择语义；显式 ModelQueryGenerator 仍仅绑定原 budget/request_cache，不改它的 provider、cache 或 index_version。默认兼容对象延迟创建时使用 ctor 捕获的原依赖引用、provider、fake/model 选择及缓存 TTL/容量标量。setter 按原赋值保存对象，不新增绑定；赋值 None 不等于“尚未创建”。

**Rationale**：若 getter 在运行后读取 generator.provider，会把旧默认构造时可能为 None 的引用换成后来初始化的对象。若 setter 自动绑定，会增加原先没有的语义。单一哨兵区分未创建和显式 None，锁内只创建/发布本地对象，不调用 generate/select 或网络。

**Alternatives considered**：统一成所有注入都自动绑定、动态追随最新 provider、将 None 当缓存未命中，都会暗改既有可观察行为。未知外部调用不能保证全覆盖，明确的契约比声称“完全向后兼容”可靠。

## R4：保留真实配置与共享对象的原选择

**Decision**：正常子图仍优先 AnswerGenerator.settings，否则使用图 settings；预算使用图已经绑定给 generator 的同一对象，cache 使用图 request_cache。旧 builder 仍按原 generator/selector 规则解析。不在 P3 修复 graph settings 与 generator.settings 可能不一致的问题。

**Rationale**：当前 builder 的 settings 优先级在 [graph.py 43 行](../../backend/app/rag/graph.py#L43)；当前工具和预算已经各有生效位置。把参数清理扩大成配置统一会改变行为并超出本次动机。

**Alternatives considered**：新增一份 Settings 或预算拷贝会改变身份/额度；继续通过旧策略载体读取基础对象保留虚假耦合；重设全部配置为 graph.settings 会修复一个未获批准的潜在差异。

## R5：清除 procedure 正常图传递，保留独立契约

**Decision**：移除 nodes/edges 的固定写入与转发；TypedDict 可选声明保留兼容说明。AnalysisOutcome.requires_procedure 默认 False、生成两个关键字及结果三元组保持。独立 EvidenceSelector 的 procedure 行为仍真实有效，不能删除或接回主图。

**Rationale**：[prepare_query](../../backend/app/rag/nodes.py#L81)固定 False，后续复制但循环不读取。公开 GraphRunResult、SSE、前端和 ThreadState 不含这些字段；诊断不保存整个 MainState/AgentState。另一方面，独立测试和 replay 脚本仍传旧生成参数，入口 schema 明确拒绝 requires_procedure。

**Alternatives considered**：删 Outcome/关键字会破坏独立调用；恢复旧分类或按参数筛引文是新增业务行为；删除全部 procedure 模块误伤独立证据处理；保留所有图内复制则仍误导维护者。

## R6：旧配置与低收益符号保留，不做批量删除

**Decision**：保留 agent_parent_threshold_chars、AGENT_PARENT_THRESHOLD_CHARS、默认 240 与解析能力，只说明其当前不控制主图 Parent 读取；BUDGET_FALLBACK_PREFIX 及预存无用导入延期。本次仅清理变更直接造成的悬空引用。

**Rationale**：旧阈值在 config/.env.example 暴露，当前仅传入未读参数；不能以清理扩大为配置迁移。常量没有仓库内引用，但不能排除外部 import，删除收益很低。

**Alternatives considered**：自动移除环境字段、恢复自动 Parent 路由、广泛卸载依赖或删旧模块都超范围。保留且如实说明不生效，不冒称修好了该旧配置。

## R7：行为证明优先，静态扫描辅助

**Decision**：实施先保存实际基线和构造边界红测，再做局部清理。构造/并发属性检查与真实 graph.run、独立服务和 SSE 配对；保留 P1/P2 所有容量、预算、期限、来源、历史和诊断测试。完整隔离回归在最终 B 阶段运行。

**Rationale**：源码无引用不能证明运行没有创建；缓存与 owned/shared 路径不能只靠构造签名断言。对比答案/来源/状态/原因/逻辑次数和历史，动态身份、时间戳及资源剩余时间不要求逐字相等。

**Alternatives considered**：仅删参数后 compile、只断言私有 helper 调用次数、将 old tests 删除以减少失败，都不足以证明行为保持。真实模型不在授权内，也不是这类结构清理的必要前置。

## 未决项与边界

没有未解决需求或技术 gate。保留方案已限定：原方法/构造/属性的已列契约继续支持，但通过修改兼容 selector 的内部 cache 间接配置主图的联动将解除；不保证未知外部内部状态突变。实施若发现新的公开依赖，先保存证据并按保留/延期处理，不借机破坏兼容。
