# R 模型传输兼容契约

2026-10-27，适用于正常参考图的 `core/reference_model.py`。原公共 Chat/SSE 契约不变。

- 仅 `openai_compatible` 且精确模型标识为 `deepseek-flash` 时，工厂默认传入 `extra_body={"thinking":{"type":"disabled"}}`；模型所有用途继承，不依赖每个调用者补参数。
- 入口仍通过 SDK `function_calling`、原 QueryAnalysis schema 和指定工具解析，研究仍使用原生 bind_tools；普通调用与流式绑定继承相同 transport body。
- 不新增提示/schema、HTTP/SSE 字段、公开错误正文、业务重试或 provider 回退；max_retries=0，当前模型/端点/凭据/温度/种子和 `.env` 文件不变。
- 其他模型标识与 Ollama 不传 thinking 字段。不把当前精确标识的实测结果推广到其他 DeepSeek 别名。
- SDK 假 HTTP 接缝可复现缺少开关时的 400；真实通过须由不带临时 override 的产品工厂和独立知识库完成，并保留原始答案、来源、usage 与错误。
