# 016 D：真实 PDF 与 ONNX 首批测试协议

日期：2026-10-28（America/Phoenix）。用户明确要求“开始真实测试”，本阶段测试当前参考图的真实问答链路，采用已批准 `gold-1.0` 的 Q1–Q4 原题、历史夹具、标准答案和必答事实；不改题、不追加 Judge，不扩展到剩余题目。D 对应 tasks Phase 9/T027–T029，报告后暂停，等待用户验收。

## 冻结条件

- 实际配置 `openai_compatible/deepseek-flash`，temperature=0、seed=42；直接使用产品 AgentGraphService/RagPipeline 和原生工厂。模型工厂的非思考策略保持，不覆盖模型/工具/提示/schema/估算器，不重试、不切 provider。
- 题库 `specs/004-query-clarification-ragas/gold-cases-v1.json`，版本 gold-1.0。源 PDF SHA256 为 `4F2BC2FC688BC9B6B5645D521960D688482638EBEF0828BD75E1A55759365017`。正式库现有两份同内容 PDF，保留其真实检索环境和重复文档，不删改以提高成绩。
- 只读复制文档元数据、PDF、Markdown、索引清单；Qdrant SQLite 使用 mode=ro 的一致性备份。仅在新快照目录创建 Qdrant 客户端，禁止迁移、重建；重定向快照内文档路径，PDF 内容和索引版本保持。
- 真实 Dense 为当前 fastembed 多语言 MiniLM 384 维 ONNX；复制现有模型缓存到本轮隔离目录，仅加载本地资源。BM25 使用原真实 english.txt 和原 stemmer 配置，不切换空词表或 deterministic。首次准备发现默认临时缓存已缺失，尚无 LLM 调用；另存原准备失败和采集器快照，从 Qdrant/bm25 官方资源补齐 936 字节词表，SHA256 必须等于历史正式批次的 `019F104BA2ED07436D05F9CDD3383034AD66014EDC27FC651F837E1A038B6451`，仅恢复准备，不构成答案重试。资源下载不是完全离线运行。
- `output/reference016/phase-d/formal-pdf-20261028-01/` 独占保存冻结、事件、原答、逐题审阅、命令/退出码和保护核对。原始 evidence 文件禁止覆盖；旧失败保留。凭据/端点明文、系统提示和私有推理不得进入产物。

## 顺序与通过条件

| 题目 | 原问题 | 必须检查 |
|---|---|---|
| Q1 | 设备上电前需要检查哪些内容？ | 原 PX-200 历史夹具；电源/接地/负载、合格万用表、198–242 V、49–51 Hz、急停复位、保护灯熄灭、无故障码 |
| Q2 | PX-200 的过流保护阈值是多少？ | 超过 16 A、持续 100 ms、立即断开主回路；不得把超过写成达到 |
| Q3 | 过流保护后如何恢复？ | 原 PX-200 历史夹具；依序断开负载、完全放电、查短路、确认负载正常、确认键清告警、重走上电；不得建议旁路或连续重启 |
| Q4 | 运行记录默认保留多久？ | 原 PX-200 历史夹具；三年、超期先进先出删除 |

逐题首次运行一次，先落盘原答/事件，再由 Codex 按原 required_facts、ordered_facts、forbidden_claims、PDF 原文和实际检索内容审阅；审阅记录不冒称用户验收。完成状态、真实工具使用、最终聚合、实际来源、事实完整性与顺序均检查。任一 failed/pending 即停止，剩余记 not_run；不重写输入或补问凑通过。若采集器/环境失败，单列 blocked/capture_failed，不冒充模型答案失败，也不自动切换模拟模式。

各题独立线程，history_fixture 只作为真实用户历史注入 checkpoint；不向模型传标准答案、必答点或审阅信息。Q1/Q3/Q4 的预置历史不是模型自行完成的历史轮次。

## 计数、运行与边界

保持 016 每分支 8 工具请求/10 研究迭代、递归 50；旧 8/12 总额度和 300/120 秒产品截止不接回主图。外部 supervisor 900 秒只限制本次自建采集子进程（含逐题审阅等待），超时记 harness_aborted，不宣称产品 timeout。无 Judge 调用。

采集入口 `output/reference016/phase-d/capture_real_pdf.py` 的 prepare/supervise/audit；复用原 B 的只记录公开事件的 capture_one。prepare 检查真实本地资源和索引，不调用 LLM；supervise 启动 real，逐题审阅通过才进入下一题。每条事件即时 flush，记录 request_id、首答、checkpoint、安全用量及实际耗时。

这是当前真实模型与既有 PDF/真实混合索引的 Graph/pipeline 测试。本轮不重跑上传/PDF 解析、不启动或重启用户服务、不宣称 HTTP/认证/浏览器验收；Parent、压缩和历史摘要只有实际调用才列为覆盖。不改正式知识库、模型配置或产品源码，不提交推送。

报告保存 `phase-d-real-pdf-20261028-report.md`，给出实际命令/退出码、逐题原答与结论、模型/工具次数、Token 来源、耗时、失败和未运行项、保护差异及后续范围。**报告后暂停，等待用户验收。**
