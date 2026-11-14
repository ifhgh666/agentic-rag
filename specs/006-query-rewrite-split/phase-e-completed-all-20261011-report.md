# 阶段E：完整输入17题全部首次输出报告

日期：2026-10-11。用户明确要求“你检测完阶段e，有错误或者停止执行的都先执行下去，不要停”。按[继续规则](phase-e-continue-policy-20261011.md)覆盖本轮E遇错停止条件，保留前八题首次记录，从RW09继续；本轮单题失败、协议错误后仍执行下一题，不改失败为通过，不重试，不进入F。

**新版E的17题已全部运行：10通过、7失败、0未运行。采集覆盖完成，质量验收未通过。** 失败为RW08、RW11、RW12、RW13、RW14、RW15、RW16。T031因质量要求未满足仍未勾选，T034及005 T018不变。完整输入题集不能证明原代词/省略补全能力通过。

## 范围、实现和冻结

采集工具 `backend/scripts/capture_query_rewrite_v1.py` 新增显式 `--continue-on-failure`，与旧停止模式互斥。新模式允许引用已有failed/uncertain人工审阅，原状态和文件哈希保留；每题先保存首次输出，正常协议再人工核对。单题模型/格式错误记failed后继续，没有重试或新Judge。批次全部执行但存在失败为 `completed_with_failures`、退出码1；该退出码表示有失败，不表示本轮中途停止。人工中断、越预算等整体约束仍保留。

仅采集工具及其安全测试发生代码变更，生产源码、改写prompt、模型配置、三字段协议、前后端API/SSE均未修改。按项目Spec Kit plan/implement流程核对宪章、已有计划、研究、数据模型、[CLI契约](contracts/entrance-capture-cli.md)和quickstart，保存继续规则与方案调整。setup-plan保留已有计划，不切换Git分支；无extensions配置，规格checklist16/16。

题集仍为[已补全17题](../../backend/tests/fixtures/query_rewrite_v1_completed_cases.json)，版本 `query-rewrite-completed-v1-20261011`，SHA-256 `fa63b42fba32b0d156616b8de61f62553dff11a765572042f9fe9e4287e0c9e9`。前八题见[首次报告](phase-e-completed-first-20261011-report.md)与 `e-completed-first-20261011-01`；新增仅RW09–RW16、RW18，保存到新目录 `e-completed-rest-20261011-01`。原RW08保留failed，没有审阅改判addendum。

