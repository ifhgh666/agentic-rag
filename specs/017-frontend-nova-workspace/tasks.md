# Tasks: Nova 前端知识工作台

## Phase 8: US5 真实前后端与模型联调（E，2026-11-02工程完成待验收）
用户明确选择真实联调；五项工程完成待验收。真实浏览器/后端/模型链路及2题首答通过，8次模型/2次搜索；原27项完成与T025/T026撤销保持。见[阶段E报告](phase-e-report.md)和[原答对照](phase-e-answer-comparison-20261102.md)。
- [x] T030 [US5] 在output/frontend017/phase-e-20261102-01/保存源码/正式资料hash、生成并校验自建PDF、真实Dense/BM25预检和2题冻结协议；同步spec/plan/research/data-model/contracts/quickstart。
- [x] T031 [US5] 在output/frontend017/phase-e-20261102-01/实现隔离server.py与真实Vite代理/浏览器integrate.mjs，验证真实认证和上传→ready，不写正式配置或资料。
- [x] T032 [US5] 通过真实界面各首次提交两题，保存output/frontend017/phase-e-20261102-01/raw/公开SSE、原答/来源/usage及跨页记录；“最多2个请求”“每题单一300秒外部采集watchdog”，不重试、不注入预期。
- [x] T033 [US5] 只取消/确认删除本轮上传UUID，核对真实空清单/空检索/退出，保存HTTP/UI证据；不改模型、提示或历史质量结论。
- [x] T034 [US5] 保存逐题原答与正确事实对照、保护/进程清理及specs/017-frontend-nova-workspace/phase-e-report.md，更新导航后暂停。

E依赖：T030→T031→T032→T033→T034。准备/评分/保护不增加模型请求；必要集成缺陷工程修复与原始真实结果分开记录。无新技术选型，研究仅只读；不越过E或自动扩充正式题集。

2026-11-02：既有D/T027–T029工程完成待验收；移除无消费者的旧样式，88项前端测试、31项受控浏览器检查、构建及依赖审计通过。A–D工程任务已交付，T025/T026仍为撤销，见[D报告](phase-d-report.md)。报告后暂停，等待用户验收。

2026-10-29：A/T001–T015与B/T016–T021记录保持；用户明确“继续执行”后，C/T022–T024工程完成待用户验收。88项前端测试、22项受控浏览器检查及构建/依赖审计通过，见[C报告](phase-c-report.md)。D仍未执行。

**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[界面契约](contracts/ui-workspace.md)、[quickstart.md](quickstart.md)。
**A-D历史授权边界（2026-11-02）**: 用户在C交付后明确“继续”，本轮只执行既有D=Phase7/T027–T029：无消费旧样式清理、三页最终矩阵与工程审计。A/B/C报告保持，不运行真实后端/模型、不操作正式文档、不提交推送。`[x]`只表示实际工程证据，不表示用户验收。

## Phase 1: Setup（A）
- [x] T001 保存当前前端原文件/Git差异和后端/016失败记录保护hash到 `output/frontend017/phase-a-20261029-01/`，运行修改前Vitest/build基线，记录实际退出码。
- [x] T002 按specify生成 `specs/017-frontend-nova-workspace/spec.md`、`checklists/requirements.md`，保存最终确认的四张图到 `design/`，明确居中登录及示例数据边界。
- [x] T003 按plan研究并生成 `specs/017-frontend-nova-workspace/plan.md`、`research.md`、`data-model.md`、`contracts/ui-workspace.md`、`quickstart.md`，复核宪章及依赖兼容。
- [x] T004 按tasks生成 `specs/017-frontend-nova-workspace/tasks.md`，通过check-prerequisites后按analyze只读核对FR/SC覆盖、阶段、状态与路径；分析结果纳入阶段记录。

## Phase 2: Foundational（A）
- [x] T005 在 `frontend/package.json`、`package-lock.json` 精确固定A实际用到的最小依赖，新增 `frontend/scripts/check-deps.mjs` 和白名单，阻止同职责重复、重复React和未使用的新运行依赖；Node>=22。
- [x] T006 下载并保存官方base-nova原始registry/许可证/hash；在 `frontend/src/components/ui/` 本地适配button/input/sheet最小集合，增加 `components/BrandMark.tsx` 和自托管字体/OFL。
- [x] T007 在 `frontend/src/styles/app.css` 建立统一neutral变量与Tailwind入口，原内容隔离到 `styles/legacy.css`，移除远程字体；配置 `vite.config.ts` 和公共Motion入口，保持旧页面业务。
- [x] T008 先在 `frontend/src/hooks/use-service-health.test.tsx` 建立健康状态/轮询/取消行为验证，再在hook、`api/client.ts`、`types/api.ts` 增加HealthResponse/getHealth与checking/online/offline投影；“轮询30秒，只在页面可见时读取，focus重新检查”，卸载/新请求取消旧读取。

## Phase 3: US1 居中登录与公共框架（A，P1）
**Goal**: 完成可独立演示的居中登录、Nova框架与真实健康状态。
**Independent Test**: 受控API下登录失败/成功/防重入、导航/退出、窄屏Sheet/焦点、健康离线/未就绪；旧页面只验兼容可用。

