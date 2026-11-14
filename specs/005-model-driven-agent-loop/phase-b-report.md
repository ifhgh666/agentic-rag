# 阶段B：模型循环验收

2026-10-08。新增ModelAgentLoop已接入LangGraph主图；节点模块删除原程序构造搜索、240字Parent、结果非空/Parent即足够、型号正则重搜和固定两次搜索。每个ToolCall按ID回填，无来源终态先反馈协议问题，再由模型决定动作。工具身份、已知Parent白名单、只读执行、缓存和配额保留。

先运行新行为测试记录缺模块失败，再实现。`D:/newsoft/python.exe -m pytest -q backend/tests/unit/test_model_agent_loop.py`：7项通过，包含同证据不同动作、长非空继续检索、多工具单项错误、重复请求缓存、合法题设数字及最多一次引用修正。

真实命令：`D:/newsoft/python.exe backend/scripts/smoke_model_loop.py --loop --output output/smoke-loop005/native-loop.json`。隔离工具、qwen3:4b-instruct，3次本地模型调用，20.30/6.34/12.10秒，输入547/688/975 tokens。第一轮尝试直接终态，收到NEEDS_RETRIEVAL_ATTEMPT反馈；第二轮模型主动搜索，第三轮根据实际证据生成带定位引文的正确答案。程序没有代发搜索。原始消息与事件保留在该JSON。

架构与真实循环通过，可进入阶段C。真实冒烟累计2请求/5调用。主图接入回归15项中13项通过，剩余2项分别断言旧的编号布局、简单请求2次调用，属于本次已明确替换的旧预期，阶段C随接口完整回归更新；不能把这些旧断言当成新Loop的性能达标证明。

上下文采用全量原文注册、完整消息配对、显式物理窗口；超过窗口才让模型选择保留原文片段，未装载ID和来源记录可见，不能用词面排序伪装模型选择。完整正式库效果尚未评测。
