# 启动与最小真实问答测试

日期：2026-10-22。授权：用户明确要求“启动测试”。本轮为 P3 完成后的运行核验，不是再次重构或原失败题正式复验；没有新建功能、修改产品代码、提交/推送或更改原阶段验收结论。

**结论：前后端启动、现有索引就绪、前端 API 转发与最小真实问答链路可用。首答阈值正确，但引用核验为 issue_found，不能宣称质量全面通过。报告后暂停，等待用户验收。**

## 当前运行状态

| 项目 | 实际结果 |
|---|---|
| 前端 | http://127.0.0.1:5173/ 返回 200；React 问答台可显示，Node PID 53376 |
| 后端 | http://127.0.0.1:8000/api/health 返回 200，status=ok、index_ready=true，Python PID 49200 |
| 前端代理 | http://127.0.0.1:5173/api/health 最终返回 200、index_ready=true |
| 实际模型配置 | openai_compatible / deepseek-flash，接口 api.deepseek.com；不是 README 所述的 Ollama 当前模式 |
| Ollama | 原进程已监听 11434，未停止或用于此次问答 |
| 服务停止点 | 前后端保持运行；没有删除、重建或上传测试文件到正式知识库 |

初次启动前 8000/5173 均未监听，使用已有 Python/Node/依赖隐藏启动，没有安装或升级。首次后端 PID 50732 正常启动，随后仅重启此任务自己的后端为 49200，以修正本次进程网络环境。该次重启之前没有提交平台问答；重启会清空进程内会话/缓存，旧服务在本次启动前并未运行。

## 连接问题与本次处理

启动环境存在 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY=127.0.0.1:7897。通过默认环境请求 DeepSeek /models 得到 ConnectError；trust_env=false 直连同一接口为 200，模型清单包含 deepseek-flash。由此定位为环境代理连接问题，没有改用 Ollama 或其他提供商。

只给新后端进程 NO_PROXY 添加 api.deepseek.com、127.0.0.1、localhost，原系统代理、父工具进程环境和 backend/.env 未修改。隔离冒烟进程使用相同绕过项。**因此以后按原环境另行启动时，仍需保留该进程绕过项或修复原代理；本轮没有持久化网络配置。**

首次前端代理健康请求在 5 秒内 ReadTimeout；服务就绪后及后端重启后均得到 200。浏览器唯一控制台错误是 favicon.ico 404，未见 React 应用错误；本轮没有顺手修改图标。

见 [首次 HTTP 记录](../../output/startup012/20261022-011329/http-first.json)、[模型初次连接](../../output/startup012/20261022-011329/provider-models.json)、[直连与代理核对](../../output/startup012/20261022-011329/connectivity-detail.json)、[最终健康记录](../../output/startup012/20261022-011329/http-running.json)、[浏览器截图](../../output/startup012/20261022-011329/browser-workspace.png)和[页面快照](../../output/startup012/20261022-011329/browser-workspace.yml)。

## 一次最小真实问答

使用真实已配置 DeepSeek 模型，FastAPI TestClient 经正常认证→PDF 上传/处理→chat SSE 路由执行；测试应用、用户凭证、PDF 和 Qdrant 全部位于本轮 output 隔离目录。没有将此题提交到正式知识库服务，也没有把真实文档或标准答案集发给模型。

测试 PDF 唯一事实：`PX-200 overcurrent protection threshold is 16 A.`

问题：`What is the PX-200 overcurrent protection threshold?`

