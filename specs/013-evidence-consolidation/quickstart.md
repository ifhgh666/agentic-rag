# Validation Guide

根目录使用已安装的 python/pytest，不安装或升级依赖。

```powershell
python output/merge013/phase-a/run.py before
python output/merge013/phase-a/run.py after
python output/merge013/phase-a/run.py related
```

运行器禁用 dotenv，设置独立 DATA_DIR、fake、deterministic 与 Sparse 本地兼容；保护插件拒绝网络、真实 Dense、正式数据 I/O 和原生 PDF。测试只使用合成/临时材料与固定 provider。每轮独立日志，拒绝覆盖结果；before 只能在实现前运行。

预期 before/after 旧集合保持、补充边界通过，related 覆盖间接调用。审计确认五函数四常量和旧 evidence 定义 AST 一致、旧模块和直接导入消失、29→28。真实质量、性能和运行中服务重新加载未测。
