# 017 阶段 D：前端全站收尾报告

**日期**：2026-11-02（America/Phoenix）  
**结论**：D / Phase7 / T027–T029工程完成，待用户验收。017 A–D的27项有效工程任务全部勾选；T025/T026日志改版保持撤销，不计为完成。88项前端测试、31项受控浏览器检查及构建/依赖/保护核对通过。

## 授权与范围

用户在C交付后要求“继续”，本轮只执行既有D：清理无消费者的旧样式、完成三页最终矩阵和工程审计、更新导航并报告。按项目speckit-implement复用既有规格/计划/任务；入口check-prerequisites成功定位017，需求清单12/12，受影响路径无嵌套AGENTS，extensions.yml不存在，无扩展hook。实际分支为codex/model-driven-agent-loop，功能指针保持017。

沿用已确认浅色Nova/Geist、原组件/依赖和API。未新增功能、库、后端或模型调用；不提交、推送、合并或发布。A/B/C报告、设计图和016失败结论保持历史事实。

## 实际改动

- 移除frontend/src/styles/legacy.css（31,117字节原源码，完整保存在before快照），此前所有规则均在legacy-content作用域内，三页已无消费者。
- [app.css](../../frontend/src/styles/app.css)仅删除该导入；[tokens.css](../../frontend/src/styles/tokens.css)仅删除两条旧兼容选择器。
- 更新[样式说明](../../frontend/src/styles/README.md)、当前spec/plan/tasks/quickstart以及README、交接导航。所有产品TS/TSX、前端API/状态控制器、页面和原组件均未修改。

本轮独立差异：[phase-d-review.patch](../../output/frontend017/phase-d-20261102-01/phase-d-review.patch)。仓库原有大量未提交改动完整保留，不将其算作本轮改动。

清理前后六组页面（登录/问答/知识库，各390和1440px）的计算样式一致，六对PNG的SHA-256也完全相同。此次清理没有改变已确认页面效果。

## 工程验证

证据目录：[phase-d-20261102-01](../../output/frontend017/phase-d-20261102-01/)。Node22.23.2、npm11.5.1，未安装或升级包；完整退出记录见[command-results.json](../../output/frontend017/phase-d-20261102-01/command-results.json)。

| 工作目录 | 实际命令/入口 | 退出 | 结果与记录 |
|---|---|---|---|
| 根目录 | .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks | 0 | 读取既有017产物，不重生成计划 |
| frontend | npm test -- --run（清理前） | 0 | 16文件/88 passed，baseline-test.log |
| frontend | npm run build（清理前） | 0 | baseline-build.log，CSS77.98kB/gzip16.03 |
| 根目录 | node output/frontend017/phase-d-20261102-01/browser-check.mjs browser-before | 0 | 六组清理前截图/计算样式，browser-before.json |
| frontend | npm test -- --run（最终） | 0 | 16文件/88 passed，test-final.log |
| frontend | npm run build（最终） | 0 | tsc/Vite通过，build-final.log |
| frontend | npm run check:deps | 0 | deps-final.log，issues为空、11项直接运行依赖 |
| frontend | npm ls --all | 0 | npm-ls-all.log，未安装optional peer未视为错误 |
| 根目录 | node output/frontend017/phase-d-20261102-01/browser-check.mjs browser-tail --tail | 0 | 4项剩余焦点/动态效果及跨页检查通过，browser-tail.json |
| 根目录 | node output/frontend017/phase-d-20261102-01/browser-check.mjs browser-accepted | 0 | 最终完整31项通过，browser-accepted.json |
| 根目录 | git -c core.safecrlf=false diff --check -- frontend | 0 | diff-check.log；仅该命令局部设置，不修改Git配置 |
| 根目录 | python -X utf8 output/frontend017/phase-d-20261102-01/verify.py | 0 | 20项核对通过，verification-final.json |

构建的TEMP/TMP仅在进程内指向本轮build-temp并在finally还原。没有lint脚本，未声称执行lint。

### 包体与来源

本轮实际清理前后构建：CSS **77.98→51.86kB**（减少26.12kB，约33.5%），gzip16.03→10.69kB。JS623.66kB/gzip206.63保持，字体45.23+46.30kB保持。这里只说明产物大小，不宣称运行时延改善。

React18.3.1、BaseUI1.9.0、Motion14.7.1、Zustand5.0.16和Markdown解析链保持，依赖清单/锁文件/白名单没有修改。check:deps中stage=017-B是白名单建立时的历史标签，本轮实际执行及报告属于D。

[source-audit.json](../../output/frontend017/phase-d-20261102-01/source-audit.json)实际核对来源清单的8项原始registry/许可证/字体，SHA-256全部匹配A/C保存的原文件。本轮未访问远端更新来源或引入新版本。

JS单块超过500kB的既有Vite警告仍在；未提高阈值、拆包或将其说成已消除。

