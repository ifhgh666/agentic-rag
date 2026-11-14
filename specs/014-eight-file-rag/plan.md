# Implementation Plan: RAG 八文件收敛

**Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)
**Branch**: 继续 codex/model-driven-agent-loop，不创建/切换；setup-plan 回退目录名不代表实际分支。

**Status**: A 工程完成，见 [报告](phase-a-report.md)。

## Summary

将 28 份源文件收敛为八文件，保留所有内部类/函数 seam，以静态导入和符号归属建立依赖方向。不是将代码移到新 helper 包。旧模块入口移除，所有仓库内调用迁移；012/013 历史保持。

## Technical Context

**Language/Version**: 当前 Python 3.12，项目支持 3.11+。
**Primary Dependencies**: 全部复用，不新增/升级。
**Storage**: 不迁移正式数据；内存会话实现随状态归属保留。
**Testing**: pytest fake/scripted/假传输/受控时间；完整 unit/contract/integration/security。
**Target Platform**: Windows，保留 socketpair 自检与模型/数据保护。
**Project Type**: 既有 FastAPI/React 应用内部架构整理。
**Performance Goals**: 八个实际源文件，不承诺时延或内存提升。
**Constraints**: 提示/协议/预算/算法保持，不运行真实模型或重启服务；不拆生产 helper 包。
**Scale/Scope**: rag 全部模块，以及必要的 main/knowledge/observability 装配导入、脚本与测试迁移。

## Constitution Check

设计前后均通过：仅交付 A；文件内部继续保持解析/索引/检索/生成/治理职责的独立类与接口，合并文件不将其实现塞入流水线方法。原文证据、密钥/数据、可观察性和工程验证保持。无宪章例外。

## Project Structure / 归属表

| 目标 | 合并来源 |
|---|---|
| __init__.py | 保留轻量包说明 |
| edges.py | 路由，保持独立 |
| graph.py | graph + pipeline，保留 AgentGraphService/RagPipeline 各自职责 |
| graph_state.py | graph_state + conversation_memory，包括 PreparedQuery/MemorySnapshot/原子存取 |
| nodes.py | nodes + query_analysis + conversation_summary + agent_loop + generator + evaluator + query_planner（除 normalize_query）+ evidence |
| prompts.py | 生产提示保持原内容 |
| schemas.py | 原 schemas + 工具输入、ModelResult/PreparedAttempt/CallSpec/AttemptRecord/CallRecord/CallOutcome/AnalysisOutcome 纯契约 |
| tools.py | 原 tools + context_builder/context_compression/cost_control/model_provider/model_call/context_admission/embeddings/sparse_embeddings/vector_db_manager/index_store/retriever + normalize_query |

具体符号归属保存 output/eight014/phase-a/symbol-map.json。CallContext 含 budget.lease 行为，留 tools；PreparedQuery 归 graph_state；normalize_query 归 tools，避免 retriever→nodes；摘要归 nodes，避免状态→节点。graph→nodes→tools，各自只向低层 schemas/graph_state/prompts 依赖，edges 仅用状态。纯结果类依赖彼此时按定义顺序放置。

## 阶段与任务映射

仅实施阶段 A，tasks 全部为同阶段任务组。基线与文档 → 静态合并/显式依赖 → 调用迁移 → 定向检查 → 完整隔离回归 → 源码/符号/提示/历史审计 → 报告后暂停。

合并采用保存原代码片段的方式，不全仓格式化；仅必要 import/自模块引用和工具 normalize_query 归属改变。模型/工具 executor 仍仅一份。公共类名称保持，删除旧模块文件，不注册 sys.modules 兼容。单包计数与无循环是新增结构检查。

## Validation / 需求映射

FR-001/002、SC-001：八文件精确集合、旧路径扫描、装配导入。FR-003、SC-002：全部顶层符号去向、函数/类 AST 按导入迁移归一化对照。FR-004/005：完整回归，生产提示字节保持，前端源文件 hash 保持。FR-006、SC-003/004：012 最终 guard 复用，24 正式 PDF 用例跳过、两真实 Dense 用例排除并单列；两旧提示断言保留，失败不覆盖。FR-007：完整命令与不可覆盖证据/报告。

## Complexity Tracking

无新抽象。tools/nodes 预计分别约 2000/1500 行，实际行数在报告列明；保持内部职责类与受控依赖。导入路径变化是本次布局收敛的兼容代价，独立能力与算法保持。
