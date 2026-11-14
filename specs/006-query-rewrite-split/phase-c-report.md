# 006 阶段 C 报告：拆分与完整原题回答

日期：2026-10-10  
授权范围：仅执行阶段 C（T017–T021）  
前置阶段：阶段 A、阶段 B 已完成并分别有阶段报告  

## 阶段目标与停止点

本阶段处理最多三个独立需求的拆分、共同条件和条件依赖传递、比较目标保留，以及单分支/多分支答案汇总和调用预算。阶段 D 的全量工程回归、阶段 E 的真实入口验收和阶段 F 的真实端到端补测均未启动。

**报告后暂停，等待用户验收。** 不自动进入阶段 D。

## 实际改动

- `backend/app/rag/query_analysis.py`
  - 在现有单入口提示中明确：只有独立信息需求才拆分；共同型号、数字、单位、时间等条件要复制到相关子问。
  - 明确“是否触发/如果发生”等依赖条件不能改成已发生。
  - 明确 A/B 比较可以拆成检索子问，但原题比较目标必须交给最终汇总。
  - 明确超过三个独立需求时返回澄清，不得静默删除第四项；未增加 Python 语义分类或额外模型调用。

- `backend/app/rag/generator.py`
  - 强化答案和多分支汇总提示：原始问题是完整目标，分支答案只是材料；最终回答要覆盖共同条件、条件性恢复和比较结论，不能简单拼接。
  - 汇总载荷保留原有 `分支汇总：` 协议前缀，新增 `original_question` 和汇总约束说明，保持 fake 测试适配器兼容。

- `backend/tests/unit/test_query_rewrite_v1.py`
  - 增加 RW11–RW14 的拆分契约检查、RW15 的四问澄清检查，以及提示中共同条件、依赖、比较和容量约束的检查。

- `backend/tests/unit/test_v3_3_multi_agent.py`
  - 检查两个独立分支分别检索、每个分支同时收到原题和自己的子问、最终汇总收到原题；更新待办续答测试使用已批准的显式 `continue_clarification` 动作。

- `backend/tests/unit/test_model_loop_budget.py`
  - 检查 1/2/3 个分支分别获得 5/4/3 次分支额度，以及多分支保留一次汇总额度、单分支不保留汇总额度。

- `backend/tests/unit/test_graph.py`
  - 检查单分支不会额外调用 `final_synthesis`。

- `specs/006-query-rewrite-split/tasks.md`
  - 仅勾选 T017–T021；D/E/F 任务保持未完成。

## 实际验证命令与结果

最终命令在 `C:\Users\ifhgz\Desktop\agentic-rag\backend` 执行：

```powershell
python -m pytest --basetemp C:\Users\ifhgz\Desktop\agentic-rag\output\query-rewrite-v1\phase-c-20261010\pytest-tmp-final -q `
  tests/unit/test_graph.py `
  tests/unit/test_query_rewrite_v1.py `
  tests/unit/test_model_loop_budget.py `
  tests/unit/test_v3_3_multi_agent.py `
  tests/unit/test_model_loop_stage_c.py `
  tests/unit/test_v4_query_analysis.py `
  tests/unit/test_v4_query_schema.py `
  tests/unit/test_v3_3_query_analysis.py `
  tests/contract/test_chat_stream_api.py
```

- 退出码：0
- 结果：**115 passed**
- 原始记录：[phase-c-backend-final.log](../../output/query-rewrite-v1/phase-c-20261010/phase-c-backend-final.log)
- `git diff --check`：退出码 0。
- 初次未指定工作区临时目录的基线命令受本机 `C:\Users\ifhgz\AppData\Local\Temp\pytest-of-ifhgz` 权限限制而退出 1；没有把该环境错误当成测试失败。随后使用仓库 `output/query-rewrite-v1/phase-c-20261010/` 下的独立 `--basetemp` 重跑并得到上述结果。

## 工程测试与真实质量的边界

本阶段测试使用 fake/scripted provider、确定性嵌入和隔离测试目录。结果证明拆分输出协议、分支路由、原题承载、汇总调用隔离、共享证据缓存和 5/4/3 分支预算的工程行为。

这些测试不能证明真实 Ollama 在中文语义拆分、共同条件复制、`如果触发` 条件推理、A/B 比较或数字保真方面一定正确。真实模型、真实索引和真实回答质量仍未评估；没有生成分数或时延结论。

本阶段未运行：

- 真实 Ollama 入口验收和 RW11–RW16/RW18 人工逐项验收；
- 005 阶段 C 中 `245 V / 400 ms` 数字失真和 PX-200 欠压超时两道历史失败题复验；
- 30 题正式平台评测；
- 正式知识库重建、`backend/.env` 修改或生产数据操作；
- 阶段 D 全量后端回归、前端构建及阶段 E/F。

根目录 `CURRENT_FAILURES.md` 未修改，历史失败证据保持不变。

## 任务状态与下一阶段

`tasks.md` 已勾选 T017–T021。下一阶段 D（T022–T029）负责公共 API/SSE 契约、日志与截止时间、前端显示、必要全量工程回归和 D 阶段报告；只有用户验收本报告并明确指示后才可开始。

**报告后暂停，等待用户验收。**
