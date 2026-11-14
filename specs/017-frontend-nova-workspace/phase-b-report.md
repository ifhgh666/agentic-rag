# 017 B 阶段报告：连续对话、Enter发送与过程简化

日期：2026-10-29（America/Phoenix）。用户明确批准修订计划并要求实施；本次仅完成B，未进入C知识库改版或D最终验收。实际Git分支保持codex/model-driven-agent-loop，无提交、推送或发布。

**结论：B工程交付完成，待用户验收。78项前端测试、23项受控浏览器场景、构建与依赖审计通过；108个保护文件无差异，旧锁中已有包版本零变化。报告后暂停，等待用户验收。**

## 实际行为与文件

- 主导航只留问答台和知识库，桌面/移动日志入口、Logs页面、前端日志API消费及LogItem类型移除；旧#/logs以history.replaceState替换#/chat。后台日志/API/历史记录保留。
- Zustand只管理当前内存会话。连续轮次独立保存正文、来源、完整Child/Parent、分析、公开活动、用量、错误与终态；累计answer替换，检索快照覆盖、Parent按真实身份去重。
- 输入固定在工作区底部，历史独立滚动。Enter发送、Shift+Enter换行、组合输入/229/repeat保护、同步防重入、非空/2000字、运行中禁用发送与新会话。失败保留轮次、部分正文并恢复原草稿（包含换行/首尾空格），不自动重试；结束后在未转移阅读焦点时恢复输入焦点。
- 每轮只显示真实事件驱动的简短状态；查询分析/工具活动默认折叠，可靠tool_run_id/tool_call_id/model_call_id关联更新，缺少身份不按名称猜合并。Token/节点/请求标识位于技术详情，不暴露私有模型输出或核验卡。来源在答案下，原文按需展开。
- Markdown基础GFM、skipHtml、图片文字占位、安全链接、代码/表格局部滚动；复制原始正文，成功/失败均反馈。
- 流控制器独立于页面。切知识库不断流；新会话清空；退出立即清空/递增代次/abort，异步logout不阻塞本地退出，认证清除也清理会话。streamChat新增兼容第五参数signal，收到complete释放读取，异常/EOF释放reader；EOF缺终态标记失败。

主要实现：frontend/src/stores/chat-store.ts、features/chat/controller.ts与activity.ts、features/chat/EvidenceList.tsx、pages/Chat.tsx、components/ProcessPanel.tsx、components/AnswerContent.tsx、styles/chat.css，以及App/AppLayout、auth/session、api/client。新增行为测试位于同目录；本次精确文件差异见[清单](../../output/frontend017/phase-b-20261029-01/this-phase-changes.json)。已移除的原日志文件和本轮修改前版本保留在before快照，不依赖Git HEAD覆盖历史修改。

## Spec Kit与阶段状态

按项目specify→plan→tasks→analyze→implement同步已有017规格、计划、任务、research/data-model/contracts/quickstart与需求质量清单。执行setup-plan.ps1 -Json、setup-tasks.ps1 -Json、check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks，均退出0；已有目录不新建feature、不切分支。extensions.yml不存在，相关hook无待执行项。

12项需求质量检查满足；13条功能要求有任务映射，见[实施前分析](analysis-b.md)。T001–T015原记录保持，T016–T021工程完成；T025/T026日志改版撤销而非勾选。T022–T024与T027–T029仍未执行。原A报告、四图和016质量失败未改写。

## 实际验证命令与结果

证据根目录：[phase-b-20261029-01](../../output/frontend017/phase-b-20261029-01/)。下表命令均实际执行，退出状态独立保存：

| 工作目录 | 命令/入口 | 退出 | 结果与记录 |
|---|---|---|---|
| frontend | npm test -- --run（改前） | 0 | 56 passed，baseline-test.log |
| frontend | npm test -- src/features/chat/controller.test.ts（未实现时） | 1 | 模块缺失红灯，red-controller.log；不称6项断言均执行失败 |
| frontend | npm install --save-exact zustand@5.0.16 react-markdown@10.1.0 remark-gfm@4.0.1 --cache ../output/frontend017/phase-b-20261029-01/npm-cache --prefer-online --no-audit --no-fund | 0 | install.log |
| frontend | npm test -- --run（最终） | 0 | 15文件/78 passed，accepted-test.log |
| frontend | npm run build（最终，进程内TEMP/TMP指向任务目录并还原） | 0 | tsc/Vite通过，accepted-build.log；保留包体警告 |
| frontend | npm run check:deps | 0 | final-deps.log，11项直接运行依赖；框架/组件/状态/Markdown解析链单份 |
| frontend | npm ls --all --cache ../output/frontend017/phase-b-20261029-01/npm-cache | 0 | tree-physical.log；未安装可选immer不当成失败 |
| 根目录 | node output/frontend017/phase-b-20261029-01/guard-probes.mjs | 0 | 6个扫描器探针：合法通过，未批准/未消费/重复React/重复unified/绕过UI均被拒绝 |
| 根目录 | node output/frontend017/phase-b-20261029-01/browser-check.mjs browser-final | 0 | 19项主场景，browser-final.json与同名截图目录 |
| 根目录 | node output/frontend017/phase-b-20261029-01/browser-supplement.mjs browser-supplement-final | 0 | 4项补充，browser-supplement-final.json |
| 根目录 | node output/frontend017/phase-b-20261029-01/verify.mjs verification-accepted | 0 | verification-accepted.json；108项保护、17个原直接库及全部原锁包版本保持 |
| 根目录 | git diff --check -- frontend | 0 | 最后去除类型文件尾部空行后通过；初次记录保留 |