- [x] T009 [US1] 先在 `frontend/src/pages/Login.test.tsx`、`components/AppLayout.test.tsx` 建立有行为价值的验证并保存未实现时结果，健康验证继承T008；不以旧的常量断言冒充登录覆盖。
- [x] T010 [US1] 在 `frontend/src/pages/Login.tsx` 使用本地Nova组件实现白底单列居中、密码显示、防重复提交、错误/加载、原认证与autocomplete；密码不新增持久化。
- [x] T011 [US1] 在 `frontend/src/components/AppLayout.tsx` 组合本地Button/Sheet、Lucide和健康hook，桌面240/72px、<768px移动导航，保持path/onNavigate/onLogout/children；collapsed默认false，仅布局key持久化，mobileOpen仅内存。
- [x] T012 [US1] 在 `frontend/src/App.tsx`、`main.tsx` 接入共享Motion、局部旧内容作用域和原hash/认证，验证退出与三页导航；不重写Chat/Knowledge/Logs或SSE。
- [x] T013 [US1] 在 `output/frontend017/phase-a-20261029-01/` 保存新check:deps、完整前端Vitest、build、npm ls及大小对比，修复本阶段新增失败并保留首次证据。
- [x] T014 [US1] 在 `output/frontend017/phase-a-20261029-01/` 用Playwright受控API验证登录/导航/退出/健康/移动Sheet与键盘，保存1440/390px截图、控制台及JSON；明确模拟接口而非真实模型质量。
- [x] T015 [US1] 核对保护hash、UTF-8/文档链接/任务映射，保存 `specs/017-frontend-nova-workspace/phase-a-report.md`，更新README/交接导航；“报告后暂停，等待用户验收”。

## Phase 4: US2 连续对话与过程简化（B，已交付）
**Goal**: 连续逐轮问答、Enter发送、折叠过程；移除前端日志。
**Independent Test**: 规格SC-001–SC-005及quickstart的B矩阵。
- [x] T016 [US2] 在 frontend/src/stores/chat-store.ts 与对应测试建立内存会话/独立轮次/generation，固定Zustand；“最多2000字”“running时禁止提交及新会话”“会话/原文/密码不持久化”。先写有行为价值测试并保存red结果。
- [x] T017 [US2] 在 frontend/src/features/chat/ 的控制器/投影及 frontend/src/api/client.ts 实现累计answer替换、快照/Parent去重、可靠ID活动合并、signal/reader释放、EOF失败、跨页与退出迟到隔离，保留016 pending语义。
- [x] T018 [US2] 在 frontend/src/pages/Chat.tsx、App.tsx、components/AppLayout.tsx 完成Nova连续对话/底部输入/Enter+Shift+IME+防重入/失败恢复/新会话与澄清；移除Logs页面及调用、旧/logs替换/chat；同步行为测试。
- [x] T019 [US2] 在 frontend/src/features/chat/ 和 components/ProcessPanel.tsx 实现原生details默认折叠的真实过程与答案下来源/完整原文，活动按ID更新；无侧栏、resizable或dnd。更新原保护测试，不用旧同名工具猜关联。
- [x] T020 [US2] 在 frontend/src/components/AnswerContent.tsx 固定react-markdown/remark-gfm，skipHtml/远程图占位/安全链接/代码表格局部滚动与原始正文复制，覆盖失败与恶意内容。
- [x] T021 [US2] 在 frontend/src/**/*.test.* 与 output/frontend017/phase-b-20261029-01/ 完成回归、构建、依赖审计/四宽度/200%/键盘/减少动态效果/模拟浏览器/保护核对，保存 specs/017-frontend-nova-workspace/phase-b-report.md 后暂停。

## Phase 5: US3 PDF文档（C，工程完成待验收）
- [x] T022 [US3] 在 frontend/src/components/ui/ 按实际需要补充同一Nova组件及来源，不新增基础库。
- [x] T023 [US3] 在 frontend/src/pages/Knowledge.tsx 实现单PDF选择/拖入、名称和状态交集过滤、统一删除确认，保留生命周期与轮询。
- [x] T024 [US3] 在 frontend/src/pages/Knowledge.test.tsx 覆盖文档流程、完成C浏览器/构建并保存 specs/017-frontend-nova-workspace/phase-c-report.md 后暂停。

## Phase 6: 已撤销
原T025日志UI与T026日志回归未实施，用户现明确移除前端日志；撤销而非工程完成。原任务文本保存在本次before快照，后台日志保持。

## Phase 7: Polish（D，工程完成待验收）
- [x] T027 完成 specs/017-frontend-nova-workspace/quickstart.md 的三页最终视口/缩放/键盘/长文本矩阵，清理无消费legacy样式。
- [x] T028 运行 frontend/scripts/check-deps.mjs、全量Vitest/build/npm ls，记录最终包体/来源/保护核对。
- [x] T029 保存 specs/017-frontend-nova-workspace/phase-d-report.md，更新导航并暂停。

## Dependencies & Execution Order
A完成记录保持 → B文档同步/一致性分析 → T016测试/状态 → T017流 → T018页面与日志退出 → T019过程 → T020Markdown → T021验证报告 → 用户验收并明确继续 → C → 用户继续 → D。
## Parallel Opportunities
仅plan技能要求的依赖只读研究使用子代理；共享源码实现串行，固定代码后的独立测试/构建可并行。不得通过并行越过阶段。
## Requirement Coverage
FR-001/FR-003/FR-009/FR-013:T018；FR-002:T021原登录保护；FR-004/FR-005:T016/T017/T018；FR-006:T020；FR-007:T019；FR-008:T022–T024；FR-010/FR-011/FR-012:T021/T027–T029。SC-001–SC-005均由T021覆盖本阶段范围。
## Implementation Strategy
本轮只执行既有D，报告后暂停；任务勾选是工程完成，不代表用户验收。复用现有规格、架构与依赖，不新增功能或技术选型；保存当前88项测试/构建与三页快照基线，删除无消费旧样式后检查四宽度、CSS及等效200%、键盘、长文本与减少动态效果，再执行最终工程审计。历史报告与失败证据不覆盖。
