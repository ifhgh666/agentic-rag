# 文脉后端

完整工作台在仓库根目录运行 `python start.py`。[快速开始](../README.md#快速开始)

## 单独运行

需要 Python 3.11+。首次配置时，在 `backend/` 从 `.env.example` 创建 `.env`。本项目使用通过 OpenAI 兼容接口接入的 DeepSeek，当前模型 ID 为 `deepseek-flash`。[配置样例](.env.example)

```dotenv
LLM_PROVIDER=openai_compatible
LLM_MODEL=deepseek-flash
LLM_BASE_URL=
LLM_API_KEY=
```

填入服务商提供的接口地址和密钥。如果服务商提供的模型 ID 不同，按它的实际值填写。然后在 `backend/` 的 Python 虚拟环境中启动服务。

```powershell
python -m pip install -r requirements.txt
python -m scripts.start_local
```

服务监听 `127.0.0.1:8000`，本地演示账号为 `admin / 123456`。知识库和索引默认存于 `backend/data/`。[API 文档](http://127.0.0.1:8000/docs)

## 测试

```powershell
python -m pytest -q tests/contract
```

手动运行 Uvicorn、完整回归和索引迁移见[测试与运行指南](../docs/testing-and-operations.md)。
