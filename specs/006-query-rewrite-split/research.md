# Research: 问题改写与拆分 V1

日期：2026-10-10。基于源方案与现有代码只读研究，未执行模型或业务测试。按项目`speckit-plan`研究步骤，两个研究代理分别核对集成和验收，结论合并如下。

本文件保留规划时的历史研究结论；2026-10-11已完成A–D工程工作，E首批在RW03失败后停止；F首次Q16保留数字、核心结论正确，但入口恢复子问缺共同条件而failed、完整答案not_verified，另两题未运行。当前状态见 [tasks.md](tasks.md)、[E 报告](phase-e-report.md)与[F 首次真实报告](phase-f-first-20261011-report.md)，原[F 待测报告](phase-f-report.md)保留，下文“待审阅/未实现”描述不作为当前进度。

| 决策 | 理由/代码证据 | 备选与取舍 |
|---|---|---|
| 更新现有QueryAnalyzer，不增加节点 | `query_analysis.py:83,180`当前已经一次调用；`graph.py:60`是入口 | 新建分析+改写串联违反一次调用；统一重构Loop无必要 |
| 严格三字段QueryAnalysis | `model_schema.py:6`已有宽松三字段类，`:14`旧QueryDecision含relation/procedure | 不保留第四个意图字段、不新增分类模型 |
| 待办auto先选动作 | `graph.py:87–106`旧relation影响待办；三字段无法表达新题/补充关系 | GitHub式默认全部续补改动小但会混入新题；不采用隐式文本规则 |
| 移出requires_procedure | `graph.py:104,125–137`传递兼容值；当前`agent_loop.py`不消费 | 不加入关键词类型判断；旧直接调用仅做必要适配 |
| 取消入口数字来源硬停止 | `query_analysis.py:45–53,237–238`集合检查不能验证条件语义；源方案要求基础格式与路由 | 保留旧硬停止会继续阻断模型数字失真；独立Judge超出范围。此取舍待计划批准 |
| 保留摘要保护与引用定位 | `conversation_summary.py:12,64`使用`_literal_constraints_preserved`；`agent_loop.py:64–86`已有核验 | 不整体删除数字helper，也不移除答案/工具安全边界 |
| 保存用户原话 | `graph.py:241`当前优先存rewritten_query，失真可能污染历史 | 改写结果独立诊断；不新建记忆系统 |
| 精确原题缓存与版本隔离 | `query_analysis.py:111–114`使用normalize_query；`query_planner.py:17–18`折叠空白/大小写 | 不提高TTL/容量；只更改入口键语义并失效旧协议 |
| 一问不强制程序恢复原句 | 同一个需补全追问也输出一问；`model_schema.py:29–38`当前折叠正文空白 | 提示及真实验收保原文；不偷偷加入语义分类规则 |
| 沿用Send分支与汇总 | `graph.py:118–134,155–166`已有分发和单/多分支路径；`generator.py:123`汇总 | 统一Loop或依赖DAG增加追踪/预算改造，源方案优先最小改动 |
| 入口自动重试0 | `query_analysis.py:177–192,207–216`没有重试；`config.py:41`入口上限1 | 源方案异常处理允许沿用，本版沿用零重试；以后增加须改预算 |
| 超过3独立需求澄清容量 | 保留全部用户目标且不越分支上限 | 截断前3项会遗漏；四项模型输出是协议失败 |
| 保留现有300s与8/12预算 | `config.py:33–48`、`cost_control.py:116–171`；本轮读取生效值一致 | 不以README旧2/4为依据，不增加预算 |

源附件自身的“单次入口”与“有限重试”由零自动重试默认消除歧义；多分支选择也已明确。无未决定的实施架构项，但所有决策仍是待审阅设计，不是已批准实现。

## 现有测试需要迁移

- `tests/unit/test_v4_query_analysis.py:35–40`目前接受完整单问改写，与新原文要求冲突。
- `tests/unit/test_v4_query_analysis.py:81–85`同时改型号/数字，不能证明否定或比较受到检查。
- `tests/unit/test_v4_query_schema.py`以及fake结构化输出需迁移三字段。
- 澄清/新题/取消回滚复用`tests/integration/test_v4_clarification_flow.py`，按新的显式动作约定改预期。
- 保留`test_model_loop_budget.py`、`test_request_deadline.py`和`tests/contract/test_chat_request_deadline.py`预算/期限回归。

## 状态与质量事实

2026-10-11E采集流程追加：用户要求遇错继续，选择显式continue模式及新目录续测未运行后缀，保留前缀failed。理由是取得完整首答覆盖，不改变质量标准；拒绝把旧失败改passed或重跑全部挑选成绩。生产调用链和预算不变，没有新增未知技术项。详见[继续规则](phase-e-continue-policy-20261011.md)。

005真实Q16输入400ms，两次输出40或ms，都是新会话、一次模型调用、零工具；第二次没有放行。最新结果32.644秒。C-UV本轮此前未复验，原32.7分钟记录不能冒充新300秒结果。006不改旧失败记录，不宣称取消拦截已修复数值质量。
