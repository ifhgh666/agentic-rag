# 017 阶段 E：真实前后端与模型联调报告

**日期**：2026-11-02（America/Phoenix）  
**结论**：E / Phase8 / T030–T034工程完成，待用户验收。真实浏览器→Vite代理→FastAPI→PDF解析/ONNX/BM25→当前deepseek-flash链路通过；两题首次回答均正确，**2通过/0失败/0未运行**。仅代表本份合成资料的本批表现，不改判016历史质量结果。

## 授权、计划与真实性

用户在A–D完成后明确选择“真实前后端与模型联调”，本轮据此在017追加单一E阶段。按项目Spec Kit specify/plan/tasks/implement更新现有spec/plan/research/data-model/contracts/quickstart/tasks，保持A–D原报告、设计图及T025/T026撤销。setup-plan、setup-tasks和check-prerequisites成功，需求清单12/12，无嵌套AGENTS或extension hook。计划研究代理仅只读核对当前参考图和缓存加载，不运行模型。

本轮沿用实际openai_compatible/deepseek-flash、温度0、seed42、正常工厂的关闭思考策略与max_retries=0。未改提示、schema、模型、RAG算法、前后端产品代码或依赖。不是受控API或假SSE：没有page.route/模型替身，实际HTTP与SDK请求完成；浏览器只克隆旁读公开SSE，不替换响应。

使用**隔离实例与临时账号**，并非验证正式管理员的真实密码：密码仅在内存传递，后端运行时只保留hash，JWT secret临时生成，未写入命令行、报告或配置文件。app.main导入前已设置绝对隔离数据/Qdrant/缓存路径；没有先创建正式Qdrant客户端。启动的后端/前端仅绑定127.0.0.1，最终均关闭。

当前016正常图实际约束为每分支8工具、10迭代、递归50；旧.env总300/120秒、8/12模型额度没有被当成当前产品约束。E单独冻结每轮单一300秒**外部采集watchdog**，不随事件重置，不宣称产品超时或立即中止远端SDK；本批未触发。共两个首次问答请求，无改问或业务重试。

## 文档与编码器预检

自建[中文文本PDF](../../output/frontend017/phase-e-20261102-01/input/integration-e2e-017.pdf)明确标记为合成测试资料，包含“停用满72小时后再次使用前重新校准”和“定期核查45天”两项事实。PDF为2733字节、1页，经渲染目视检查和实际PdfParser/pymupdf4llm复开提取验证；[提取文本](../../output/frontend017/phase-e-20261102-01/input/parsed.md)与[渲染图](../../output/frontend017/phase-e-20261102-01/input/integration-e2e-017.png)保留。评分预期文件只用于采集后的审阅，没有注入模型输入。

PDF SHA256：581afd5d4b973f02d526195c52c703261b36c272769a7a9927f413f63cc35a25。两题、资料及非敏感模型快照在实际请求前冻结，见[protocol.json](../../output/frontend017/phase-e-20261102-01/protocol.json)、[cases.json](../../output/frontend017/phase-e-20261102-01/cases.json)和[preflight.json](../../output/frontend017/phase-e-20261102-01/preflight.json)。

真实fastembed多语言MiniLM ONNX输出384维；默认Qdrant/BM25预检非空Sparse，179个非空停用词，stemmer启用。保持SPARSE_OFFLINE_FALLBACK=false，通过FASTEMBED_CACHE_PATH及HF_HUB_OFFLINE加载复制缓存，没有注入编码器工厂或使用deterministic。真实936字节词表SHA256=019f104ba2ed07436d05f9cdd3383034ad66014edc27fc651f837e1a038b6451。准备阶段LLM调用0。

## 实际联调流程

