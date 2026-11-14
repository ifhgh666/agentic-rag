# Quickstart: 云兼容端点的结构化输出兼容

验证本功能需要两类证据：**离线工程检查**（可重复、不花钱）与**真实端点运行**（证明能真正完成问答）。二者不可互相替代。

## 前置条件

- 后端依赖已安装；本机 Python 为项目当前使用的解释器（本机实测 `D:\newsoft\python.exe`，3.12.4）。
- 真实运行需要：用户自备的云兼容端点配置（`backend/.env` 中的 `LLM_PROVIDER=openai_compatible`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`），以及已就绪的本地索引（`/api/health` 返回 `index_ready=true`）。
- 真实运行会消耗端点额度；不要用正式知识库做破坏性操作。

## 一、离线工程检查（工作目录 `backend`）

```powershell
python -m pytest -q tests/unit/test_model_provider.py
python -m pytest -q tests/unit tests/contract tests/integration tests/security
```

预期：新增用例覆盖契约 §2/§3/§4/§5；全量回归无新增失败。若全量耗时过长，至少须运行提供商单元测试与受影响调用方（入口分析、循环、汇总）的既有测试。

## 二、真实端点验证（证明 SC-001~SC-003）

1. 启动后端（工作目录 `backend`）：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. 健康检查：`GET http://127.0.0.1:8000/api/health` 应返回 `index_ready=true`。

3. 通过正常登录态提交一个知识库内有依据的问题（例如 `PX-200 的过流保护阈值是多少？`），观察：

   - SSE 事件序列中出现 `answer` 且有至少一个来源；
   - 不再出现 `error` + `complete(status=failed, reason=model_unavailable)`；
   - 请求轨迹中可见 `structured_mode` 与 `structured_fallback`；
   - 端到端耗时不超过 300 秒。

4. 直接对端点确认行为差异（可选，用于定位）：

   - 严格模式请求应被端点拒绝（400）；
   - 通用 JSON 模式请求应返回合法 JSON。

## 三、本地路径回归（证明 SC-004）

```powershell
python -m pytest -q tests/unit/test_model_provider.py tests/unit/test_v3_3_query_analysis.py tests/unit/test_v4_query_analysis.py
```

预期：本地与测试提供商路径结论与改动前一致。

## 四、判定与记录

- 通过：SC-001（真实回答 + 来源）、SC-002（连续 3 次入口分析结构有效）、SC-003（回退可见且请求次数 ≤ 2）、SC-004（本地路径无回归）。
- 不通过：保留原始采集（请求标识、事件序列、耗时、用量）与失败原因，不得改写为通过。
- 报告须写明：本次是否使用测试外壳、是否改动环境、哪些结论来自真实端点、哪些仅来自离线检查，并在报告后暂停等待用户验收。

## 五、明确的非目标

- 不提高 300 秒整次期限或 120 秒单次等待；
- 不新增依赖、不修改 `requirements.txt`；
- 不修改前端、索引格式、知识库数据与 008 的展示结论；
- 不把本地模型性能问题算作本功能缺陷。
