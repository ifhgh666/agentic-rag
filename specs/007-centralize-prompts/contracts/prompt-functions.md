# Contract: rag/prompts.py 函数

当前[实际 prompts.py](../../../backend/app/rag/prompts.py)是生产提示唯一来源，保留9个固定提示函数，并提供入口、分支、证据、预算与结构化回退的参数化消息模板。原先的两类模型压缩提示已删除，证据侧只由[context_compression.py](../../../backend/app/rag/context_compression.py)提供 Token 估算与动态阈值。消费者显式导入所需函数；模块不调用模型，不读取 `.env` 或用户数据，不产生网络/文件副作用。

| 函数 | 入参 | 返回正文及消费者 |
|---|---|---|
| get_rewrite_query_prompt | 无 | 完整入口提示；QueryAnalyzer |
| get_conversation_summary_prompt | max_chars:int，取原memory设置 | 原summary JSON提示及同一上限；conversation_summary |
| get_orchestrator_prompt | protocol:str，native或structured，取原settings | 原Loop提示及适用兼容附文；agent_loop |
| get_aggregation_prompt | 无 | 原grounded答案/引文JSON提示；generator._grounded_request |
| get_answer_generation_prompt | 无 | 原基础生成提示；generator.generate_with_result |
| get_retrieval_rewrite_prompt | 无 | 原单检索目标提示；query_planner兼容调用 |
| get_answer_repair_prompt | feedback:str，原异常反馈 | 原生成修正消息；generator |
| get_loop_repair_prompt | feedback:str，原异常反馈 | 原Loop协议/引文修正消息；agent_loop |
| get_aggregation_instruction | 无 | 原payload.instruction；generator汇总 |

动态当前题、历史、summary、pending、证据和预算通过消息模板函数参数传入，固定标签与指令不留在消费者中。工具schema及其description仍由`tools.py`维护，输出字段说明仍由`schemas.py`维护。既有参数合法性由原设置/调用控制，模块不新建运行时语义校验；修正反馈仍只作原有消息的一部分。

消息role、顺序、预算和错误处理不由prompt模块改变。2026-10-13用户授权入口结构化补充：QueryAnalyzer传response_schema=QueryAnalysis，Ollama使用with_structured_output的json_schema模式；入口prompt不再包含格式段。其他调用保留原路径。入口协议query-rewrite-v1保持；REWRITE_PROMPT_VERSION用于缓存与工程报告，不混同fixture版本，不修改真实采集器。见[结构化调用契约](structured-output.md)。

用户审阅入口是 canonical `get_rewrite_query_prompt()` 全文，已同步[prompt-review](../prompt-review.md)。所有消费者直接使用`app.rag.prompts`；不存在单数`prompt.py`、`rag_agent`转发包或第二份提示正文。A2的双包过程保留在[架构整理报告](../phase-rag-agent-architecture-20261018-report.md)，当前单包契约以[A3报告](../phase-single-rag-package-20261018-report.md)为准。
