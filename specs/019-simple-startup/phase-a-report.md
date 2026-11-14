# 019 阶段 A 简化本地启动

2026-11-14。T001–T006 工程完成，等待用户验收。

[根启动器](../../start.py)创建缺失的示例配置、准备依赖并管理两个服务。[后端入口](../../backend/scripts/start_local.py)准备本地 Dense 嵌入资源，从原有设置加载模型，并为本机启动启用 `admin / 123456`。密码哈希和 JWT 签名密钥由进程自动生成。快速开始使用 [OpenAI 兼容接口配置](../../backend/.env.example)。

## 验证

| 根目录命令 | 退出与结果 |
| --- | --- |
| `pwsh -NoProfile -File .specify/scripts/powershell/resolve-template.ps1 spec-template` 和 `setup-plan.ps1 -Json`、`setup-tasks.ps1 -Json`、`check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 各 0。首次模板调用误传 `-Name`，改用位置参数后通过。 |
| `python -X utf8 output/reference016/phase-a/run.py simple-startup-20261114-01 tests/contract/test_local_startup.py tests/contract/test_auth_api.py tests/unit/test_reference016_model.py` | 0，13 项通过。见[测试日志](../../output/reference016/phase-a/simple-startup-20261114-01.log)。 |
| `python -X utf8 -m py_compile start.py backend/scripts/start_local.py` | 0。 |
| `python -X utf8 start.py` | 1，报告现有 8000 端口被占用。既有前后端继续运行。 |
| `python -X utf8 -u output/simple-startup-019/smoke.py output/simple-startup-019/local-5hum0_8d/frontend/node_modules` | 0。独立目录与端口下，首次配置初始化、后端健康、前端代理、固定账号登录、错误密码、受保护文档接口、进程退出和配置保留均已验证。见[启动日志](../../output/simple-startup-019/local-sk624087/launcher.log)。 |

早期联调复现了本机 Conda 虚拟环境加载 SSL DLL 失败，启动器改为使用当前 Conda 解释器和项目内隔离依赖目录。后续验证也修正了客户端等待及 Windows Ctrl+Break 清理，最终两项服务均释放监听端口。历史运行日志保留在 `output/simple-startup-019/`。

联调运行了实际 Uvicorn 和 Vite，模型及嵌入使用隔离替身、依赖复用已安装版本。首次联网下载和真实问答未复测。现有 `backend/.env` 指纹一致，现有服务没有切换。后续可用本机启动器验证现有接口配置。

**报告后暂停，等待用户验收**。