## 三页浏览器矩阵

本机Chrome headless，独立context，API全部受控，聊天使用本轮临时合成SSE服务。**真实后端请求0、模型调用0、真实检索0、正式上传/删除0**。截图中的绿色健康、文档、答案/来源及用量均为测试夹具，不代表真实服务就绪或模型质量。

最终[完整结果](../../output/frontend017/phase-d-20261102-01/browser-accepted.json)包含31项：

| 范围 | 项数 | 实际核对 |
|---|---:|---|
| 清理前后对照 | 6 | 三页390/1440px的计算样式及PNG保持 |
| 四宽度与长内容 | 12 | 三页390/768/1440/1920px；长账号、长答案/代码/32列表格、长文件名/来源；无页面横向溢出 |
| CSS内容放大与等效浏览器缩放 | 6 | 三页CSS200%可访问；720×500 CSS/DPR2等效200%，问答输入留在视口，知识库确认框可用 |
| 键盘流程 | 3 | 登录密码切换/Enter/退出；问答Shift换行/Enter/表格和过程/完整原文；知识库筛选/横滚/删除取消/Tab/Escape/焦点 |
| 减少动态效果与焦点 | 3 | 三页可见键盘焦点，问答spinner无动画 |
| 跨页与会话 | 1 | 运行中切知识库后返回、两轮不重复、旧日志地址替换和新会话清空 |

页面异常0、控制台错误0；保留1条Motion开发环境reduced-motion提示，没有隐藏为“无警告”。没有/api/logs请求，Markdown不执行脚本或加载远程图片。

截图：[登录桌面](../../output/frontend017/phase-d-20261102-01/browser-accepted/login-1440.png)、[问答390px长内容](../../output/frontend017/phase-d-20261102-01/browser-accepted/chat-390-long.png)、[知识库768px长文件名](../../output/frontend017/phase-d-20261102-01/browser-accepted/knowledge-768-long.png)、[问答等效200%](../../output/frontend017/phase-d-20261102-01/browser-accepted/chat-effective-200.png)。已实际查看这些截图，其他视口截图保存在同目录。

## 首次失败与检查修正

原始批次结果保留：browser-01: 20通过/1失败/10未运行；browser-02: 25通过/1失败/5未运行；browser-final: 28通过/1失败/2未运行。最终另存browser-accepted，31项全部执行，不覆盖初始失败或把初始未运行项当作通过；对应脚本版本browser-check-01/02/03.mjs均保留。

1. 首轮把CSS zoom=2内容放大当作浏览器缩放，要求输入在初始视口。zoom-probe显示容器936 CSS px被放大，文档高2000px、输入底部1915px；还原原legacy样式后结果相同。垂直滚动后输入底部915px可见，等效浏览器720×500下底部461.6px可见。检查区分这两种方式；没有改产品高度来迎合探针。**CSS内容放大仍需要垂直滚动访问输入，不声称它自动固定在初始屏幕内。**
2. 第二轮要求两列中文长表格横滚，但table-probe测得clientWidth=scrollWidth=309px，内容已正常换行。补用真实会溢出的32列表格后，table-focus-probe测得内容1133px、容器309px，ArrowRight后scrollLeft=40且焦点保持，再进行完整检查。不是为通过测试而修改产品。
3. 一轮减少动态效果检查从末尾文本框Tab后检查任意激活节点，焦点目标选择不当；改为从复制回答按钮按Tab验证页内可用控件。4项定向和最终31项通过，产品TSX未改变。

另一次广泛只读搜索扫到历史pytest受限目录而被拒绝，随后仅按受影响目录逐级核对AGENTS；未改权限、清理旧目录或申请提升权限。

## 保护与交接

181份清理前指纹中，10份属于本轮允许修改/删除路径；其余**171份保护文件无差异**。包含后端、已有.env/示例/requirements、016原答与失败资料、A/B/C报告和设计图、全部产品TS/TSX及API/类型/测试、原Nova源码/字体与依赖锁文件。新增前端源码0，仅删除已备份的legacy.css。保护、UTF-8、链接、来源、任务状态和原始失败保留检查见[verification-final.json](../../output/frontend017/phase-d-20261102-01/verification-final.json)。

本轮临时Vite5175/PID44576核对名称与启动时间后已停止，浏览器context和合成SSE服务已关闭；未启动或重启后端。正式知识库/索引和账号未操作，旧真实质量失败不改判。

未实测真实后端登录/索引/PDF联调、真实模型、其他浏览器、操作系统原生缩放/输入法/剪贴板；等效缩放与受控接口通过不能替代这些结论。

017前端计划已无剩余有效工程任务；工程交付不代表用户验收或真实问答质量通过。本轮到D为止，不自动开展额外联调或评测。

**报告后暂停，等待用户验收**。
