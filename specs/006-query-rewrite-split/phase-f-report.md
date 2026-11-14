# 006 阶段 F：采集工具完成，真实三题待登录

日期：2026-10-11。用户在 E 失败报告后再次要求“继续下一个阶段”，本轮只进入 F（T033–T035），使用项目内 [speckit-implement](../../.agents/skills/speckit-implement/SKILL.md)。继续指令不改变 E 的失败结论，也不把 T031 勾选为完成。

**本轮完成 F 采集工具和39项隔离工程检查；正常平台登录尚未获得隐藏密码输入，三道真实题全部未提交。F真实验收未完成，不能判通过或判模型答题失败。等待中的采集进程已停止，没有后台续测。报告后暂停，等待用户验收与安全登录输入。**

## 完成文件与行为

- [采集工具](../../backend/scripts/capture_query_rewrite_e2e.py)：从冻结RW24读取Q16、C-UV、比较题，顺序不可更换；每题独立新线程，只提交原题和明确新题动作，使用正常 `/api/auth/login` 与 `/api/chat/stream`。
- 密码通过 `getpass` 隐藏交互输入；可选 `--credential-dialog` 使用本机遮掩输入框。无密码/Token参数，认证响应不保存；凭据仅在本次进程内用于本机登录，结束时尝试正常注销。
- 每题先独占保存 `.attempt.json`、首次 `.sse.txt` 与 `.raw.json`，再分别人工审阅 `entrance_status` 和 `answer_status`。只有两者均通过才提交下一题；澄清、失败、timeout、用量不可得、错误调用计数、人工无法确认或知识库指纹变化均停止，无自动补充/追问/重试/Judge。
- 原始答案、引用、核验卡、用量来源与请求/调用ID按实际保存；本地既有 `logs/loop_traces/<request-id>.json` 仅按准确UUID定位并关联哈希，另提取模型首次可见输出和工具轨迹。不新增HTTP调试接口，不把全提示词搬入公共事件。
- `manifest.json`冻结原题、模型配置、代码与正式PDF/文档记录/索引/Qdrant存储指纹；`summary.json`记录实际状态，未运行项没有请求ID。用量不可得保留null，不写成0。
- [安全测试](../../backend/tests/unit/test_query_rewrite_e2e_capture.py)使用HTTP stub及临时文件，覆盖拒绝覆盖、固定三题/新线程/零标准答案注入、原始证据保存、分别审阅、格式/timeout/未知用量/库变化停止，以及认证不落盘。

生产入口、图、模型提示、预算、前端源码、已有夹具、`.env`和正式库均未修改。README、CURRENT_STATUS及006的规格/计划/任务/指南/契约导航文字已同步为“F工具完成，真实待登录”，没有宣布006功能完成。

## 当前真实状态

| 题目 | 原题 | 实际状态 | 入口 / 完整答案 |
|---|---|---|---|
| Q16 | 设备输入电压为 245 V，持续 400 ms，会触发什么保护？之后如何恢复？ | **not_run** | 均未评估 |
| C-UV | PX-200 输入电压为195 V，持续300 ms，是否会触发欠压保护？请说明判断依据。 | **not_run** | 均未评估 |
| COMPARE | PX-200 的过压保护触发电压和恢复电压分别是多少？哪个更高？ | **not_run** | 均未评估 |

聊天API请求0、真实模型/检索工具/云端/Judge调用均0；没有实际回答、引用或请求ID。Token和真实问答耗时为“不适用/未运行”，不能把工程stub用量或时延移作真实成绩。

已启动采集器的遮掩密码框模式并等待输入，但没有得到密码，未调用登录接口，未创建真实批次输出目录。随后仅终止这一个等待中的采集进程（PID30548；路径和启动时间已核对），Shell退出1；这是交互未完成，不是模型质量失败。未提交Q16，也未跳到C-UV或比较题。结构化事实见 [pending-auth.json](../../output/query-rewrite-v1/engineering/phase-f-20261011/pending-auth.json)。

正常平台认证需要交互凭据。[T033](tasks.md)明确要求“隐藏交互凭据”，[操作规范](../../docs/testing-and-operations.md)要求密码不进入参数、报告或版本控制。本轮缺少这项输入，因此真实采集尚不能完成；不要在聊天中发送密码。

## 服务、配置与正式库保护

初始本地API8000和前端5173连接被拒绝；Ollama11434正常，已安装 `qwen3:4b-instruct`。正式Qdrant只读SQLite核对现有8个Point后，使用已有配置隐藏启动后端和前端，未重建或迁移索引。

| 服务 | 本轮PID | 状态 |
|---|---:|---|
| 后端8000 | 52988 | 本轮新启动，`/api/health`返回200、`index_ready=true`；交付时保持可用 |
| 前端5173 | 57652 | 本轮新启动，前端代理健康检查200；交付时保持可用 |
| 等待登录的采集器 | 30548 | 已停止；没有后台评测请求 |

本轮原服务没有运行，因此没有重启已有活跃服务或清空其会话；新后端的会话/缓存为空。PID仅为当前快照，恢复时须重核端口和进程归属。启动日志和PID见 [services-started.json](../../output/query-rewrite-v1/engineering/phase-f-20261011/services-started.json)、[后端启动日志](../../output/query-rewrite-v1/engineering/phase-f-20261011/backend-startup-errors.log)及[健康检查](../../output/query-rewrite-v1/engineering/phase-f-20261011/startup-health.json)。

