# Validation Guide

根目录使用已安装 Python；不安装/升级依赖，不启动服务。

```powershell
python output/eight014/phase-a/run.py before-full
python output/eight014/phase-a/run.py focused tests/unit/test_rag_architecture.py tests/unit/test_graph.py tests/unit/test_prompt_consumers.py tests/unit/test_model_call_governance.py tests/unit/test_v3_7_procedure_evidence.py
python output/eight014/phase-a/run.py after-full
```

每轮标签唯一，记录 argv/cwd/退出码、guard hash 与日志，不覆盖失败。before-full 仅合并前可用。guard 禁 dotenv/网络/Dense/正式数据 I/O/原生 PDF；仅允许 Windows 内部 socketpair。完整轮保留两项旧措辞失败；24 PDF skip、2 Dense deselect 不算通过。源码审计核对八文件、符号/算法/提示/前端/历史保持及静态依赖无环。
