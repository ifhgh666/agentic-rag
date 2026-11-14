# Implementation Plan: 018 按工具需求分流聊天

**Branch** `codex/model-driven-agent-loop` · **Date** 2026-11-13 · [规格](spec.md)

## Summary

阶段 A 在当前聊天图首节点加入模型工具需求判断。直接回答复用会话历史及 SSE 答案。知识库分支先改写并判断信息充分性，然后按现有研究与聚合流程执行。

## Technical Context

Python、FastAPI、LangGraph 与现有结构化输出接口，React/Vite 继续消费现有 SSE。状态保存在原有内存 checkpoint。验证使用既有隔离 pytest 及 Vitest，保持真实评测、正式数据和当前服务进程的授权边界。无新技术依赖。

## Constitution Check

阶段 A 完成后保存报告并暂停。普通回复允许使用通用知识或已有会话内容。专属文档问题仍由现有证据路径回答。分流结果不含推理正文，现有工具准入、来源与请求日志边界适用。

## Project Structure

- `backend/app/rag/` 管理结构化分流、直接回答、改写和图路由。
- `backend/app/core/` 投影答案和真实过程事件。
- `frontend/src/features/chat/` 为实际新增的节点提供进度和过程名称。
- [调研](research.md)、[状态](data-model.md)、[SSE 契约](contracts/chat-routing.md)、[验证指南](quickstart.md)和[任务](tasks.md)与此阶段对应。
