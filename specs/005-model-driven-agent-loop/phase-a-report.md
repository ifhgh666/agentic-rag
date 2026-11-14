# 阶段A：协议与预算验收

2026-10-08，分支`codex/model-driven-agent-loop`。146个既有源码文件和差异保存于output/loop005-baseline/；11个正式知识库文件哈希已冻结。忽略文件覆盖Python/Node、本地配置和运行数据；无AGENTS.md及扩展钩子；005前置检查通过。

先执行新增协议测试，2项失败准确暴露Ollama工具ID丢失和兼容提供者返回形状差异。修复后执行：

`D:/newsoft/python.exe -m pytest -q backend/tests/unit/test_model_loop_protocol.py backend/tests/unit/test_model_loop_budget.py backend/tests/unit/test_model_provider.py`

15项通过。完整assistant/tool消息与统一调用形状、线程原子配额、汇总/辅助槽保留、工具和截止时间均有覆盖。

真实探测命令：`D:/newsoft/python.exe backend/scripts/smoke_model_loop.py`。本机qwen3:4b-instruct，原生tools、4096上下文、768输出预留。隔离资料，不改正式库，无云端。第一次14.21秒，输入197/输出25 tokens，主动调用search_child_chunks；第二次3.28秒，输入261/输出21，收到配对工具结果后给出正确试验参数JSON。原始记录：output/smoke-loop005/native-protocol.json。

结论：阶段A通过，可以进入阶段B。这个两调用探测证明协议可用，不证明完整Loop的检索质量、引用稳定性或30题效果。真实冒烟额度已使用1个请求/2次调用，总上限6请求。
