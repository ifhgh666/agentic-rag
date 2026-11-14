# 验证指南

## E 真实联调交付（2026-11-02）

实际链路与2题首答通过，原答/用量/截图及限制见[阶段E报告](phase-e-report.md)。本次已有integration-started.json，采集器禁止静默重跑；后续重测必须另存新批次并保留本次。
证据目录output/frontend017/phase-e-20261102-01；新增的E由用户明确选择，下面A–D不调用真实后端的表述均属历史。

1. python -X utf8 output/frontend017/phase-e-20261102-01/prepare_assets.py：生成中文文本PDF并复开/渲染校验；复制并验证真实Dense/BM25缓存，冻结2题、资料与非敏感模型快照，LLM调用0。
2. node output/frontend017/phase-e-20261102-01/integrate.mjs：启动自有隔离FastAPI和Vite代理，真实浏览器失败/成功登录、上传等待处理、两个首答及跨页、删除/退出。每题300秒外部watchdog，不设假响应。
3. 读取raw SSE和完整原答，对照72小时/45天、实际来源与调用/用量；记录失败、未运行及限制；不自动重试。
4. 比较181项源码/配置和11项正式资料文件hash，仅停止本轮服务，保存phase-e-report.md后暂停。若有必要产品修复，才补相关工程测试/构建。

## D工程交付（2026-11-02）

88项前端测试、31项受控浏览器检查、构建及依赖审计通过；清理前后六组计算样式一致。见[D报告](phase-d-report.md)。以下为本轮实际执行矩阵，截图与退出状态保存在同一证据目录。

仅Phase7/T027–T029，证据目录 `output/frontend017/phase-d-20261102-01/`。复用既有批准范围，不新增模型/后端或正式数据操作。

1. 先保存181项源码/配置/历史资料指纹，当前88项前端测试与构建基线，以及三页在390/1440px的截图和计算样式。受控API及合成SSE只用于浏览器展示。
2. 确认无legacy-content消费者后，移除legacy.css及导入和两条兼容规则；对照六份计算样式，保护已确认的页面效果。
3. 三页逐一检查390/768/1440/1920px、长文本、CSS200%内容放大及720×500 CSS/DPR2等效浏览器200%，无页面横向溢出。CSS内容放大允许文档垂直滚动到输入；等效浏览器缩放检查输入位于当前视口内，知识库表格局部滚动。
4. 登录键盘/密码切换/Enter与退出；问答Shift换行/Enter、代码与表格局部滚动、过程和完整原文；知识库键盘交集筛选、表格滚动、删除取消/Tab圈定/Escape/焦点返回。
5. 三页reduced-motion与可见焦点；问答跨页不断流、两轮与旧日志跳转/新会话；不重新执行真实题集。
6. 最终Vitest/build/check:deps/npm ls、包体与来源/保护核对；保存phase-d-report.md后暂停。以下C/B节均为历史阶段验证说明。

## C工程交付（2026-10-29）

88项前端测试、22项受控浏览器检查、构建/依赖审计通过；命令退出码、失败修正和截图见[阶段C报告](phase-c-report.md)。下述是本轮已实际执行的C验证范围；后面的B矩阵保留历史范围。报告后暂停，等待用户验收。
仅Phase5/T022–T024，证据目录output/frontend017/phase-c-20261029-01。完整前端基线78项通过后，先验证新行为缺失，再实现并运行Knowledge定向/全量Vitest、build、check:deps与实际依赖树。浏览器使用隔离context接管全部/api请求：单PDF选择/拖入、多文件/非PDF拒绝、同文件重选、名称+状态交集、processing轮询至ready/failed、刷新失败保留列表、删除取消/错误/成功/防重入/焦点；390/768/1440/1920及200%/reduced-motion。合成文档/状态不进入真实知识库，不启动后端。保存phase-c-report.md后暂停，D三页最终矩阵留后续。

Node>=22，单npm锁文件。B使用独立受控浏览器API，不启动后端，不使用真实账号、真实模型或正式PDF。

## Spec Kit入口（根目录）
~~~powershell
.specify/scripts/powershell/setup-plan.ps1 -Json
.specify/scripts/powershell/setup-tasks.ps1 -Json
.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
~~~
已有017目录/计划不覆盖历史，extensions.yml不存在时全部hook跳过。B历史基线/截图/原始日志保存在output/frontend017/phase-b-20261029-01；C见本节顶部证据目录。

## 工程命令（frontend）
~~~powershell
npm test -- --run
npm run build
npm run check:deps
npm ls --all
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
~~~
若5173已有其他服务，保留它并选择5174。新增依赖使用项目output缓存及--save-exact，不改全局npm设置。每次执行保存独立日志及退出码。

## B矩阵
1. Enter/Shift/IME/229/repeat、双击/空输入/2000字/运行中禁止、新会话及失败恢复。
2. 两轮历史、累计answer替换、retrieval快照、Parent去重、请求身份隔离、并行同名工具、无ID独立事件。
3. 默认折叠及真实状态、Markdown/恶意HTML/图片/链接/表格/代码、复制成功/失败、完整原文页码。
4. 澄清默认补充/显式新题/取消、分析成功后失败仍pending、pending=false后失败不恢复。
5. 流期间切知识库并返回继续，退出abort与迟到忽略，刷新/新会话清空，EOF失败保留部分答案。
6. 两项导航及/logs替换/chat，无/api/logs请求；登录与知识库原兼容。390/768/1440/1920px、200%缩放、键盘、reduced-motion截图及控制台记录。
7. 对照before-hashes保护后端/配置/016报告/A报告与图片/Login/Knowledge；检查依赖版本、React唯一和包体。

受控API通过不代表真实模型质量；B/C/D各自阶段证据均已保存，D三页工程矩阵已完成；真实后端/模型尚未联调。报告后暂停，等待用户验收。