### 浏览器与数据真实性

使用本机Chrome headless/Playwright1.62.1，独立浏览器context；全部API被受控响应接管，聊天由临时合成SSE服务提供，结束后fixture服务和浏览器均关闭。真实模型调用0、真实检索0、正式上传/删除0。截图中的文档、健康绿色和用量均是明确的测试数据，不代表真实服务或问答质量。

19项主场景覆盖两项导航/旧路由、Enter、Shift换行、合成IME/229/repeat、累计答案/两轮、原文/工具身份合并、失败恢复/澄清、真实事件状态、跨页、手动阅读、Markdown安全、四宽度、CSS放大/减少动态效果、移动焦点/Escape、退出迟到与刷新/新会话。补充4项覆盖回答后输入焦点、1440×1000物理视口等效200%（720×500 CSS/DPR2，输入底部约461.6px可见）及受控剪贴板成功/失败。

控制台错误0、页面异常0；启用减少动态效果时出现1条Motion开发提示，未将其掩盖为无警告。操作系统真实输入法、系统剪贴板权限、多浏览器及真实后端凭据登录未实测；测试事件与模拟接口通过不替代这些结论。

截图：[回答桌面](../../output/frontend017/phase-b-20261029-01/browser-final/chat-answer-1440.png)、[过程展开](../../output/frontend017/phase-b-20261029-01/browser-final/chat-process-1440.png)、[运行中](../../output/frontend017/phase-b-20261029-01/browser-final/chat-running-1440.png)、[390px](../../output/frontend017/phase-b-20261029-01/browser-final/chat-width-390.png)、[等效200%](../../output/frontend017/phase-b-20261029-01/chat-effective-200-percent.png)。

## 依赖、包体与保护

新增仅Zustand5.0.16、react-markdown10.1.0、remark-gfm4.0.1，均MIT；选型及官方来源见[research](research.md)。保持React18.3.1、ReactDOM18.3.1、已有组件/图标/动画与工具版本。unified11.0.5、remark-parse11.0.0、@types/mdast4.0.4单份；锁中已有包版本变化0，没有resizable/dnd/Gradio或第二套状态/Markdown库。

当前构建JS613.32kB/gzip204.00，CSS67.37kB/gzip14.07；字体45.23+46.30kB保持。对照上一轮登录布局构建记录JS438.91/gzip150.16、CSS58.57/gzip12.33，Markdown新增使体积增加。本轮未单独运行B改前build，不把历史记录冒充本轮性能基线。Vite仍给出单块>500kB警告，未提高阈值或宣称性能改善；后续可单独评估按需拆包，不越过本次阶段。

108项保护包括backend/app、backend/.env及示例/requirements、016报告、A报告/设计图、Login、Knowledge、原基础组件/字体/健康hook，全部无差异。正式知识库/索引未操作。

## 首次失败与修正

首个快照命令工作目录写错，随后在根目录成功保存基线；未写用户源码。初始控制器红灯、tsc遗留日志re-export与details类型、类型文件末尾空行均保留输出后修正。首次构建因系统Temp中esbuild临时文件权限失败，改任务内TEMP/TMP后成功，未删系统文件或改变全局环境。

npm隐藏node_modules/.package-lock.json误把物理不存在的WASM可选包视为已安装，导致npm ls误报。先确认Windows原生oxide存在、WASM目录不存在，将单个隐藏缓存文件原样移至证据npm-hidden-lock-before.json，保留项目package-lock与全部依赖版本；重扫实际树退出0，未安装无用WASM或optional peer来掩盖问题。

浏览器最初记录包括Windows ESM路径格式、夹具拦截了/src/api模块、hash跳转断言过早、慢流释放时机过早；原browser-first/second/third/fourth记录保留，最终另存browser-final，不覆盖首次失败。需求覆盖脚本初次未识别任务的缩写编号，已将映射改为完整FR编号，verification.json初次与verification-accepted.json最终均保留。

## 未执行与停止点

前端开发服务器当前为http://127.0.0.1:5173，PID61020，HTTP200；后端8000检查不可连接，本轮未启动。真实登录/模型联调未进行，不修改密码或.env。

下一阶段仅在用户明确授权后实施C知识库；D三页最终验收另行进行。当前无未解决B工程失败，但工程通过不等于用户验收或真实模型质量通过。

**报告后暂停，等待用户验收**。
