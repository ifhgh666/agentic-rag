# Implementation Plan: 017 Nova 前端工作台

## E 真实联调计划（2026-11-02，工程交付）

实际结果：真实浏览器到FastAPI、PDF解析/ONNX/BM25与当前deepseek-flash链路通过；2题首次回答正确，8次真实模型、2次搜索。已完成删除/退出和自有进程清理。详见[阶段E报告](phase-e-report.md)，原A-D报告保持。

Summary：在同一017内追加Phase8/T030–T034，执行用户明确选择的真实联调；原A–D作为历史保留。先冻结资料/问题/预期和资源，再通过实际浏览器访问同一产品FastAPI与Vite代理，最后审阅答案、清理本阶段实例并报告。

Technical Context：当前Python D:/newsoft/python.exe、既有FastAPI/Uvicorn、PyMuPDF/pymupdf4llm、真实fastembed ONNX 384维与Qdrant/BM25、React/Vite/Chrome；当前openai_compatible/deepseek-flash、温度0、seed42，正常工厂关闭思考且max_retries=0。不新增依赖/技术选型。数据全部在output/frontend017/phase-e-20261102-01，模型缓存复制，不在正式目录创建Qdrant客户端。

模型边界：016正常图每分支8工具、10迭代、递归50；旧.env总300/120s、8/12模型额度不代表当前产品约束。E每轮另设单一300秒外部采集watchdog，事件不重置；超时保存现场并终止本阶段自有进程，记harness_aborted，不宣称产品超时或立即终止远端SDK。最多2个首次问答，不自动重试/换模型。语义非通过而服务仍可用时继续第二题；运行超时/服务失效则保存并标记依赖场景未运行，不擅自加请求。

隔离：在任何app.main导入前设置绝对DATA_DIR/QDRANT_DB_PATH及缓存路径；使用模块创建的app，不再次create_app争用索引。临时账号密码只在进程内传递，子进程仅保留其hash；JWT secret临时生成，不读取正式账号密码，不覆盖.env。前端通过本轮专用代理指向隔离后端，端口先核对，只停止本轮PID。

真实编码资源：复制已有Dense缓存；FASTEMBED_CACHE_PATH指向E资源，HF_HUB_OFFLINE=1，预置经936B/SHA-256验证的bm25/english.txt。保持SPARSE_OFFLINE_FALLBACK=false、默认English stopwords和stemmer启用；不注入Sparse工厂、不用deterministic。先实际预检384维Dense及非空Sparse/stopwords，LLM调用0。

观测：无API拦截、假响应或假SSE服务。浏览器仅透传克隆读取公开聊天响应，保存原始SSE及接收时间；保留UI截图、HTTP状态/请求ID、答案/来源/实际usage。采集私有模型配置只写非敏感字段。测试PDF/问题可见，评分预期不进入问答输入。

任务及停止点：T030快照/预检/冻结 → T031真实服务与登录上传 → T032两轮首答及跨页 → T033仅自建文档删除/退出 → T034原答对照、指纹、清理和phase-e-report.md后暂停。报告后的质量修复/复测需另行授权。

Constitution Check：设计前后均满足单阶段、职责/接口保持、真实证据与评分分开、正式数据保护、完整记录。研究代理e_integration_research只读核对实际016规则与缓存加载路径；无未解决需求澄清或新增选型。仅在本轮发现直接HTTP/UI契约故障时做必要修复并补对应工程检查，不更改RAG提示/算法或隐藏真实失败。

**D工程交付（2026-11-02）**：用户在C交付后要求“继续”，执行既有Phase7/T027–T029。清理无消费legacy文件/导入/兼容规则，保留其快照；对照三页清理前后样式，完成既有矩阵与最终工程审计。沿用现有技术栈、组件来源和API，无新增选型/依赖/功能；C及以下各自日期的授权记录为历史。D报告后暂停，等待用户验收。

**D结果**：T027–T029完成待验收，88项测试与31项受控浏览器检查通过；构建CSS由77.98降到51.86kB，六组清理前后计算样式保持；来源/依赖与保护核对见[D报告](phase-d-report.md)。不运行真实后端或模型。

**C历史授权（2026-10-29）**：用户“继续执行”后仅执行C=Phase5/T022–T024；下文B授权与交付为历史记录。知识库按既有design/knowledge-preview.png迁移，C报告后暂停，D与016质量修复不执行。

**C工程交付（2026-10-29历史）**：T022–T024完成；88项前端测试、22项受控浏览器检查、构建及依赖审计通过，见[C报告](phase-c-report.md)。C的知识库已退出legacy作用域，D仍未执行。下文B Summary/Structure和阶段表记录其当时范围；C最终设计以下方C章节为准。报告后暂停，等待用户验收。

**Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)
**B历史授权**: 用户明确批准修订计划并要求实施，仅执行B。实际Git分支保持codex/model-driven-agent-loop；Spec Kit指针017。A历史报告和图片不改写。

**B交付**: T016–T021工程完成，78项测试、23项受控浏览器场景、build/check:deps/npm实际树和108项保护核对通过；见[阶段报告](phase-b-report.md)。报告后暂停，等待用户验收。

## B历史 Summary
浅色Nova连续对话、底部输入、Enter发送、对话内原生折叠过程与答案下方来源；移除前端日志。原右侧可调面板与日志改版计划撤销。C知识库与D全站最终验收留后续。

