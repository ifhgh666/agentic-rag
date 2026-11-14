# 016 E：gold-1.0 全量真实测试与答案对照

2026-10-28（America/Phoenix）。用户明确要求“全部测试一遍，前面停止了不影响后面的，最后得出分析，对比模型的答案和正确答案”。本次 E=tasks Phase 10/T030–T032，为一整个全量测试/分析阶段，替代 D 的首个非通过即停止规则；D 及更早原始失败不改判。

## 范围和运行规则

- 重新独立运行 gold-1.0 Q1–Q15 全部 15 个场景、19 轮原定输入，不引用 D 的 Q1 替代本轮，不重试或择优。Q9–Q12 的两轮分别保留；同场景用同线程，其他场景隔离。前轮失败仍执行原定下一轮/下一场景。
- 保持当前 deepseek-flash、temperature=0、seed=42 和产品正常原生工厂、图、提示、工具、schema。真实 fastembed ONNX 384 维+原 BM25、正式测试 PDF/16 Point 索引的全新只读隔离副本，沿用 D 已验证原词表。没有产品修改、Judge、模拟问答、provider 切换、正式数据重建或服务重启。
- fixture 保存原问题、history_fixture、flow_steps、参考答案和必答/禁答项；向模型只交原问题、原动作和原历史，不交当前题标准答案、判据或审阅信息。
- 原始 raw/events 文件独占创建、逐事件 flush；异常、空答和无待办错误如实保存并继续。每个场景独立自建子进程，外部 900 秒 watchdog 仅终止本场景采集并继续下一场景，不作为产品 timeout；如发生全局数据指纹变化/不可读取等完整性阻断，保留证据并明确剩余未运行，不伪造全测。
- 采集期间不因质量失败暂停等审阅；全部输入尝试完成后统一逐题对照。记录 request_id、模型/工具/云路径调用、Token 来源和耗时。无质量失败时才声称通过；采集成功不等于质量成功。

## 判据与对照产物

10 道 answerable、4 道 clarification_flow、1 道 unanswerable 分开统计。事实答案按原 reference_answer、required_facts、ordered_facts、forbidden_claims 及本次检索正文作语义审阅；同义表达允许，不能仅按字符串相等评分。实际出处与数值/完整性分别核对。

交互按原步骤的 expected_status、pending、是否检索、取消的零模型调用以及末轮事实完整性检查；任一必要步骤失败则该场景失败，不能用末轮成功覆盖首轮失败。原 fixture 的 expected_questions 精确文字和 expected_relation 额外记诊断差异：016 已批准将 pending 补充统一投影为 clarification，因此 Q12 的旧 uncertain 字段不单独作语义失败；需保持未确认状态、原 pending、无无依据检索。禁止为消除这些差异改题集或产品。

Q11/Q12/Q13 的 reference_answer=null，正确答案栏展示原预期行为（取消/继续澄清/明确资料不足），不能填“无正确答案”或当作零分。Q13 不应编造固件版本、下载地址或操作步骤。

每题保存模型完整首答、标准答案/正确行为、逐事实覆盖/遗漏/错误、步骤顺序、来源情况、状态及可定位原始证据。输出逐题 review.json、完整 comparisons.json、可阅读的 `phase-e-answer-comparison-20261028.md` 和 `phase-e-full-gold-20261028-report.md`。总体统计同时给事实题/交互题/无答案题分母，不把用量、采集完成率或来源存在当成答案准确率。

## 准备与保护

复用 D 的只读快照、资源和正常产品装配辅助函数，不改 D collector。E 侧车位于 `output/reference016/phase-e/capture_full_gold.py`，本批目录 `output/reference016/phase-e/full-gold-20261028-01/`。运行前冻结源码/配置/题集/正式数据及旧报告/证据，保存 Git 和文档改前快照；真实调用前检查 PDF、Dense、BM25、Point 数量和索引版本。运行结束核对保护项，报告阶段的计划内失败清单更新单列。

本阶段不重测 HTTP/认证、浏览器或 PDF 上传/解析，不自动修改框架来改善成绩。完成全部尝试与对照分析、保存报告后暂停，等待用户验收。
