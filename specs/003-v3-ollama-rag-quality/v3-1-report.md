# V3-1 阶段验收：恢复 PDF 结构与索引质量

日期：2026-09-27。**结论：V3-1 验收通过，停在本阶段；没有进入 V3-2。**

## 已交付

1. **结构化 PDF 解析**：使用 `pymupdf4llm.to_markdown(page_chunks=True)`，按页保存 Markdown，清理重复页眉和页码；保留中文标题、表格行及准确页码。无可选中文本的扫描件仍明确拒绝，OCR 不在本阶段。
2. **Parent/Child 质量**：按 Markdown 标题及编号层级划分 Parent；短 Parent 合并，长 Parent 均衡切分，Child 在长度上限内带重叠。测试 PDF 的 `extracted.md` 现在包含 6 个真正章节标题和参数/问答表，不再把 `300 ms`、`16 A`、`3 年` 当作章节。
3. **真实本地 Dense**：默认使用 FastEmbed ONNX 多语言模型 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`（384 维），缺少本地模型时明确报错，不悄悄退回哈希向量；`EMBEDDING_BACKEND=deterministic` 仅保留作离线测试。此次模型已缓存到 `backend/data/models/`，无需 PyTorch（本机 PyTorch 曾出现 DLL 初始化错误）。本机 `backend/.env` 已保留其他配置，仅将嵌入模型/模式和 Child 尺寸调整为 V3-1 配置。
4. **索引版本闸门**：`backend/data/index/manifest.json` 记录解析/分块版本、嵌入模型及维度、源 PDF 哈希、Child 哈希和 Point 数；版本或数据不一致时 `index_ready=false`，拒绝使用旧索引。提供先预览、备份后显式执行的 `python -m scripts.reindex_v3 --apply` 迁移入口。
5. **重建旧 Point**：验收中复现并修复 Qdrant 本地“删除集合后同名重建仍残留旧 Point”的问题。现在重建前按 Point ID 清空并校验数量，防止失效文档再次混入。

## 正式数据与验证

| 指标 | V3-0 旧状态 | V3-1 当前状态 |
|---|---:|---:|
| 测试 PDF 可提取页数 | 4 | 4 |
| 正确识别的编号章节 | 0/6 | 6/6 |
| Parent / Child | 13 / 14 | 7 / 8 |
| Qdrant 集合 Point | 50（含 36 条失效文档） | 8（仅当前 PDF） |
| 真实 Dense | 哈希向量 | FastEmbed 多语言 ONNX |
| 四道基线题关键事实进入 Top-5 Child 或对应 Parent | 不稳定 | **4/4**，独立测试索引验证 |
| 后端全量测试 | V2 记录为 64 passed | **73 passed** |
| 编译检查 | — | 通过 |
| 正式服务 `/api/health` | 重建前 `index_ready=false` | **`index_ready=true`** |

对原测试 PDF 的第 2–4 页使用 Poppler 渲染并目视核对了中文字体、章节、参数表、保护表和问答表；Markdown 中关键中文词和数值无乱码。新增测试覆盖页码、标题/表格、误判数值标题、小/大 Parent、Child 边界、缺少模型不暗中回退、源文件/配置/Point 不匹配及重建重复累积。

执行的主要验证命令：

```powershell
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/tests backend/scripts
cd backend
python -m scripts.reindex_v3
python -m scripts.reindex_v3 --apply
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

正式重建前的可恢复备份位于 `backend/data/backups/v3-1-20260927-120509-076522/`；最终重建前另有 `v3-1-20260927-120728-c67b2e/`。较早的 `v3-1-20260927-120449-4f3824/` 来自首次备份尝试，不作为首选恢复点。备份均保留，未删除用户原始 PDF。后端已在本机 `127.0.0.1:8000` 重新启动，前端未改动。重启会清空 V2 进程内会话记忆。

## 变更范围

- 解析与切分：`backend/app/knowledge/pdf_parser.py`、`chunker.py`；
- 嵌入与索引：`backend/app/config.py`、`rag/embeddings.py`、`rag/index_store.py`、`rag/vector_db_manager.py`、`app/main.py`；
- 配置、依赖与迁移说明：`backend/requirements.txt`、`.env.example`、本机 `.env`、`backend/README.md`、`backend/scripts/reindex_v3.py`；
- 新增/更新解析、分块、嵌入、索引和真实检索测试。

## 阶段边界与未完成事项

- 本阶段证明的是**证据召回**，不是“最终答案 4/4 正确”。V3-0 找到的编排器“任意短 Child 导致只选一个 Parent”问题、答案生成和评估误判仍未在 V3-1 修改；这些属于后续证据选择/回答阶段。
- 本阶段未接入 Ollama、未调用云端问答 API；Ollama 适配从 V3-2 开始，须由用户另行确认。
- 新机器没有本地 ONNX 模型时，按 `backend/README.md` 手动准备模型，再上传/重建索引；应用不会自动联网下载模型。
- V3 目录目前没有 `tasks.md`，Spec Kit 前置脚本会错误地定位到 V2；本阶段按明确的 V3 计划单独实施与验收，未勾改 V2 任务。
