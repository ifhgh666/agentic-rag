# V2-1 阶段验收报告：Qdrant Dense Migration

**日期**：2026-09-23

## 已交付

- 增加 `qdrant-client>=1.14.2,<2.0` 依赖。
- 增加 `VectorDbManager`，支持本地 Qdrant collection 创建、Dense upsert、查询、计数和按文档删除。
- `IndexStore` 保留 V1 接口，底层查询改为 Qdrant，不再使用 FAISS 查询。
- 首次启动自动读取旧 `vectors.npy` + `children.json` 并迁移到 Qdrant。
- 增加 Qdrant 路径、collection 和 Dense 向量名配置。
- 增加 Qdrant 单元测试、旧索引迁移测试和测试目录隔离。

## 验证命令与结果

```powershell
cd C:\path\agentic-rag\backend
pytest -q
```

结果：`32 passed`。

真实服务验收：

- `http://127.0.0.1:8000/api/health`：`status=ok`，`index_ready=true`。
- `admin / 135436` 登录：HTTP 200。
- `/api/debug/retrieve`：能从 `document_child_chunks` 返回 Child 检索结果。
- Qdrant 数据目录：`backend/data/qdrant`。

## 阶段边界确认

本阶段没有实现：Sparse BM25、Hybrid Retrieval、LangGraph、Tool Calling、Agent Loop、
上下文压缩、会话记忆或新的前端 Process 流程。

## 未完成事项

- V2-2 需要在本阶段 Dense collection 基础上加入 Sparse 向量和 Hybrid 查询。
- 本地 Qdrant 只支持单进程访问；若以后需要并发服务，应切换到 Qdrant Server/Cloud，
  但这不属于 V2-1。
