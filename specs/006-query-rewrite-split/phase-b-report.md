# 006 阶段 B 报告：上下文与澄清动作

日期：2026-10-10  
授权范围：仅执行阶段 B（T012–T016）  
前置阶段：阶段 A 已完成并有 [阶段 A 报告](phase-a-report.md)  
分支：`codex/model-driven-agent-loop`

## 阶段目标与停止点

本阶段处理必要上下文补全、待澄清问题与普通历史隔离、继续补充/开始新问题/取消三种明确动作，以及前端动作提示。阶段 C 的多问题拆分完整回答、阶段 D 的全量工程回归和阶段 E 的真实入口验收均未启动。

阶段报告保存后暂停，等待用户验收；不会自动进入阶段 C。

## 实际改动与验证范围

- [入口提示](../../backend/app/rag/query_analysis.py)：明确只使用理解当前问题所必需的历史；当前原题和明确确认补充优先于冲突旧历史；历史中仅提出“是否/如果”时保留条件，不把未确认触发改成已发生；陌生但明确的型号继续原样保留。
- [澄清集成测试](../../backend/tests/integration/test_v4_clarification_flow.py)：新增待办 + `auto` 的零模型调用、待办不变、三个动作选项以及 `new_question` 不泄漏旧待办且可建立新待办的检查；保留原有继续补充合并、取消、失败回滚、线程隔离和下游失败恢复检查。
- [入口分析测试](../../backend/tests/unit/test_v4_query_analysis.py)：检查上下文提示包含最少历史、当前条件优先及未确认条件保护要求。
- [前端待办交互](../../frontend/src/pages/Chat.tsx)：明确提示未选择动作时系统不会猜测消息与待办的关系，保留继续补充、开始新问题、取消待办三个按钮及显式动作提交。
- [前端测试](../../frontend/src/pages/Chat.test.tsx)：检查三个按钮、动作发送、取消空输入、失败保留待办和新的“不猜测关系”提示。
- [隔离检查运行器](../../output/run_query006_checks.py)：根据阶段标签把 B 阶段测试记录保存到独立的 `phase-b-20261010` 目录；A 阶段默认路径保持不变。

图和记忆层的动作状态转换沿用阶段 A 已实现的契约并在本阶段联调验证：`continue_clarification` 合并原待办、确认补充和当前补充；`new_question` 屏蔽旧待办；`cancel` 零模型/工具并清除待办；入口模型或下游失败时恢复请求前的待办版本。

## 实际验证命令与结果

### 后端阶段 B 针对性检查

最终命令在 `C:\path\agentic-rag\backend` 工作目录执行：

```text
D:/newsoft/python.exe output/run_query006_checks.py phase-b-backend-04 \
  --basetemp=C:/path/agentic-rag/output/query-rewrite-v1/phase-b-20261010/pytest-tmp-04 \
  -q tests/integration/test_v4_clarification_flow.py \
  tests/unit/test_v4_query_analysis.py tests/unit/test_v4_thread_state.py \
  tests/contract/test_chat_stream_api.py tests/contract/test_chat_request_deadline.py
```

- 退出码：0
- 结果：**52 passed**，1 个既有 pytest 缓存目录权限 warning；无测试失败
- 记录：[phase-b-backend-04.log](../../output/query-rewrite-v1/phase-b-20261010/phase-b-backend-04.log)、[phase-b-backend-04.json](../../output/query-rewrite-v1/phase-b-20261010/phase-b-backend-04.json)

此前同一批次的 `phase-b-backend-03` 也为 51 passed；新增提示保护测试后最终结果为 52 passed。第一次 `phase-b-backend-01` 因指定的 basetemp 父目录尚未创建而产生 setup 错误，没有进入测试断言；原始记录保留在阶段 A 输出目录，未覆盖。

### 前端阶段 B 检查

命令在 `C:\path\agentic-rag\frontend` 工作目录执行：

```text
npm test -- --run
```

- 退出码：0
- 结果：**8 个测试文件通过，23 tests passed**
- 记录：[frontend-test-01.log](../../output/query-rewrite-v1/phase-b-20261010/frontend-test-01.log)

本阶段没有运行前端生产构建；构建和前端全量回归属于阶段 D 的范围。

## 工程测试与真实质量的边界

后端检查使用 fake/scripted provider、确定性嵌入、临时数据目录和隔离 Qdrant；前端使用 Vitest/JS DOM。结果证明动作契约、状态隔离、失败回滚、提示内容和 SSE/API 映射的工程行为，不能证明真实模型一定正确补全指代、保留 `245 V / 400 ms` 条件或做出正确的文档答案。

本阶段未运行：

- 真实 Ollama 上的 RW07–RW10、RW18 入口补全验收；
- 005 阶段 C 的两道历史失败题复验；
- 阶段 C 的多问题完整答案和比较/条件推导验收；
- 前端生产构建、D 阶段全量回归；
- 30 题正式平台评测或正式索引重建。

根目录 [CURRENT_FAILURES.md](../../CURRENT_FAILURES.md) 未修改；其中记录的 `400 ms` 数字失真和历史超时问题仍未被本阶段的 fake/mock 测试解决或重新判定。

## 任务状态与下一阶段

`tasks.md` 已勾选 T012–T016；T017–T035 保持未开始。下一阶段 C（T017–T021）处理最多三个独立问题、共同条件/依赖/比较目标承载，以及单分支与多分支汇总的完整原题回答。

**报告后暂停，等待用户验收。**
