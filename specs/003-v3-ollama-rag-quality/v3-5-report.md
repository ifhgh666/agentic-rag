# V3-5 阶段验收：模型成本与质量闸门

日期：2026-09-28。**结论：V3-5 验收通过；V3 计划已完成，本轮停在此阶段。**

## 本阶段交付

- 增加请求级原子模型调用预算：默认简单问题最多 **2 次**，复杂或多问题最多 **4 次**；查询分析、证据缺口改写、上下文压缩、最终回答各默认最多 **1 次**。并行 Agent 共用同一预算，不能分别绕过总上限。预算耗尽时，不再请求模型；有证据则列出带来源的原文摘录并明确“未生成综合结论”，无证据则说明信息不足。
- 每请求输出 `usage` SSE 事件和 `rag.usage` 结构化日志：记录 prompt、completion、总 Token，模型调用次数、各节点调用数、缓存命中数、模型耗时及请求耗时。Ollama 返回用量时使用提供商实测值；缺失时使用估算并标记来源。事件和日志不含提示词正文、私有推理或密钥。
- 新增有界内存缓存：查询分析按 `thread_id + 问题 + 对话背景 + 索引版本` 复用；证据缺口改写按 `thread_id + 问题 + 已检索问题 + 索引版本` 复用；检索结果按规范化问题、Top-K、分数阈值和索引清单版本复用。缓存默认 300 秒、最多 256 项；索引清单变更会使旧检索结果和查询缓存键失效。请求内重复工具/Parent 访问仍沿用单飞去重，并计入命中统计。答案缓存为可选项，本阶段未启用，以避免复用过期或缺失来源的回答。
- 前端过程面板增加本次模型调用、输入/输出和总 Token、实测/估算标记、缓存命中、耗时及预算提示；显示实际发生的模型调用与阶段，不再显示未独立执行的“问题表示”占位阶段，也不把未知耗时伪装为 `0 ms`。本地模型不可连接、超时、未配置或索引未就绪时展示安全的失败原因，不暴露异常中的文档内容。
- 增加统一八场景回归入口：四道真实 PDF 基线题、无证据、同线程追问、多事实、冲突证据。对明确型号的并列问题增加狭窄的误澄清保护，避免本地小模型偶发把清晰的“双问题”直接打回；真正指代不明的问题仍需澄清。

## 验证

- 后端：`cd backend; python -m pytest -q` → **117 passed**；`python -m compileall -q app tests scripts` 通过。
- 前端：`cd frontend; npm test -- --run` → **8 passed**；`npm run build` 通过。
- 本地 Ollama 统一回归：`cd backend; python -m scripts.smoke_v3_5_regression` → **8/8 通过，云端模型调用 0 次**。四道真实 PDF 问题仍为 **4/4**，每题 1 次本地回答调用；复杂双事实样例 2 次调用，未超过 4 次上限。该脚本只使用临时索引或隔离证据，不修改正式知识库。
- 强制压缩预算：`cd backend; python -m scripts.smoke_v3_4_baseline --only Q2 --threshold 400` → 通过。上下文估算由约 1654 Token 压至 252 Token；压缩与回答各 1 次，合计 **2/2 次**，答案仍引用原文的 **16 A / 100 ms**，没有云端调用。
- 自动化新增覆盖：并行预算原子性、节点上限、缓存容量/过期/索引版本失效、查询分析及重写缓存、实测与估算 Token 汇总、预算耗尽的证据型回退、SSE 用量与日志同一请求标识、失败原因脱敏、明确双问题误澄清保护，以及前端用量展示。

## 变更位置与运行

- 后端核心：`app/rag/cost_control.py`、`query_analysis.py`、`query_planner.py`、`retriever.py`、`index_store.py`、`tools.py`、`model_compression.py`、`generator.py`、`graph.py`、`graph_state.py`、`pipeline.py`、`app/config.py`。
- 前端：`src/pages/Chat.tsx`、`src/components/ProcessPanel.tsx`、`src/types/api.ts`、`src/api/client.ts`、`src/styles/app.css`。
- 配置、说明与测试：`backend/.env.example`、`backend/README.md`、`backend/scripts/smoke_v3_5_regression.py` 及相关单元、契约和集成测试。
- 本地启动仍使用 `backend/.env` 中的 `LLM_PROVIDER=ollama` 与已安装的 `OLLAMA_MODEL`。后端从 `backend` 目录运行 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`；前端从 `frontend` 目录运行 `npm run dev`。如后端已使用 `--reload`，代码更新会自动载入；正式数据未被本阶段重建。

## 边界与未完成事项

- 正式知识库的 PDF、Qdrant 索引和 `backend/.env` **没有被修改**。若正式库仍使用 V3-1 之前的索引，须停后端后按 V3-1 的预览、备份及重建步骤处理，不能把临时索引 4/4 等同于正式库验收。
- 缓存位于单进程内存，重启会清空；多进程部署不共享缓存。图执行目前是同步运行，SSE 在图完成后回放实际轨迹，不是逐节点实时推送。失败发生在模型提供商尚未返回用量时，无法获得该次调用的实测 Token。
- 规则型答案评估不是独立事实评审；未加入在线 RAGAS 或 Judge Model，以免增加每次问答的成本。小模型仍可能波动，八场景回归需要在模型或索引升级后重跑。
- V3 目录仍没有 `tasks.md`；Spec Kit 前置脚本会误指向 V2。本阶段按已批准的 V3 `plan.md` 执行，未修改 V2 任务。`.specify/extensions.yml` 不存在，无扩展钩子需要执行。
