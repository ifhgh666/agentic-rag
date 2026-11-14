# 006阶段A实施基线

日期：2026-10-10。授权：仅阶段A（T001—T011）。本文件在产品代码修改前生成。

- 原工作区修改与未跟踪文件已完整留存；不还原、不清理。
- Git分支：`codex/model-driven-agent-loop`。原功能导航为005，阶段A按用户明确授权定位006。
- 已有文件：324份；正式知识库PDF/Markdown/Parent/索引清单指纹：11份。
- `.env`仅保存哈希，未复制或公开其内容；配置只记录下列非敏感白名单。

```json
{
  "llm_provider": "ollama",
  "ollama_model": "qwen3:4b-instruct",
  "max_simple_llm_calls": 8,
  "max_llm_calls_per_request": 12,
  "max_query_analysis_calls": 1,
  "max_tool_calls": 16,
  "request_timeout_seconds": 300.0,
  "llm_timeout_seconds": 120.0,
  "model_context_window": 4096,
  "max_context_tokens": 3072,
  "llm_max_output_tokens": 768,
  "model_context_safety_tokens": 256,
  "rag_cache_ttl_seconds": 300,
  "rag_cache_max_entries": 256,
  "max_question_chars": 2000
}
```

详细基线：[baseline.json](../../output/query-rewrite-v1/phase-a-20261010/baseline.json)；既有差异保存在同目录worktree-before.diff，修改前文件副本在before/。

005 C真实验收仍未通过，T018未完成、D未启动。Q16两次400ms改错、C-UV原超时及未复验状态继续以根CURRENT_FAILURES.md和005报告为准。本轮只做工程检查，不更新这些真实失败结论。

后续核对正式库、配置、旧失败记录与阶段外文件哈希；仅把本轮获准修改单独列出，不将历史diff作为本轮改动。
