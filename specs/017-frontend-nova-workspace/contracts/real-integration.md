# E 真实联调契约

沿用现有GET /api/health、POST /api/auth/login、GET/POST/DELETE /api/knowledge/documents、POST /api/chat/stream和POST /api/auth/logout，不变更wire或产品接口。独立Vite仅代理真实隔离实例。

测试账号与JWT secret只存在于本轮进程；上传前清单为空，上传回执processing后必须从实际清单观测ready及块数。UI两轮各提交完整问题一次，SSE由当前产品公开协议驱动；克隆观测不替换响应、不传gold。原始答案/来源/用量、request/thread ID和时间戳可追溯。

删除只允许uploaded UUID及integration-e2e-017.pdf，先取消确认不删除，再确认真实DELETE；实际清单为空且debug/retrieve无该文档；退出后客户端token清除、原token被服务拒绝。不得对正式文档或账号执行此流程。

语义失败仍保留原答并在服务可用时继续第二题；超时/服务故障保留已收到事件，后续依赖项明确not_run。两题首答/对照完成即停止，不自动修复模型/改问/重试。每轮300s是采集上限，不是产品截止。
