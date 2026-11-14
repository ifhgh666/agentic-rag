# 017 A：Nova 基础、居中登录与公共框架

日期：2026-10-29（America/Phoenix）。授权来自用户“先把上面的写成计划然后执行”；按根 AGENTS.md 的单阶段规则，本轮仅生成完整计划并实施 A=tasks Phase1–3/T001–T015。

**结论：A 工程交付完成，待用户验收。56 项前端测试、19 项主浏览器检查和3项补充检查通过，类型/构建、依赖白名单与实际依赖树审计通过。问答、知识库和日志的页面改版仍在 B/C，D 全站矩阵未执行。报告后暂停，等待用户验收。**

## 计划与交付

- 按项目 specify→plan→tasks→analyze→implement 流程建立 [规格](spec.md)、[计划](plan.md)、[任务](tasks.md)、[研究](research.md)、[数据模型](data-model.md)、[界面契约](contracts/ui-workspace.md)、[验证指南](quickstart.md)。保存 [居中登录](design/login-centered-preview.png)、[问答](design/chat-preview.png)、[知识库](design/knowledge-preview.png)、[日志](design/logs-preview.png) 四张确认图；图中示例数据没有注入产品。
- 29项任务覆盖12项功能要求与5项验收标准；规格质量12项通过，一致性静态及人工语义核对没有阻断项。A的15项有完成证据；B/C/D共14项保持未勾选。
- 登录按最后修订图实现白底单列、整组水平/垂直居中，短屏允许滚动；移除左侧介绍。复用原认证与token，增加密码显示、防同步重复提交、错误/加载和autocomplete。
- 公共框架采用Lucide、Nova Button/Sheet、本地品牌标识；桌面240px可折叠至72px，移动端Sheet具备Escape、焦点返回和键盘循环。保留hash导航与退出，不放静态数量或未接通的全局“新会话”按钮。
- 健康状态读取已有公开GET /api/health，区分检查/连接/离线与索引状态；可见时30秒轮询，focus重新检查，新请求/卸载取消旧读取。健康401不清令牌；原受保护接口401仍清令牌，有真实Axios接缝单测及浏览器补充证明。
- 接入Tailwind4.3.3/Vite插件4.3.3与本地base-nova源；React18和Vite6保持。新增运行依赖固定为BaseUI1.9.0、cva0.7.1、cn0.5.0、Lucide1.64.0、Motion14.7.1，均有当前使用点。Node最低版本同步为22。未提前安装Zustand、可调面板、Markdown或dnd-kit。
- 官方组件原始registry、MIT和hash保留，本地仅适配React18 ref、导入、图标与中文关闭文本；Geist两档字体与OFL自托管。新样式与旧页面的legacy-content作用域隔离，移除运行时Google字体请求。旧问答的静态“本地知识模式”标记由样式隐藏，框架状态取实际健康响应。

主要源码：frontend/src/pages/Login.tsx、components/AppLayout.tsx、components/ui、BrandMark/MotionProvider、hooks/use-service-health、api/client.ts及health类型、styles/app.css/tokens.css/legacy.css、scripts/check-deps.mjs与dependency-policy.json。入口、Vite配置、package/lock同步；构建生成的vite.config.js和tsbuildinfo亦有变化。

## 实际命令与验证

根工作目录：C:/Users/ifhgz/Desktop/agentic-rag。npm命令在frontend目录；run-check.mjs只负责保存原命令输出和退出码，不改变命令语义。实际Git分支保持codex/model-driven-agent-loop；Spec Kit指针为017，不创建、提交或推送分支。.specify/extensions.yml不存在，无前后hooks。

| 实际命令/工具 | 退出状态 | 结果与证据 |
|---|---:|---|
| create-new-feature.ps1 -Json -Number 17 -ShortName frontend-nova-workspace；setup-plan.ps1 -Json；setup-tasks.ps1 -Json | 均0 | 新功能及活动模板，完整文件已落盘 |
| check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks | 0 | 全部设计/任务可定位 |
| node output/frontend017/phase-a-20261029-01/inspect-plan.mjs | 0 | 17要求/29任务、覆盖100%、无静态问题；人工核对宪章/边界 |
| 修改前 npm test -- --run；npm run build | 均0 | [40 passed基线](../../output/frontend017/phase-a-20261029-01/baseline-tests.log)、[构建基线](../../output/frontend017/phase-a-20261029-01/baseline-build.log) |
| 新行为实现前定向Vitest | 1 | 12项未实现检查失败，[原记录](../../output/frontend017/phase-a-20261029-01/red-tests.log)保留 |
| npm install --save-exact 五项A运行依赖；npm install --save-dev --save-exact 两项Tailwind依赖 | 均0 | 显式output缓存，固定版本和现有锁；不改全局npm配置 |
| npm test -- --run（最终） | 0 | [11文件/56 passed](../../output/frontend017/phase-a-20261029-01/a-final-tests.log) |
| npm run build（最终，含tsc -b） | 0 | [构建日志](../../output/frontend017/phase-a-20261029-01/a-final-build.log) |
| npm run check:deps | 0 | [依赖检查](../../output/frontend017/phase-a-20261029-01/a-final-deps.log)：8项直接运行依赖，单一React/ReactDOM，无未使用新增运行依赖 |
| node output/frontend017/phase-a-20261029-01/check-guard.mjs | 0 | [5个隔离检查](../../output/frontend017/phase-a-20261029-01/dependency-guard-checks.json)：正常输入通过，未批准依赖/重复React/未使用Motion/绕过UI封装均被拒绝 |
| npm ls --all（首次） | 1 | [原日志](../../output/frontend017/phase-a-20261029-01/a-final-tree.log)：隐藏缓存虚列未安装的可选WASM分支 |
| 保存失效隐藏缓存后 npm ls --all | 0 | [实际磁盘树](../../output/frontend017/phase-a-20261029-01/a-tree-after-cache.log)，没有加包或改版本；[处理说明](../../output/frontend017/phase-a-20261029-01/npm-cache-resolution.md) |
| Playwright受控API主检查 | 19项通过 | [结构化结果](../../output/frontend017/phase-a-20261029-01/browser-check.json) |
| Playwright补充检查 | 3项通过 | [健康401/焦点循环/短屏](../../output/frontend017/phase-a-20261029-01/browser-supplement.json) |
| node output/frontend017/phase-a-20261029-01/verify-evidence.mjs | 0 | [200保护文件、12前端原业务文件、SSE正文、UTF-8/链接、源码hash](../../output/frontend017/phase-a-20261029-01/protection-and-docs.json)均无异常 |
| git diff --check -- frontend | 0 | 无新增空白格式问题；Git提示既有LF/CRLF转换信息，不是失败 |

