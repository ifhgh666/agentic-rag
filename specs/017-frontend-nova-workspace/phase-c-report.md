# 017 阶段 C：Nova 知识库交付报告

**日期**：2026-10-29（America/Phoenix）  
**结论**：C / Phase5 / T022–T024 工程完成，待用户验收。88 项前端测试、22 项受控浏览器检查、构建、依赖及保护核对通过。D / T027–T029 未执行。

## 授权与范围

用户在状态说明后要求“继续执行”，实施过程中再次“继续”；本轮按已声明的第一个未完成阶段完成知识库。沿用已确认的 [知识库效果图](design/knowledge-preview.png) 和浅色 Nova/Geist；Spec Kit 指针保持017，Git 分支仍为 codex/model-driven-agent-loop。A/B报告与设计图保留历史。

本轮使用项目内 speckit-plan、speckit-tasks、speckit-implement 流程更新既有文件，三个入口脚本退出0；需求检查清单12/12。未创建新功能或重写已完成阶段，extensions.yml 不存在，无前后置扩展hook。T022–T024已勾选，任务完成不表示用户验收。

## 完成的行为与文件

- [Knowledge.tsx](../../frontend/src/pages/Knowledge.tsx)：Nova标题、实际文档计数、单PDF选择/拖入、名称和状态交集、空库/无匹配/加载/错误反馈、文档表格和删除确认。保留服务器顺序，不新增批量、排序或OCR。
- 上传共用同步锁，多文件整批拒绝、非PDF拒绝；选择值及时复位，失败后同一文件可以重选。上传回执先显示processing，再刷新；仅有processing时按1800ms轮询，ready/failed、失败原因及父子块数来自接口响应。列表刷新失败保留上次成功内容；后台读取防重叠，变更后刷新以版本号排除迟到响应，卸载清理计时并忽略迟到结果。
- 删除使用本地Nova AlertDialog，默认聚焦取消；取消/Escape返回原按钮，成功移除按钮后回到搜索。请求中阻止重复确认及关闭，失败保留文档、弹框和错误，收到成功响应后才移除行。
- [knowledge.css](../../frontend/src/styles/knowledge.css)：页面与弹框局部样式，手机上传按钮换行、表格独立横向滚动、长文件名换行、确认按钮至少44px高。表格建立定位容器，使隐藏辅助文本也限制在滚动区域内。
- [alert-dialog.tsx](../../frontend/src/components/ui/alert-dialog.tsx)、[来源清单](../../frontend/src/components/ui/source-manifest.json)、UI README：补充同一官方base-nova组件，沿用BaseUI1.9.0；本地Button导入、React18 Cancel ref适配。原registry/哈希保存在 [upstream](../../output/frontend017/phase-c-20261029-01/upstream/)，MIT许可证保持。没有新增或升级依赖。
- [App.tsx](../../frontend/src/App.tsx)仅移除Knowledge的legacy包装；样式入口增加knowledge.css。更新样式说明、当前规格/计划/任务/研究/状态契约、README和交接导航。legacy文件和导入保留给D清理。
- [Knowledge.test.tsx](../../frontend/src/pages/Knowledge.test.tsx)：10项行为测试，覆盖状态/块数、交集过滤、单文件校验、上传重选/防重入、轮询停止、刷新失败、删除确认/取消/失败/重试和空库。

本轮差异可单独查看 [phase-c-review.patch](../../output/frontend017/phase-c-20261029-01/phase-c-review.patch)，避免将仓库中已有大量未提交改动算作本轮。

## 实际命令与结果

证据目录：[phase-c-20261029-01](../../output/frontend017/phase-c-20261029-01/)。完整退出状态见 [command-results.json](../../output/frontend017/phase-c-20261029-01/command-results.json)。Node22.23.2、npm11.5.1；未安装新包。

| 工作目录 | 实际命令/入口 | 退出 | 结果与日志 |
|---|---|---|---|
| 根目录 | .specify/scripts/powershell/setup-plan.ps1 -Json | 0 | 读取并更新既有计划，不覆盖历史 |
| 根目录 | .specify/scripts/powershell/setup-tasks.ps1 -Json | 0 | 既有C任务范围保持 |
| 根目录 | .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks | 0 | 当前017产物齐备 |
| frontend | npm test -- --run（改前） | 0 | 78 passed，baseline-test.log |
| frontend | npm test -- src/pages/Knowledge.test.tsx（实现前） | 1 | 10 failed，red-knowledge.log；缺少新行为的红灯保留 |
| frontend | npm test -- src/pages/Knowledge.test.tsx | 0 | 10 passed，focused-knowledge-01.log |
| frontend | npm test -- --run（最终） | 0 | 16文件/88 passed，test-final.log |
| frontend | npm run build（最终） | 0 | tsc/Vite通过，build-final.log；仅进程内TEMP/TMP指向任务目录并还原 |
| frontend | npm run check:deps | 0 | check-deps.log，issues为空 |
| frontend | npm ls --depth=0、npm ls --all | 各0 | npm-ls.log、npm-ls-all.log；未安装的optional依赖未当成错误 |
| 根目录 | node output/frontend017/phase-c-20261029-01/browser-check.mjs browser-final | 0 | 20项通过，browser-final.json及同名截图目录 |
| 根目录 | node output/frontend017/phase-c-20261029-01/browser-supplement.mjs browser-supplement-final | 0 | 2项通过，browser-supplement-final.json及截图 |
| 根目录 | git diff --check -- frontend | 0 | diff-check.log；保留Git的LF/CRLF提示 |
| 根目录 | python -X utf8 output/frontend017/phase-c-20261029-01/verify.py（最终） | 0 | 17项核对通过，verification-final.json |

