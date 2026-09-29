# V2-2 阶段验收报告：Sparse + Hybrid Retrieval

**日期**：2026-09-23

## 已交付

- 加入 `qdrant-client[fastembed]>=1.14.2,<2.0`，默认使用 `Qdrant/bm25`。
- 新增延迟加载的 `SparseEmbeddingService`，把 FastEmbed 输出转换为 Qdrant `SparseVector`。
- Qdrant Child collection 同时保存 `dense` 和 `sparse` 两个命名向量；Parent 仍只保存在文件型 Parent Store。
- 使用 Dense/Sparse 两路 Prefetch 和 Qdrant DBSF Fusion 查询。
- `IndexStore` 能把 V2-1 Dense-only collection 或旧 `vectors.npy`/`children.json` 迁移为混合 collection。
- 检索结果增加 `retrieval_mode=hybrid`，debug/retrieve 接口会随结果返回该字段。
- 默认检索配置更新为 `top_k=7`、`min_score=0.4`，模型、向量名和 collection 均由配置管理。

## 验证命令与结果

```powershell
cd C:\path\agentic-rag
python -m pytest backend/tests/unit/test_sparse_embeddings.py backend/tests/unit/test_vector_db_manager.py backend/tests/unit/test_index_store.py backend/tests/unit/test_retriever.py -q
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/tests
```

结果：定向测试 `8 passed`；后端完整测试 `35 passed`；编译检查通过。

真实运行验收：

- FastEmbed `Qdrant/bm25` 已成功加载并完成缓存。
- 混合 Qdrant collection schema 和 Fusion 查询已通过本地验证。
- 停止旧服务后启动新代码，Dense-only collection 已自动迁移为混合 collection。
- Qdrant collection `document_child_chunks` 实测包含 `dense`、`sparse` 两个命名向量，
  共 35 个 Child Points。
- `GET /api/health` 返回 `index_ready=true`；`admin / 135436` 登录成功；
  `POST /api/debug/retrieve` 返回 `retrieval_mode=hybrid`，技术词查询可返回结果。

## 阶段边界

本阶段没有实现 LangGraph、Tool Calling、Agent Loop、上下文压缩、会话记忆或新的前端流程。
下一阶段是 V2-3，需用户明确继续后再开始。