| 检查 | 真实结果 |
|---|---|
| 认证错误/成功 | 错误密码401，临时账号正确密码200，真实JWT认证 |
| 上传与处理 | POST202返回processing；实际列表ready，2 Parent/2 Child，索引健康就绪 |
| 首次问答与跨页 | E01请求运行中切到知识库再返回，读取持续；同一thread完成两轮，UI保留两条答案 |
| 来源与过程 | 实际来源/检索原文和过程可展开；2次search_child_chunks，未触发Parent读取 |
| 删除 | 首次取消没有DELETE，确认只删除本轮UUID，HTTP204；实际清单0、debug检索0 |
| 退出 | HTTP204，客户端token清除；原token访问返回401，服务端撤销生效 |
| 收尾 | 后端正常退出0，前端自有进程SIGTERM结束；隔离文档和Qdrant Point均为0 |

上传UUID：fb11a810-2314-45a1-aeae-fa544eccf6eb。本轮真实文档处理约0.270秒；浏览器上传检查步骤3.221秒还包括界面、轮询及截图，二者不混用。

## 两题原答与正确事实

完整逐题审阅见[原答对照](phase-e-answer-comparison-20261102.md)与[manual-review.json](../../output/frontend017/phase-e-20261102-01/manual-review.json)，审阅者为Codex，不冒称用户验收。

| 题目 | 正确事实 | 模型首次核心回答 | 判定 | 浏览器采集 | 服务管线 |
|---|---|---|---|---:|---:|
| E01：停用多久后重新校准？ | 满72小时，再次使用前重新校准 | 连续停用满72小时后，需要在再次使用前重新校准 | 通过 | 4.839s | 4.561s |
| E02：定期核查间隔？ | 45天 | 定期核查间隔为45天 | 通过 | 4.027s | 3.841s |

两条答案无额外错误数值或条件，来源均为实际上传的integration-e2e-017.pdf。服务返回相关章节；page_start/page_end为null，没有补写页码。每轮各引用同一文件的两个已检索章节，包含一个与该题直接相关的章节。

- E01 request_id：8ccb019e-c5a1-4488-a4b4-5fe47113d4d7。
- E02 request_id：d28f977a-2080-40fb-9f31-1b338ce05411。
- 两轮thread_id：thread-f09c9f74-f7a1-45f7-854c-6c843a88ace3。

原始公开SSE：[E01](../../output/frontend017/phase-e-20261102-01/raw/E01.sse)、[E02](../../output/frontend017/phase-e-20261102-01/raw/E02.sse)；完整原答/来源：[E01 JSON](../../output/frontend017/phase-e-20261102-01/E01-answer.json)、[E02 JSON](../../output/frontend017/phase-e-20261102-01/E02-answer.json)。累计answer事件39/28条，界面每轮按累计正文更新；没有把这些事件数误算为模型调用。

## 真实调用与用量

| 项目 | E01 | E02 | 合计 |
|---|---:|---:|---:|
| 模型/兼容云路径调用 | 4 | 4 | 8 |
| rewrite_query / orchestrator / aggregate_answers | 1/2/1 | 1/2/1 | 2/4/2 |
| search_child_chunks | 1 | 1 | 2 |
| retrieve_parent_chunks / Judge | 0/0 | 0/0 | 0/0 |
| provider输入Token | 3031 | 3053 | 6084 |
| provider输出Token | 213 | 182 | 395 |
| provider合计Token | 3244 | 3235 | 6479 |
| 模型耗时累计 | 4.027s | 3.703s | 7.730s |

用量来源为provider，不是估算。两题浏览器采集合计8.866秒，包含UI操作、跨页和观察等待，不包括资源准备、服务启动或人工审阅；不是整体任务时延或性能基准。远端模型别名不证明固定权重修订。

## 实际命令、文件与退出状态

证据目录：[phase-e-20261102-01](../../output/frontend017/phase-e-20261102-01/)。