首次完整回归full-test-01.log与首次构建build-01.log也通过，未替代最终结果。构建JS623.66kB/gzip206.63、CSS77.98kB/gzip16.03；字体45.23+46.30kB保持。B历史构建为JS613.32/CSS67.37kB；本轮未另跑改前build，不把历史数值作为本轮性能基线。单块超过500kB的Vite警告仍在，未抬高阈值或提前拆包。

## 浏览器证据与真实性

本机Chrome headless与Playwright使用独立context，所有/api请求由受控响应接管。列表、健康绿色、上传回执、processing→ready/failed和删除均为合成数据。**真实后端请求0、模型调用0、真实检索0、正式上传/删除0**；这些检查只证明前端行为，不证明PDF解析、索引或问答质量。

20项主场景覆盖：加载/导航、接口字段投影与长文件名安全、交集过滤、多个/非PDF拒绝、上传失败重选/防重入、轮询两类终态、刷新失败恢复、删除取消/Tab/Enter/Escape/焦点/请求中保护/失败重试、390/768/1440/1920px、表格键盘滚动、CSS200%/减少动态效果、跨页和首次失败/空库。补充2项核对最终上传排布，以及1440×1000物理窗口等效200%（720×500 CSS、DPR2）的知识库与删除弹框。

四宽度document.scrollWidth分别为390/768/1440/1920；390与768的表格视区352/477px，表格内容790px，仅局部滚动。减少动态效果时spinner持续时间为0.00001s。最终页面异常0、非预期控制台错误0；保留5条刻意503错误响应产生的资源日志，补充检查控制台错误0。

截图： [桌面最终](../../output/frontend017/phase-c-20261029-01/browser-supplement-final/knowledge-final-1440.png)、[390px最终](../../output/frontend017/phase-c-20261029-01/browser-supplement-final/knowledge-final-390.png)、[删除失败](../../output/frontend017/phase-c-20261029-01/browser-final/knowledge-delete-failed.png)、[手机删除](../../output/frontend017/phase-c-20261029-01/browser-final/knowledge-delete-390.png)、[等效200%弹框](../../output/frontend017/phase-c-20261029-01/browser-supplement-final/knowledge-effective-200-dialog.png)。已实际查看桌面、手机、弹框及缩放截图并修正排版。

系统文件选择窗口、跨应用原生拖放、操作系统缩放、多浏览器和真实后端凭据联调未实测；选择由Playwright文件选择事件提供文件，拖放由浏览器DataTransfer事件模拟。

## 首次失败及修正

1. 实现前10项红测失败已保留；实现后定向和全量通过。
2. browser-01有8项通过，在Shift+Tab后立即检查焦点失败。focus-debug记录显示焦点先到BaseUI隐藏guard、下一帧回到确认按钮；已按其实际rAF行为等待明确目标焦点，正反Tab均验证，未修改产品焦点实现。原脚本browser-check-01.mjs与结果保留。
3. browser-02前12项通过，390px横向溢出。overflow-debug定位到表头sr-only绝对定位文本：body390而根滚动宽760；局部定位探针确认后给表格滚动容器增加position:relative，390/768均恢复根宽与视口一致。browser-03与最终20项均通过，旧失败不覆盖。
4. 截图复核发现AlertDialog的data-slot不同于Button，确认按钮没有获得局部44px高度规则；改用弹框内button选择器，并让手机选择按钮另起一行。最终主检查和补充检查均验证按钮高度及排布。
5. 首次保护脚本把现有紧凑写法Knowledge/误写成带空格匹配，App最小差异检查失败；确认实际只移除一层包装后修正匹配。verification-first保留，最终17项通过。
6. 临时Vite首次清理检查因PowerShell JSON日期被再次字符串解析而时区比较错误，保护规则拒绝停止、未误关进程；直接比较DateTime后核实同一PID/名称/启动时间，仅关闭本轮PID9540。两次记录均保留。另一次只读Win32_Process查询被系统拒绝，端口改用socket确认，无权限提升。

## 保护、限制与停止点

168份改前指纹中，15份属于获准修改文件；其余**153份保护文件无差异**，包括62份backend代码/配置、23份016资料及失败记录、A/B报告/设计图、原问答/状态控制器/登录/导航/健康hook、API类型和客户端、原Nova基础组件/字体，以及package.json与锁文件。新增源码仅Knowledge测试、knowledge.css和AlertDialog三个文件，依赖版本和原来源清单条目保持。详见 [verification-final.json](../../output/frontend017/phase-c-20261029-01/verification-final.json)。

未启动或重启后端，未操作正式知识库/索引/账号，未提交、推送或发布。本轮临时Vite5174已停止，浏览器context已关闭。016已记录的真实问答失败和未通过结论保持，不因本轮前端工程通过改判。

下一阶段仅在用户明确验收并指示继续后实施D：三页最终视口/键盘/缩放矩阵、无消费legacy清理、最终依赖/构建与报告。当前无未解决C工程失败；真实后端联调及D收尾尚未执行。

**报告后暂停，等待用户验收**。