本机Ollama `qwen3:4b-instruct`、4.0B/Q4_K_M，digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`，temperature0/seed42。窗口4096、输入3072、输出768、安全余量256，单次等待120秒、每题总期限300秒；每题入口1次、工具0。新增调用上限9，前后合计17；无缓存、云端、Judge、自动重试、正式索引访问、平台登录或聊天API请求。

新[manifest](../../output/query-rewrite-v1/e-completed-rest-20261011-01/manifest.json)冻结配置、代码、模型和来源前缀；continuation中的RW08 `original_status=failed`、`accepted_status=failed` 表示沿用失败审阅，绝非质量通过。各请求、线程和模型调用ID、首次输出及审阅文件见新[summary](../../output/query-rewrite-v1/e-completed-rest-20261011-01/summary.json)。完整17题与来源哈希见[aggregate-summary](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/aggregate-summary.json)。模型仅收到冻结原题和必要上下文，预期标准不作为用户输入发送。

## 新增九题结果

| ID | 结果 | 入口耗时 | 输入/输出Token | 首次输出与依据 |
|---|---|---:|---:|---|
| RW09 | passed | 17.953秒 | 523/37 | 明确PN8733启动电压，原句保留，不被历史双对象覆盖 |
| RW10 | passed | 4.862秒 | 499/38 | MN-42上电检查完整单问原句保留，无澄清 |
| RW11 | failed | 5.202秒 | 505/45 | 拆成两问，第二问仅“运行记录保留多久”，漏共同设备PX-200；问号变化不作为失败原因 |
| RW12 | failed | 7.542秒 | 509/68 | 三问覆盖三项需求，但第三问型号变成 `PX-20、0` |
| RW13 | failed | 6.764秒 | 518/64 | `400 ms`变“40或 400 ms”；恢复子问缺型号、电压和持续时间 |
| RW14 | failed | 7.627秒 | 510/80 | 双方阈值和比较目标保留，但多生成第三路依赖比较检索，未按规格由最终汇总比较 |
| RW15 | failed | 8.069秒 | 511/80 | 输出四问且is_clear=true，超过三问上限；第三问还把型号写成 `PX-20、0`，现有schema返回invalid_model_output |
| RW16 | failed | 9.782秒 | 546/97 | 当前400 ms未被旧40 ms替换，但完整问题仍被误判不清楚，反问过压阈值及是否已发生事件 |
| RW18 | passed | 4.383秒 | 495/33 | 明确换题保留原句，旧过流恢复待办未进入模型输入 |

前批RW01–RW07通过、RW08失败，本批3通过、6失败，合计10通过、7失败；没有uncertain或未运行项。每题独立请求，17个模型调用ID、请求ID、线程ID各不重复。

## 七项失败与边界

- RW08：完整条件恢复问题被误判不清楚，反问所求恢复条件。保留[原始首答](../../output/query-rewrite-v1/e-completed-first-20261011-01/RW08.raw.json)及原人工失败，不重跑。
- RW11：第二子问缺共享型号，未独立明确检索对象，见[首答](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW11.raw.json)及[审阅](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW11.review.json)。
- RW12：型号失真，见[首答](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW12.raw.json)。UTF-8文件核对确认不是终端折行导致。
- RW13：数值条件被加上未给出的40 ms备选，并丢失恢复共享场景，见[首答](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW13.raw.json)。这是另一道题的独立首答，不等于重跑005原Q16，旧证据不覆盖。
- RW14：第三问为“PN8733的过流阈值是否高于PX-200的过流阈值”。三问没有超容量、型号没有错误，但违反spec用户故事3场景3“不机械增加第三路检索”，故属于拆分方式不符，见[审阅](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW14.review.json)。没有运行最终回答，不能说比较答案错误。
- RW15：正确预期应让用户选择最多三项，不应静默删需求或输出四问。JSON可解析，但四项questions不符合现有结构契约，因此自动记录 `invalid_model_output` 并继续RW16；未新增语义拦截。另有型号失真，见[首答](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW15.raw.json)和[采集后人工说明](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/RW15.manual-assessment.json)。
- RW16：反问“PX-200的过压保护阈值是多少”等本该检索的信息，见[首答](../../output/query-rewrite-v1/e-completed-rest-20261011-01/RW16.raw.json)。题设数字保留与清晰度正确是不同维度，不能因未抄旧40 ms就判整体通过。

以上是同一冻结生产prompt和模型下的实际表现，无法据此确定更深的内部原因，也未开展模型对比。没有将一般拆分措辞差异、普通空格或问号变化单独判失败。E只检验入口处理，不证明真实RAG答案、引文、比较或恢复结论正确。

## 用量、耗时与实际命令

新增模型9次、工具/云端/Judge/重试0；provider实测Token输入4616、输出542、合计5158。入口请求耗时合计72.184秒，模型trace72.175秒。新批次274.662秒含逐题审阅等待，外层命令281.876秒另含导入/准备，不能当单次推理时间。

新版17题总计模型17次、工具/云端/Judge/重试0；provider Token输入8739、输出931、合计9670，入口耗时127.841秒、模型trace127.824秒。前后批次分开启动，墙钟含中间用户交流，不生成单次全批次耗时。各真实题均在120秒/300秒预算内结束，未运行真实到期压力场景。

| 工作目录 | 实际命令 | 退出状态与结果 |
|---|---|---|
| 根目录 | `./.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；定位006，已有所需文档 |
| 根目录 | `./.specify/scripts/powershell/setup-plan.ps1 -Json` | 0；已有plan保留；仅规则调整，不覆盖历史产物 |
| 根目录 | `D:/newsoft/python.exe output/prepare_query006_e_continue.py` | 0；287个保护文件、17项正式数据与备份基线 |
| backend | `D:/newsoft/python.exe -m pytest -q tests/unit/test_query_rewrite_capture.py` | 1；26项setup error，默认系统临时目录PermissionError；未运行断言，日志保留 |
| backend | `D:/newsoft/python.exe -m pytest -q tests/unit/test_query_rewrite_capture.py --basetemp <仓库内工程目录>/pytest-temp-01` | 0；26 passed，pytest耗时2.73秒；1项pytest缓存写入权限warning，不影响断言；外层12.475秒 |
| backend | `D:/newsoft/python.exe -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_completed_cases.json --output ../output/query-rewrite-v1/e-completed-rest-20261011-01 --resume-from ../output/query-rewrite-v1/e-completed-first-20261011-01 --continue-on-failure` | 1；九题全部执行，completed_with_failures，3通过、6失败、0未运行 |
| 根目录 | `D:/newsoft/python.exe output/read_query006_e_rest.py RWxx` | 九题均独立读取0；核对保存的UTF-8首答，排除PTY显示干扰 |
| 根目录 | `D:/newsoft/python.exe output/audit_query006_e_all.py` | 0；汇总、调用/输入/唯一首答、文件保护和文档审计通过，不代表质量通过 |
| 根目录 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

工程运行器为 `output/run_query006_e_rest.py tests`、`tests-local`及`real`；精确命令分别保存在工程目录的invocation/exit JSON。原[工程失败日志](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/tests.log)、[工程通过日志](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/tests-local.log)、[真实调用参数](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/real-invocation.json)、[真实退出状态](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/real-exit.json)均保留。工程检查使用scripted provider、仓库独立临时目录，无正式检索或真实模型调用；与九题Ollama人工验收分开。

## 保护、任务状态和下一阶段

[保护基线](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/baseline.json)与[审计结果](../../output/query-rewrite-v1/engineering/phase-e-continue-20261011/artifact-audit.json)核对287个文件：只允许采集器及对应unit测试两处代码变更，其余285个保护文件未变。生产prompt、旧/新冻结夹具、原E/F报告与首答、失败清单、`.env`、前端及17项正式数据/索引和备份保留。未重启服务、修改正式库、提交或推送。

同步spec/plan/tasks、quickstart、验收矩阵、README和CURRENT_STATUS的最新事实。T030完成继续模式工程支持，T032已保存完整结果报告；T031完整输入首答已采齐但七项质量失败未闭环，仍未完成。原代词、省略和待办续补真实能力未因本次全测获得证明。

下一阶段原计划为F：正常平台API的Q16、C-UV和比较题端到端验收，当前仍只有旧Q16失败记录。用户本轮只要求测完E，本轮没有进入F或005/30题。后续修复prompt、改变模型或重测失败题需相应明确指示，不自动进行。**报告后暂停，等待用户验收。**
