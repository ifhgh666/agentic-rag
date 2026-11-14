# Tasks: 019 简化本地启动

## 阶段 A

- [x] T001 在 specs/019-simple-startup/ 保存规格、计划及启动契约。
- [x] T002 [US1] 在 start.py 添加配置初始化、依赖准备、启动检查和进程管理。
- [x] T003 [US2] 在 backend/scripts/start_local.py 添加固定演示账号、嵌入资源准备及本地 Uvicorn 入口。
- [x] T004 [US1] 更新 backend/.env.example、README.md 和 docs/testing-and-operations.md 的本地启动说明。
- [x] T005 [US2] 在 backend/tests/contract/test_local_startup.py 验证固定登录、错误密码、Token 和本机边界。
- [x] T006 验证根启动器、认证和健康检查，保存 specs/019-simple-startup/phase-a-report.md。

T001 → T002/T003 → T004/T005 → T006。