## Technical Context
React18/TypeScript strict/Vite6，保留已安装BaseUI/Nova、Lucide、Motion及本地Geist。B只新增Zustand、react-markdown和remark-gfm，版本按research.md官方核验结果精确固定。单npm锁文件，旧直接依赖版本保持；不引入resizable、dnd、Gradio、查询缓存或第二套库。
状态仅内存；浏览器存储只保留现有token/布局偏好。测试用Vitest/jsdom、tsc/Vite及Playwright受控API；不触发真实模型、正式上传删除或后端重启。

## Constitution Check
研究前及设计后均符合：B独立交付；store/流控制/事件投影/UI分责；证据按轮且不宣称正确；后台/配置/历史指纹保护；真实/模拟分开报告。无需修改宪章。

## B历史 Project Structure
frontend/src/stores存会话状态，features/chat存流控制/活动投影与展示，components/AnswerContent处理Markdown。Chat退出legacy作用域，Knowledge继续legacy。App控制认证/路由，AppLayout仅两项导航。来源与过程在每轮内部，无额外布局库。

## Architecture and Interfaces
- 后端API、SSE事件名/数据、模型与prompt不变。streamChat原四参数保持兼容，新增第五参数signal?:AbortSignal，fetch传signal，读取finally释放reader；无complete而EOF视为中断失败。
- ChatSession含threadId、draft、action、pending、turns、runningTurnId、generation；每轮有本地id及requestId，累计answer替换，retrieval快照覆盖，Parent按tool_call_id+parent_id去重。事件首先校验代次、轮次、请求/线程身份。
- 流控制独立于页面挂载；切页不断流。退出立即递增generation/abort/清空，再调用原logout；迟到响应不写回。新会话仅空闲可用。clearToken的现有401行为须同时通知App清除会话。
- 输入按钮/键盘共用同步防重入入口；组合输入/isComposing/229/repeat不发送；Shift换行。失败恢复原提交文字；非cancel立即显示用户消息并清空草稿。
- 活动按tool_run_id/tool_call_id/model_call_id可靠身份关联；无身份不按工具名猜合并。展示命名查询分析/检索/读取/生成，低层节点与用量在默认收起详情。收到终态前不得显示完成。
- Markdown skipHtml，不启用rehype-raw；图片文字占位、安全链接、表格/代码局部滚动；复制原始正文及失败提示。原文纯文本，不省略实际保留内容。
- 路由只接收/chat、/knowledge；/logs以history.replaceState转/chat。移除Logs页面和前端listLogs调用，保留后台端点及历史。

## Phases and Stop Points
| 阶段 | tasks | 范围 | 报告 |
|---|---|---|---|
| A已交付 | Phase1–3/T001–T015 | 原基础与登录 | 原A报告保持 |
| B已交付 | Phase4/T016–T021 | 连续对话与执行过程 | phase-b-report.md保持 |
| C已交付待验收 | Phase5/T022–T024 | 单PDF知识库改版 | phase-c-report.md后暂停 |
| D已交付待验收 | Phase7/T027–T029 | 三页最终矩阵/依赖审计 | phase-d-report.md后暂停 |
原Phase6/T025–T026未执行，因用户移除日志页而撤销；不勾成已完成。

## Validation
先保存本轮基线，覆盖用户逐项验收及原pending/SSE行为；验证四宽度/200%/键盘/减少动态效果、登录与知识库兼容、旧日志地址。记录命令退出码、截图、依赖树/包体和保护hash。浏览器使用模拟API，不能据此宣称真实模型质量通过。报告后暂停，等待用户验收。

## Complexity Tracking
无后端、数据库或永久状态迁移；原生details无需新增折叠库。新增三项库均有实际使用点，未使用库不提前安装。

## C设计与实施边界

使用现有Geist/neutral/Nova Button/Input，按实际需求补充官方base-nova AlertDialog源码（MIT、原registry/hash保留）并适配本地Button；沿用已安装BaseUI1.9.0，无新增依赖或版本变化。原生select提供状态筛选，删除使用同一AlertDialog，默认聚焦取消；请求中阻止重复确认和关闭，失败保留弹框/文档及错误，成功后删除行、回到仍存在的控制点。

Knowledge退出legacy-content作用域，独立knowledge.css限定页面及删除弹框；保留legacy文件供D最终清理。桌面为图中的紧凑文档表，移动端表格局部滚动、页面不横向溢出。名称大小写不敏感子串与processing/ready/failed状态取交集，保留服务端顺序，无额外排序/批量/OCR。空库、无匹配、加载、刷新失败、上传/删除忙碌分别展示。

单PDF选择和拖入共用校验/同步提交锁，多文件整批拒绝、非PDF拒绝；文件选择值及时复位以支持同文件重选。上传回执先保留processing行，再刷新列表；processing按原1800ms轮询，ready/failed及块数只用实际响应，失败时保留最后成功列表。后台刷新不重叠，突变后强制新刷新拒绝过期响应；卸载清理计时并忽略迟到结果。REST函数/后端wire契约不变，会话控制器及切页不断流保持。

T022→T023→T024，测试先固定缺失行为后实现；保存B当前78项基线、聚焦行为测试、全量前端/构建/依赖审计及受控浏览器。浏览器覆盖选择/拖入、交集过滤、生命周期、删除取消/成功/失败、键盘焦点、窄屏与200%/减少动态效果；不调用真实API。保护backend/配置/016失败、B问答与登录/导航及旧报告，保存C报告后暂停。宪章复核：同一阶段、模块职责保持、原始失败/数据保护、接口兼容、来源可追溯；无新技术未知项或需研究代理的选型。