| 工作目录 | 实际入口 | 退出 | 记录 |
|---|---|---|---|
| 根目录 | python -X utf8 output/frontend017/phase-e-20261102-01/snapshot.py | 0 | snapshot.log，181份源码/配置及11份正式资料指纹 |
| 根目录 | pwsh -NoProfile -File .specify/scripts/powershell/setup-plan.ps1 -Json | 0 | setup-plan.json；保留既有计划 |
| 根目录 | pwsh -NoProfile -File .specify/scripts/powershell/setup-tasks.ps1 -Json | 0 | setup-tasks.json及模板结构 |
| 根目录 | pwsh -NoProfile -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks | 0 | prerequisites.json |
| 根目录 | python -X utf8 output/frontend017/phase-e-20261102-01/update_plan.py | 0 | 追加E设计/契约/任务和冻结两题 |
| 根目录 | python -X utf8 output/frontend017/phase-e-20261102-01/prepare_assets.py | 0 | prepare-assets-01.log与preflight.json |
| 根目录 | node --check …/integrate.mjs；python -X utf8 -m py_compile …/server.py | 0 | 采集器和服务入口语法检查，随后真实运行成功 |
| 根目录 | node output/frontend017/phase-e-20261102-01/integrate.mjs | 0 | integrate-01.log、integration-result.json |
| 根目录 | python -X utf8 output/frontend017/phase-e-20261102-01/finalize_metadata.py | 0 | 完整原答人工审阅、任务及导航更新 |
| 根目录 | python -X utf8 output/frontend017/phase-e-20261102-01/verify.py | 0 | verification-final.log/json，20项核对通过 |

实际后端/前端入口分别为server.py和serve_frontend.mjs，子进程windowsHide=true，只绑定本轮8001/5176；未重启或停止其他服务。密码与凭据未作为命令行参数传递。本轮仅增加运行辅助文件与规格/报告；产品代码0变更，依赖0变更，因此没有无理由重复D的88项单测/构建，也没有把D结果冒充本轮运行。

截图：[文档真实就绪](../../output/frontend017/phase-e-20261102-01/screenshots/knowledge-ready.png)、[E01真实答案](../../output/frontend017/phase-e-20261102-01/screenshots/E01-answer.png)、[E02真实答案](../../output/frontend017/phase-e-20261102-01/screenshots/E02-answer.png)、[过程与原文](../../output/frontend017/phase-e-20261102-01/screenshots/real-process-and-evidence.png)、[确认删除后](../../output/frontend017/phase-e-20261102-01/screenshots/knowledge-deleted.png)。PDF、实际答案及过程截图已目视查看。

## 保护与限制

20项核对通过：181份改前源码/配置中，8份是获准更新的导航/设计资料，其余**173份保护文件无差异**；全部**11份正式资料/索引文件的清单和SHA-256保持**，原Dense缓存文件也保持。正式.env、API/前后端代码、016原答/失败、A–D报告和设计图、字体与依赖均未改写。唯一删除对象是本次上传的隔离文档，正式目录只读指纹核对。见[verification-final.json](../../output/frontend017/phase-e-20261102-01/verification-final.json)和[本轮独立差异](../../output/frontend017/phase-e-20261102-01/phase-e-review.patch)。

页面运行异常0，所有API无404/5xx。控制台有1条预期错误密码401和1条非API资源404；该404没有采集资源URL，尚未定位，不能宣称控制台零错误。PDF库保留legacy-layout/use_ocr参数提示；本资料为可提取文本，实际解析成功，没有增加OCR或安装可选包。

本批没有覆盖正式账号密码、正式知识库问答、Parent工具、澄清/复杂恢复、其他浏览器或系统输入法/剪贴板。2题简单事实通过不能证明历史四项质量问题已经修复；gold-1.0没有重跑，016原11通过/4部分正确未通过结论保持。

T030–T034完成，本轮E到此结束。所有有效工程任务共32项完成，T025/T026保持撤销。用户验收和任何后续复测另行进行，不自动追加真实模型请求。

**报告后暂停，等待用户验收**。