- 登录 HTTP 200、上传 HTTP 202；合成文档 ready，隔离索引 ready。
- chat HTTP 200，仅提交一次、无外层自动重试；request_id=`74478665-f660-47bc-b2d9-30a93d95725c`，终态 completed / model_answered。
- 首答核心为“PX-200 的过流保护阈值为 16 A”，并返回 startup-synthetic.pdf 来源。模型另扩写动作时间、可调性和容差等资料缺口；原始内容保留，没有重试选择更好答案。
- 请求耗时 **14514 ms**，整个隔离流程 15389 ms；模型调用 **4 / 8**，工具 **3**，云调用 4。节点为入口 1、orchestrator 3。
- 用量：输入 5606、输出 563、合计 6169 Token，usage_source=mixed；不把 mixed 计量称为全部提供商实测。模型时间 12173 ms。
- 核验卡：evidence_status=found、citation_status=**issue_found**、numeric_status=not_evaluated、completeness_status=not_evaluated。返回重复来源，其中一个页码未知；引用卡异常尚未修复，不把“流程 completed”解释为引用/语义质量全部通过。

此次真实的是模型推理；测试索引用 deterministic 嵌入与 sparse fallback。它证明最小 API 链路，不证明真实 Dense 语义检索、全部正式 PDF 或原 Q16/C-UV 失败题已通过。正在运行的正式服务仍使用原 fastembed 配置，其 index_ready=true 也不等于全库答题质量通过。

首次证据：[请求与边界](../../output/startup012/20261022-011329/smoke-attempt.json)、[原始 SSE](../../output/startup012/20261022-011329/smoke-first.sse.txt)、[解析事件](../../output/startup012/20261022-011329/smoke-first-events.json)、[结果及用量](../../output/startup012/20261022-011329/smoke-result.json)、[执行脚本](../../output/startup012/20261022-011329/startup012_smoke.py)。没有覆盖 CURRENT_FAILURES 或原始失败记录。

## 实际命令与改动核对

| 操作 | cwd / 命令 | 结果 |
|---|---|---|
| 后端启动/进程重启 | backend：`D:/newsoft/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`，Start-Process -WindowStyle Hidden，日志重定向 | 最终 PID 49200 监听；启动命令单元退出 0，服务保持运行故没有进程结束码 |
| 前端启动 | frontend：`C:/Users/ifhgz/nvm/nodejs/node.exe node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort`，隐藏窗口/独立日志 | PID 53376 监听；启动命令单元退出 0，服务保持运行 |
| 连通性 | 根目录 Python/httpx：GET 本机 health、前端页面/代理 health；带配置凭据的 GET DeepSeek /models 不保存头/密钥 | 原连接失败/超时保留，最终本机与直连请求成功 |
| 浏览器 | Playwright navigate/snapshot/screenshot http://127.0.0.1:5173/ | 页面可见，favicon 404 单列 |
| 真实隔离冒烟 | 根目录：`D:/newsoft/python.exe C:/Users/ifhgz/AppData/Local/Temp/startup012_smoke.py` | 退出 0；passed 仅表示 HTTP/终态/16/来源最低条件，引用卡异常单列 |
| 源码/配置核对 | 根目录 Python hashlib 对照启动前 208 项文件 | 退出 0，产品/测试源码、.env、配置示例、包/锁文件、功能指针和 CURRENT_FAILURES 均未改 |

核对脚本首次用 Windows 默认 GBK 读取含中文 JSON 时发生 UnicodeDecodeError，已显式 UTF-8 读取；没有为此重跑模型。原始命令轨迹和 [核对记录](../../output/startup012/20261022-011329/source-and-command-check.json)保留。

启动命令和 PID：[启动记录](../../output/startup012/20261022-011329/launched-processes.json)、[进程代理绕过/重启记录](../../output/startup012/20261022-011329/backend-relaunch.json)。日志：[后端最终 stderr](../../output/startup012/20261022-011329/backend-direct.stderr.log)、[后端初次 stderr](../../output/startup012/20261022-011329/backend.stderr.log)、[前端 stdout](../../output/startup012/20261022-011329/frontend.stdout.log)。本轮没有改项目实现、依赖或已有 .env；仅新增运行证据与本报告。

可以从 http://127.0.0.1:5173/ 打开系统。下一步若需要处理引用核验异常或进行正式库真实问答验收，应另行明确范围；本轮不自动诊断修改或继续更多题。

**报告后暂停，等待用户验收。**