### 截图与预览

- [实装登录1440px](../../output/frontend017/phase-a-20261029-01/login-desktop.png)、[实装登录390px](../../output/frontend017/phase-a-20261029-01/login-mobile.png)、[短屏390×520](../../output/frontend017/phase-a-20261029-01/login-short.png)。
- [公共框架桌面](../../output/frontend017/phase-a-20261029-01/shell-desktop.png)、[移动导航](../../output/frontend017/phase-a-20261029-01/navigation-mobile.png)。框架截图中的旧问答内容尚未进入B改版。
- 本轮仅新启Vite：npm run dev -- --host 127.0.0.1 --port 5173 --strictPort；服务位于http://127.0.0.1:5173/，保留供用户查看。没有启动/重启后端。

浏览器接口全部拦截为隔离响应，账号/密码均为测试值；验证登录成功/失败、密码显示、三页导航、索引未就绪、离线、桌面折叠、移动打开/选择/Escape/焦点、退出、减少动态效果和短屏。不向实际后端发送问答、上传或删除。401/503控制台错误是刻意注入的失败场景；Motion开发提示减少动态效果已启用；没有页面运行异常。

## 首次失败与修复

1. 新CSS首次构建失败：旧Google字体URL含分号，初始提取错误留下500等CSS片段。修正为整行移除后独立构建通过。[原失败](../../output/frontend017/phase-a-20261029-01/build-first-failure.log)保留；不把组合命令末尾check:deps的0当成构建通过。
2. 浏览器采集脚本最初使用不可用的require、路由匹配误拦Vite源码，以及过于精确的像素/即时焦点判断；调整工具适配、精确API前缀、减少动态效果和异步焦点等待。最终检查/截图单列，原问题记录见[采集记录](../../output/frontend017/phase-a-20261029-01/browser-harness-first-attempts.log)。
3. npm隐藏树缓存包含磁盘上不存在的可选WASM节点。只将node_modules/.package-lock.json移动到证据目录保存后重扫，完整npm ls退出0；项目package-lock、版本和直接依赖未因这次修复改变，没有添加五个无使用点的包。

## 包体、保护与限制

| 构建资源 | 修改前 | A最终 |
|---|---:|---:|
| JS | 224.98kB / gzip75.33kB | 438.86kB / gzip150.12kB |
| CSS | 26.74kB / gzip6.38kB | 58.44kB / gzip12.28kB |
| 自托管字体 | 远程请求 | 本地45.23kB+46.30kB |

组件可访问交互、Motion与兼容样式带来体积增加；本轮没有声称性能提升。后续逐页迁移将移除旧兼容样式，B再按实际消费安装其余库。首次安装/取回源码字体用过网络，运行时字体自托管，不宣称首次准备完全离线。

200项后端/配置/016报告及旧失败hash保持，12项原前端业务/测试文件未改；client中StreamEvent起的SSE正文完全一致。既有锁文件中已存在包的版本变化为零。正式知识库与索引未操作；真实模型/Judge调用为零；未运行后端全量测试、不将模拟UI结果当作模型质量结论。016最新真实质量的11通过/4未通过保持。

目前无未解决的A工程失败；[当前失败边界](CURRENT_FAILURES.md)记录已修问题和后续未执行范围。真实管理员与真实后端登录联调未在本轮进行，浏览器模拟结果不替代它。768/1920px及四页全状态矩阵留D。

## 下一阶段及停止点

A/T001–T015交付待验收；B/T016–T021将实现Zustand当前会话、连续对话、可调证据面板、Markdown/复制、全局新会话及跨轮隔离。C文档/日志、D全站验收均未实施。本轮不自动进入B。

**报告后暂停，等待用户验收。**
