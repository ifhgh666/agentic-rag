# V3-2 阶段验收：Ollama 模型适配层

日期：2026-09-28。**结论：V3-2 验收通过，停在本阶段；未进入 V3-3。**

## 交付内容

- 统一 `ChatProvider.complete` 与 `ModelResult`，分别适配本地 `ChatOllama`、显式选择的 OpenAI-compatible 接口、离线 `FakeProvider`。
- 默认 `LLM_PROVIDER=ollama`，本地地址限制为环回 HTTP；保留原云端配置，但不会在 Ollama 故障时回退调用。
- 新增 `QueryAnalysis` 结构化输出契约，包含 `is_clear`、最多 3 个 `questions` 和 `clarification_needed`；实际查询分析留给 V3-3。
- `model_call` 执行事件记录调用节点、原因、耗时、输入/输出 Token 估算与提供商实际返回的计数；不记录提示词或密钥。
- 增加本地连通性、工具调用、中文回答、超时、云端隔离和离线测试；`scripts/smoke_ollama.py` 可重复执行真机验收。
- 旧测试夹具明确启用离线 Sparse 编码，避免从本机 `.env` 继承联网配置。

## 验证结果

- 后端全量测试：**83 passed**；`python -m compileall -q backend/app backend/tests backend/scripts` 通过。测试中的 Ollama 离线/超时场景不触发云端回退。
- 本机 Ollama **0.34.4** 已安装并启动；最终模型 `qwen3:4b-instruct`（2.5 GB）下载完成、摘要校验通过，`backend/.env` 当前明确选择该本地模型。原 `qwen3:4b` thinking 版只用于对比试验，因实际会把分析文本混入回答正文，已用精确模型名 `ollama rm qwen3:4b` 删除；可重新下载恢复。
- 最小问答 `python -m scripts.smoke_ollama`：模型返回“PX-200 的过流保护阈值是 16 A。”；**7.8 秒，实际输入/输出 87/18 Token，估算 87/14 Token**。同次验收中成功发起 `search_child_chunks` 工具调用，答案为简短中文且无 `<think>` 文本。
- 隔离端到端 `python -m scripts.smoke_ollama_api`：临时知识库上传合成 PDF，走完整问答接口，答案包含 **16 A**。`/api/logs` 记录 `model_call`，节点为 `collect_answer`、提供商为 `ollama`，**6.8 秒，实际输入/输出 92/16 Token，估算 101/12 Token**。正式 Qdrant 未被打开或重建。
- 正式后端 `/api/health` 保持 `status=ok`、`index_ready=true`；前端可访问。原云端密钥保留在本机 `.env`，但 Ollama 模式的提供商选择只创建本地客户端，地址只允许本机环回 HTTP。

## 问题与处理

1. 首次下载模型在约 929 MB 时遇到网络 EOF，重试后完整下载并校验；后续 instruct 版也下载成功。
2. `qwen3:4b` thinking 版即使请求关闭推理，仍可能输出长篇分析。单靠删 `<think>` 标签无法清理未标记的分析，因此改用 [Qwen 官方注明只支持非思考模式的 4B Instruct 2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)，并保留标签清理作为额外防护。
3. 全量测试曾有 4 项旧索引测试因继承本机 `.env` 的 Sparse 在线设置而连接模型源失败；测试夹具改为显式离线后，全量复测 **83/83 通过**。生产 Sparse 配置未被改动。
4. 初版端到端验收脚本导入默认应用时碰到正式 Qdrant 独占锁；现于导入前将默认实例和测试实例分别隔离到临时目录，复测通过，无正式索引写入。

## 阶段边界

V3-2 只解决模型接入与最小验收；不改 V3-3 查询分析编排、不保证四道基线题的最终答案 4/4 正确。V3 目录没有 `tasks.md`，Spec Kit 前置检查会定位到 V2；本阶段按 V3 计划单独实施，未修改 V2 任务。
