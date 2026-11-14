# 019 A 配置清理补充

2026-11-14。用户要求清除本地密钥配置文件中旧的密码哈希及不再需要的项目。本次为既有本地启动入口的配置清理，登录实现和 Agent 行为保持原状。

## 完成内容

- 本地 `backend/.env` 定向移除 24 项：由启动器生成的认证参数、未使用的 Ollama 配置、退出当前在线链的旧模型限制和循环参数。使用内存中的修改前配置逐项核对，所有保留值、模型连接字段、嵌入后端和知识库路径一致；没有输出或保存这些值到报告。
- `backend/.env.example` 同步删去旧认证字段及失效参数，保留当前生效的模型、嵌入、检索、分块、日志和运行配置。
- `docs/testing-and-operations.md` 说明示例面向 `python start.py`，研究边界来自当前图常量；直接运行 Uvicorn 的认证参数由环境另行提供。

## 验证

| 根目录执行的命令 | 结果 |
| --- | --- |
| `python -`（定向清理与内存校验） | 退出 0。保留字段值逐项一致；运行时生成的 `admin / 123456` 验证通过。 |
| `python -X utf8 output/reference016/phase-a/run.py env-config-cleanup-20261114-01 tests/contract/test_local_startup.py tests/contract/test_auth_api.py` | 退出 0，4 项通过。记录位于 `output/reference016/phase-a/env-config-cleanup-20261114-01.log`。 |
| `python -`（清理后的本地与示例配置解析） | 退出 0。两份配置均可解析，旧字段消失，固定账号的运行时认证参数有效。 |
| `git diff --check`、`git check-ignore backend/.env` 和 `git ls-files -- backend/.env` | 退出 0。本地密钥文件被忽略且未跟踪，Git 交付仅包含示例、说明和本报告。 |

认证检查使用实际密码校验、JWT 与隔离 HTTP 客户端，应用模型和嵌入使用替身。未运行真实问答，未接触正式索引或重启现有服务。此前启动与模型质量记录保留其原有结论。

本次没有待实现项，也不新增后续功能阶段。

**报告后暂停，等待用户验收。**
