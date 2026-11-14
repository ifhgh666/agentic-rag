# Tasks：模型驱动 Agent Loop

**依据**：spec.md、plan.md、research.md、data-model.md、contracts/agent-loop.md、quickstart.md。
**实施授权**：2026-10-08用户明确说“执行”；实施分支`codex/model-driven-agent-loop`。阶段A—D逐个验证，不覆盖既有修改。

**最新状态**：2026-10-09用户仅授权执行C，并重申一次一个阶段、报告后暂停。T011—T015工程任务已交付：后端419项、前端23项及构建通过；两次真实场景失败，C运行验收未通过，T018待复验。交付[阶段C报告](phase-c-report.md)后停留C，不自动推进D。10月8日状态保留在[原暂停报告](phase-c-paused-20261008.md)。

**后续超时授权**：10月9日用户要求最大5分钟。T019已完成：请求300秒上限、API独立等待、同一截止传递与迟到会话隔离，后端最终425项通过。见[超时补充报告](timeout-300s-report.md)。没有重跑真实题目，T018仍未完成，D未启动。

**最新C复验**：用户随后以“继续”恢复T018。第一题Q16独立复验一次，32.644秒后仍因400 ms被模型改为“40或 ms”而constraint_mismatch失败；按失败暂停规则，第二题未运行。见[复验报告](phase-c-recheck-20261009-report.md)。T018未完成，报告后再次停留C，D未启动。

## Phase 1：准备

- [X] T001 保存现有代码/差异与正式知识库哈希到output/loop005-baseline/；核对.gitignore、项目约束和运行环境。
- [X] T002 完成005任务初始化与前置检查，更新specs/005-model-driven-agent-loop/spec.md实施授权状态。

## Phase 2：基础（阶段A）

- [X] T003 编写完整工具消息及两种提供者协议测试backend/tests/unit/test_model_loop_protocol.py，先记录失败。
- [X] T004 修复backend/app/rag/model_provider.py：保留role/content/tool_calls/tool_call_id/name；统一ToolCall(id/name/args)，支持按剩余时间调用。
- [X] T005 实现backend/app/rag/cost_control.py原子共享预算：请求8/12、分支5/4/3、汇总预留1、辅助预留1、工具16；原截止240秒已于10月9日按用户要求在T019改为300秒，配置在backend/app/config.py。
- [X] T006 新增backend/scripts/smoke_model_loop.py并验证本机原生工具搜索→全部ToolMessage→模型续轮；记录specs/005-model-driven-agent-loop/phase-a-report.md。

## Phase 3：US1 模型决定动作（P1，阶段B）

独立验收：同样证据，改变模型动作即可改变搜索/Parent/回答路径；短证据不强制Parent，长证据不强制回答。

- [X] T007 [US1] 新增backend/tests/unit/test_model_agent_loop.py，覆盖上述路径、多工具/缓存/无隐式语义回退。
- [X] T008 [US1] 实现backend/app/rag/agent_loop.py和graph_state.py：每轮原问题、分支、工具结果、预算交模型；最多三个分支。
- [X] T009 [US1] 改写backend/app/rag/nodes.py及graph.py路由，移除240字、非空、型号正则和固定重搜；所有工具按ID处理，身份注入、Parent白名单、缓存与物理上下文边界保留。
- [X] T010 [US1] 完成协议/行为回归与真实循环观测，记录specs/005-model-driven-agent-loop/phase-b-report.md。

## Phase 4：US2 场景推导（P1，阶段C）

独立验收：195V/300ms、65℃和READY场景保留模型结论及准确原文；题设数值不是设备阈值。

- [X] T011 [US2] 实现backend/app/rag/model_schema.py及generator.py的BranchAnswer、引用定位、最多一次修正；取消数字全抄引文和流程原文覆盖，单分支直接采用、多分支模型汇总。
- [X] T012 [US2] 修复backend/app/rag/query_analysis.py有效改写覆盖问题；保留原用户条件与现有会话/澄清隔离。

## Phase 5：US3 真实失败原因（P1，阶段C）

独立验收：无资料、无效工具、坏JSON、引用失败、预算、超时、取消独立标识；无云或规则回退。

- [X] T013 [US3] 在backend/app/rag/agent_loop.py、graph.py、pipeline.py及schemas/chat.py传递终态/stop_reason；失败不写成正常答案。

## Phase 6：US4 过程与对比（P2，阶段C/D）

独立验收：decision_id→model_call_id→tool_call_id可追溯；同协议30题首次结果完整计分。

- [X] T014 [US4] 更新backend/app/rag/pipeline.py与frontend/src/components/ProcessPanel.tsx、types/api.ts，按真实顺序显示模型动作、程序阻断、轮次/来源/耗时；保留完成后回放语义。
- [X] T015 [US4] 更新受新Loop影响的旧测试并运行backend/tests与frontend测试/构建，记录specs/005-model-driven-agent-loop/phase-c-report.md。
- [X] T019 [US3] 按10月9日用户要求设置整次请求最大300秒；在backend/app/api/chat.py补充独立等待期限，向pipeline/graph/共享预算传递同一截止时间，限制迟到答案与会话写入；新增6项测试并完成425项后端回归、重启与健康检查，交付specs/005-model-driven-agent-loop/timeout-300s-report.md后暂停。
- [ ] T018 [US3] C阶段运行复验：在最终总等待修复版本上确认正常场景答案、实际调用期限与事件关联，保留已有失败记录。10月9日恢复后Q16复验仍失败，C-UV未运行；见phase-c-recheck-20261009-report.md。报告后暂停，待用户后续明确指令；未通过前不宣称C全部验收。
- [ ] T016 [US4] 新增backend/scripts/capture_model_loop.py，冻结配置/题库/库哈希，通过正常API复测30题及单列9次关键题，生成output/rag30-loop005/标准答案/平台回答/分数/耗时对比报告。

## Phase 7：交付

- [ ] T017 对照规格与质量/成本门槛复核真实结果，记录specs/005-model-driven-agent-loop/phase-d-report.md和README.md启动/配置/限制；检查扩展钩子及编码，交付实际达标/未达标项。

## 依赖与执行策略

T001—T006基础先行；T007—T010为US1最小完整循环；随后US2/US3和US4工程观测，最后真实评测。各阶段失败先修复原因再推进，不能用fake成绩代替真实模型。

不同测试文件可并行执行；同一graph/provider/loop文件修改串行。US1行为测试与US2数值测试可独立准备，US3异常测试与US4前端展示测试可并行验证；本轮按阶段串行修改，不启动额外子代理。

原17项及新增C复验项T018采用checkbox、任务ID、用户故事标签和实际路径。本轮仅恢复C授权，报告后暂停；D与最终评分仍需后续明确授权，不宣称未验收或未实施的阶段完成。
