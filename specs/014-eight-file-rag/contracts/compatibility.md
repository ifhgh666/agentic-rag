# Compatibility Contract

旧模块路径移除，不建立 forwarding 文件、sys.modules 别名或隐藏 helper 包。符号迁移表由实际 AST 生成，包含全部原顶层能力；新导入仅来自八文件。应用/脚本/测试同步迁移，仓库外调用者按表改路径。

各类/函数名称、合法参数/返回、缓存身份、budget/lease/deadline、工具与 SSE 语义保持。输入模型 JSON schema 与生产 prompt 内容保持。结构检查和 monkeypatch 定位适配归属变化，不能弱化业务断言或掩盖旧失败。模型提供商、资源关闭/索引锁和单飞缓存 seam 保持原类。

入口采集器的源码指纹清单同步改为 nodes/schemas/tools/prompts 和采集脚本。旧批次记录不修改，旧布局与当前源码混用仍返回 continuation_code_mismatch，不将架构迁移视为允许复用旧冻结批次。
