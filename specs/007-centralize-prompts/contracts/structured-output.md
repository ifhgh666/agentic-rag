# 入口结构化调用契约

日期：2026-10-13。适用007本轮A补充，授权来自用户“那你先补好这个”。

1. 唯一入口schema为backend/app/rag/schemas.py的QueryAnalysis。三个必填字段：is_clear严格bool、questions为list[str]且最多3项、clarification_needed为非null的str，extra=forbid。字段description说明清楚时1–3问/空澄清、不清楚时空问题/具体澄清。原有strip、长度、重复与状态联动validators保持，不新增语义检测。
2. prompts.py的get_rewrite_query_prompt只返回业务规则；不含JSON示例、字段名/类型/格式段。动态上下文仍是原user消息，不把schema字符串追加回prompt。
3. ChatProvider.complete与complete_model增加可选response_schema:type[BaseModel]|None；入口显式传QueryAnalysis，其他调用不传。无该参数的提供方不能静默以普通生成代替绑定。
4. Ollama用with_structured_output(response_schema, method="json_schema", include_raw=True)。原始可展示首答/usage保留，ModelResult新增可选structured_output。兼容接口显式传response_format={type:json_schema,json_schema:{name,schema,strict:true}}，仅在原显式配置模式下使用；本轮无云端连接。
5. complete_model保留同一总等待保护，并按schema取得严格结构化对象；无效/截断/缺字段/额外字段/联动失败均保留raw但structured_output为空，入口继续invalid_model_output。提供方拒绝绑定按现有model_unavailable，timeout按现有timeout，不公开解析异常正文，不增加重试或修复模型调用。
6. 入口按结构化对象读取字段，原题/动作/历史/续补/缓存与结果输出契约保持。提示版本、json_schema模式和schema哈希进入缓存；输入保守估算包含schema。取消、待办auto及预算/窗口阻断仍为零调用。
7. 公共API/SSE字段和失败码保持，B已接入其他10提示函数，正文及其模型调用模式保持。工程记录不证明真实模型遵守保真，也不修改旧题集、首答或失败记录。报告后暂停，等待用户验收。

## 2026-10-13 补充R：字段状态生成约束修复

外部API/SSE保持，模型仍只返回三个字段。QueryAnalysis.model_json_schema()根object附两个完整anyOf对象分支：is_clear=true只能1–3问及clarification_needed=空串；false只能空questions及非空澄清。每个分支完整列出properties/required/additionalProperties=false，避免语法编译器只读取分支时丢失结构限制。Ollama及显式兼容接口绑定函数保持；拒绝新schema仍按现有失败码，不降级/重试。后置校验、strip及重复检查不变。
