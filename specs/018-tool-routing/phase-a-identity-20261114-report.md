# 018 A 补充修正：文脉助手身份

2026-11-14。工作台原直接回复提示仅定义通用助手角色。用户询问模型身份时，截图记录了底层模型将自己称为 DeepSeek 最新版模型。

[提示](../../backend/app/rag/prompts.py)将自身名称、身份、能力与模型问题分流到直接回复，明确产品身份为「文脉 · PDF 知识工作台」的知识助手。技术细节仅使用已确认的系统信息，会话历史不作为模型身份依据。变更限定于分流和直接回复提示，以及对应测试。

从仓库根目录执行 `python -X utf8 output/reference016/phase-a/run.py assistant-identity-focused-20261114-01 tests/unit/test_reference016_model.py tests/unit/test_reference016_graph.py tests/contract/test_reference016_stream.py tests/integration/test_reference016_session.py`，退出 0，32 项通过。模拟 SDK 请求验证“你好”“你是谁”“你是什么模型”均携带文脉身份提示，直接回答请求不绑定工具。见[日志](../../output/reference016/phase-a/assistant-identity-focused-20261114-01.log)。

后续运行验收范围为重启后端并用真实模型核对两个身份问句。当前阶段仅做隔离验证，服务仍需重启加载身份提示。

**报告后暂停，等待用户验收**。
