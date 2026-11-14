# P3 依赖及兼容状态模型

状态：A/B 已按下述模型实施，工程核对见 [B 报告](phase-b-report.md)；原设计约束保持。依据 [规格](spec.md)、[计划](plan.md)和[兼容契约](contracts/compatibility.md)。本功能不新增业务数据库、持久化模型或产品 API。

## 依赖条目

这是工程清单，不要求新增运行期类。

| 字段 | 含义/约束 |
|---|---|
| evidence_id | 对应 scope 的 E1–E6，可拆分子项 |
| definition / references | 定义、正常图、独立调用、配置/序列化证据 |
| disposition | remove_from_graph / retain_compat / retain_active / defer |
| phase | A 或 B；延期条目不伪装完成删除 |
| contract / validation | 需保留的调用与可观察结果、验证位置 |

状态流：candidate → reviewed → planned disposition → 实施后 evidenced result。静态“未读取”只到 candidate/reviewed，不自动等于删除许可。

## 当前图实际依赖

| 依赖 | 所有权与关系 |
|---|---|
| settings | AnswerGenerator 优先使用 generator.settings，否则图 settings；不复制或统一冲突配置 |
| tools | 原 create_rag_tools 的结果；模型决定工具，旧 query generator 不参与 |
| generator | 原注入实例，普通生成/汇总/修复接口不变 |
| budget | 引用图创建并绑定的同一 ModelCallBudget；owner/lease/期限规则仍由 P2 管理 |
| request_cache | 引用图的同一 RequestToolCache；分支缓存和计数不复制 |

精简 builder 的生命周期仅构造并编译子图，不 start 请求、不调用模型、不申请新缓存。旧 builder 仅翻译原依赖，复用同一实现。

## 两个兼容属性

每个 Graph 实例各有 query_generator、evidence_selector 的私有值；一个实例锁可协调两者。无需通用 lazy 容器或新数据类。

| 状态 | 进入方式 | 显式读取 | 赋值 |
|---|---|---|---|
| UNINITIALIZED | 默认构造时放私有哨兵 | 锁内创建一个对象/必要的 rewrite cache，保存后返回 | 保存给定值，进入 ASSIGNED |
| READY | 首次读取构造成功 | 返回同一对象，不重建 | 保存给定值，进入 ASSIGNED |
| ASSIGNED | ctor 选择的显式注入或 property setter | 原样返回该值，含显式 None | 原样覆盖，仍为 ASSIGNED |

- ctor query_generator 的原 truthiness/`or` 选择保持；被原规则视为未提供时进入 UNINITIALIZED。
- 显式注入 ModelQueryGenerator 在 ctor 保留 budget/request_cache 绑定；setter 不新增重绑定。
- 默认对象所需原 settings/document_store/budget/request_cache/provider 引用、fake/model 选择和缓存 TTL/容量在 ctor 捕获；只保存引用/标量，不为了捕获而创建旧对象或专用缓存。
- 首次并发读取只发布一个对象；赋值与读取串行化。创建失败只影响该显式访问，不缓存半成品、不影响正常主图，不自动调用模型。
- 主图构造/执行不得读取这两个兼容属性；否则会重新引入失效依赖。

## procedure 和旧阈值

正常 MainState → Send → AgentState 不再写/转发 procedure_required/procedure_only。TypedDict 声明保持 total=False 下的可选兼容字段，不新增字段或验证。AnalysisOutcome 的 requires_procedure 及生成两个关键字仍存在，当前语义保持。

ThreadState、GraphRunResult、公开 SSE 与诊断快照顶层不新增/删除字段；无迁移。Settings 旧字段/环境名/默认 240 保留，当前主图不使用其驱动 Parent 决策。

## 行为基线

在隔离工程记录中保存 answer、sources、status、reason、logical model/tool counts、cache hits、history/pending、诊断状态与首次结果。不同运行的 request_id、model_call_id、时间戳、耗时和剩余时间仅作关联，不要求字节相等。首答/失败证据不得覆盖。