非敏感准备快照见 [profile-prepared.json](../../output/query-rewrite-v1/engineering/phase-f-20261011/profile-prepared.json)：Ollama `qwen3:4b-instruct`，temperature0、seed42，本地model digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`；单/多总模型8/12、入口1、工具16，整请求300秒、模型等待120秒，窗口4096/输入3072/输出768/安全余量256。Dense=fastembed，实际`sparse_offline_fallback=false`，未调整配置；本轮没有编码或检索，不能据此声称BM25初始化完全离线。

采集器沿用服务器300秒绝对期限；HTTP传输留5秒接收超时终态，不增加模型预算或服务器执行期限。每请求12次、三请求总36次为上限；本轮没有验证真实到期截断或模型时延。

正式库11个历史保护文件及6个index/Qdrant存储文件指纹均与F前基线一致，`.env`未变化；64份受保护文件（生产代码、固定夹具、CURRENT_FAILURES、A–E报告等）无变化。基线：[baseline.json](../../output/query-rewrite-v1/engineering/phase-f-20261011/baseline.json)，核对：[artifact-check-before-report.json](../../output/query-rewrite-v1/engineering/phase-f-20261011/artifact-check-before-report.json)。运行日志与模型缓存不属于库内容指纹，Qdrant的进程锁也不纳入内容哈希。

## 实际工程命令与退出状态

| 工作目录 | 命令/操作 | 退出状态与结果 |
|---|---|---|
| 仓库根 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；定位006；requirements清单16/16完成，只读未改；extensions.yml不存在，无前后钩子 |
| 仓库根 | `python output/run_query006_phase_f.py red-01` | runner1、子pytest2；新模块未实现时1个收集错误，日志保留 |
| 仓库根 | `python output/run_query006_phase_f.py green-01` | 0；36 passed in8.10秒，runner16.561秒 |
| 仓库根 | `python output/run_query006_phase_f.py green-02` | **0；最终39 passed in8.21秒**，runner17.162秒；新增负数/bool/超额调用计数断言 |
| backend | `python -m scripts.capture_query_rewrite_e2e --url http://127.0.0.1:5173 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/e2e-first-20261011-01 --stop-on-failure --credential-dialog` | 等待隐藏登录输入，无聊天请求；该等待进程终止后Shell退出1 |
| 仓库根 | `python output/check_query006_phase_f_artifacts.py artifact-check-before-report.json` | 0；库/索引/env/64份保护文件一致，三题未运行，文档UTF-8有效 |
| 仓库根 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

Python仍为 `D:/newsoft/python.exe`。最终工程runner实际命令：

```powershell
# cwd=backend
python -m pytest -p no:cacheprovider -q tests/unit/test_query_rewrite_e2e_capture.py tests/unit/test_query_rewrite_capture.py tests/contract/test_chat_stream_api.py tests/contract/test_chat_request_deadline.py --basetemp ../output/query-rewrite-v1/engineering/phase-f-20261011/green-02-tmp
```

测试显式fake/deterministic/sparse离线模式、独立DATA_DIR和相对Qdrant路径，不占用正式索引。实际参数及退出码见 [green-02.json](../../output/query-rewrite-v1/engineering/phase-f-20261011/green-02.json)，原始输出见 [green-02.log](../../output/query-rewrite-v1/engineering/phase-f-20261011/green-02.log)。红/绿中间记录均保留；本轮没有生产/前端变更，未重复D全量后端494、前端26和build检查。

服务启动实际使用 `Start-Process -WindowStyle Hidden`：后端 `D:/newsoft/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`（cwd backend），前端 `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort`（cwd frontend），分别保存stdout/stderr。

辅助操作曾有一次只读SQLite命令引号错误，改用here-string后读取8个Point；一次Get-CimInstance只读PID查询被拒绝，后改用Get-Process核对；第一次停止进程的启动时间精确比较因毫秒未匹配而拒绝操作，随后核对到秒后仅停止30548。没有自动审批拒绝、未停止后端/前端或其他进程，未删除证据。

## 继续方式与未评估项

T033完成；T034保持未勾选；T035保存本待测报告，不表示F通过或006完成。E的RW03失败及其后14项未运行仍保留，005的Q16/C-UV旧失败不变，005 T018未完成，005 D和30题未启动。

继续F真实采集需要在可见本机终端完成隐藏密码输入。可复用命令如下；输出目录必须不存在，本轮尚未创建该目录：

```powershell
Set-Location -LiteralPath 'C:\Users\ifhgz\Desktop\agentic-rag\backend'
D:/newsoft/python.exe -m scripts.capture_query_rewrite_e2e --url http://127.0.0.1:5173 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/e2e-first-20261011-01 --stop-on-failure
```

输入密码后才提交Q16首次请求；不要把密码加入参数或聊天。每题提交后分别人工审阅入口和完整答案，保存依据，再决定是否继续下一题；有合理澄清也不能计为完整保护/恢复答案通过。标准答案、历史或提示不发送给平台。

当前正式PDF包含推荐问答，未来F结果不能当作无泄漏检索质量评分；数字/条件推导、保护/恢复、欠压、比较、引用和真实耗时均仍未评估。未下载模型、未扩大预算、未改提示、未绕过认证；后续仍限定F，不自动开始E修复/复验或其他阶段。

**报告后暂停，等待用户验收与安全登录输入。**
