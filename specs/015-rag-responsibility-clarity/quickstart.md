# Validation Guide

A 已在隔离条件下实施，当前待用户验收，原始命令、退出码与限制见 [阶段报告](phase-a-report.md)。本文件不构成后续阶段或真实评测授权。

工作目录为仓库根。复查时使用独立且未使用过的 label；运行器会拒绝覆盖已有证据：

```powershell
& D:/newsoft/python.exe output/clarity015/phase-a/run.py <新标签> tests/unit/test_rag_architecture.py
```

运行器在 backend 工作目录启动 pytest，禁用 dotenv，以 fake/scripted provider、deterministic embedding 和临时索引运行；保护真实 Dense 加载、普通网络连接、正式数据及原生 PDF 打开，同时允许 Windows asyncio 的内部 socketpair。

- 本轮迁移前完整：817 通过、2 失败、24 跳过、2 排除；迁移后完整：820 通过、2 失败、24 跳过、2 排除。
- 96 项定向、6 项保护证明、71 个应用/脚本模块的导入检查通过。
- 161 项定义 AST 等价、144 份非核心调用文件逻辑等价、51 个应用模块静态无环；提示/配置/前端及旧阶段报告保持。
- 两项旧提示措辞断言没有更改；24 正式 PDF 跳过、2 Dense 排除均未运行，不证明真实检索或真实回答质量。

A 只调整职责，不删除功能。B 的调用壳/重复投影/SDK 复用候选未执行；A 验收并明确指示后才进入。
