# 006 阶段 E 续测报告：RW07 代词补全失败后停止

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-11。用户明确接受“少一个空格可以的”，随后要求“继续执行阶段e”。沿用项目内 [speckit-implement](../../.agents/skills/speckit-implement/SKILL.md)，本轮仅续测E。**新增RW04–RW06通过，RW07失败，后10项未运行；按用户澄清后的标准，累计6通过、1失败、10未运行。E尚未通过，T031保持未勾选。报告后暂停，等待用户验收。**

## 验收依据与历史记录

[空格验收澄清](phase-e-whitespace-acceptance-20261011.md)允许不影响题意的普通空格数量变化。型号、数字、单位、文件名、否定、比较、共同条件和依赖仍须保持；补全/拆分按含义核对，不要求与夹具示例措辞逐字一致。

原RW03仅将 `Guide_V1.PDF` 后两个U+0020变成一个，按用户要求接受。另存[审阅补充](../../output/query-rewrite-v1/engineering/phase-e-resume-20261011/review-addendum.json)，关联原输出、原审阅与原summary的哈希；[原E报告](phase-e-report.md)及原failed审阅不覆盖。RW01–RW03没有重跑，不重新选取输出，也不增加前三题的模型调用。

## 本轮真实首次结果

| 案例 | 结果 | 入口耗时 | 实测输入/输出Token | 人工核对 |
|---|---|---:|---:|---|
| RW04 | 通过 | 20.299秒 | 506 / 45 | PX-200、16 A及[运行摘录已移除]等否定条件完整，原题保留 |
| RW05 | 通过 | 5.961秒 | 518 / 57 | 小数195.5 V、300 ms及是否欠压保护完整，没有给出答案 |
| RW06 | 通过 | 5.713秒 | 515 / 54 | 245 V、400 ms及是否过压保护完整，没有机械拆分共同参数 |
| RW07 | **失败** | 7.006秒 | 515 / 64 | 未利用唯一对象PN8733补全[运行摘录已移除]，反而要求用户重新说明设备 |
| RW08–RW16、RW18 | 未运行 | — | — | 首次实质失败后停止，共10项，没有请求/调用ID |

RW07输入历史唯一消息为“PN8733 的启动电压是多少？”，当前问“它的恢复条件是什么？”。保存的模型用户输入确认包含这条历史，输入没有裁掉对象。首次输出：

```json
{
  "is_clear": false
}
```

要求完成的最少补全是“PN8733 的恢复条件是什么？”或同义表达。即使模型认为恢复场景还需澄清，也应识别已有唯一设备；本次明确再次询问设备身份，未完成FR-004/SC-002的唯一指代补全。这是语义能力问题，与空格数量无关。程序正常接受该三字段JSON并返回澄清，没有新的运行时语义拦截；失败是离线人工验收判定。

依据：[RW07首次原始记录](../../output/query-rewrite-v1/e-resume-20261011-01/RW07.raw.json)、[人工审阅](../../output/query-rewrite-v1/e-resume-20261011-01/RW07.review.json)。没有用程序替换输出、修改prompt再重跑，或继续提交RW08。

| 案例 | 采集请求ID | 模型调用ID |
|---|---|---|
| RW04 | [运行记录已移除] | [运行记录已移除] |
| RW05 | [运行记录已移除] | [运行记录已移除] |
| RW06 | [运行记录已移除] | [运行记录已移除] |
| RW07 | [运行记录已移除] | [运行记录已移除] |

新批次入口模型4次，每题1次；工具、云端、Judge、自动重试、缓存命中均0。实测输入2054、输出220，共2274 Token，`usage_source=provider`。入口请求耗时合计38.979秒，模型trace合计38.974秒。批次内部墙钟223.814秒包含人工审阅与辅助读取；外层进程231.424秒包含启动及本地模型身份核对，均不能当作单题推理时延。四次均未触及120秒模型上限或300秒整请求期限，未实测到期截断。

累计七项各只有一次真实入口调用；按本轮标准RW01–RW06六个完整单问可接受，RW07失败，十项未测。这是跨两批的逐题首次记录汇总，不把原批次summary的2通过/1失败改写成新成绩。条件式、模糊指代、明确补充、2/3问拆分、比较、超容量、历史冲突和换题仍未测，不能推定通过。最终比较答案和保护/恢复质量属于F，本轮不评估。

## 完成文件、冻结条件与保护

- 更新[采集脚本](../../backend/scripts/capture_query_rewrite_v1.py)：增加 `--resume-from` / `--review-addendum`，只向新目录写原未运行的连续后缀；读取原完整summary，核对夹具、生产入口代码、配置、模型身份与审阅关联；拒绝已有输出目录、已尝试后缀和未经接受的旧失败。不改变默认完整批次与顺序失败停止行为。
- 更新[采集安全测试](../../backend/tests/unit/test_query_rewrite_capture.py)：新增10项续测安全检查，涵盖只运行14个剩余首次输出、旧证据不变、原失败审阅保留、补充说明不入模型输入，以及缺授权/哈希错误/参数变化/已尝试/不连续/新失败停止。
- 新批次证据保存到 `output/query-rewrite-v1/e-resume-20261011-01/`，含[manifest](../../output/query-rewrite-v1/e-resume-20261011-01/manifest.json)、每题attempt/raw/review及[summary](../../output/query-rewrite-v1/e-resume-20261011-01/summary.json)。只计本轮新调用，旧三题以哈希和原调用ID引用，不复制为新模型调用。
- 更新spec中的用户空格验收澄清、tasks实际进度，以及README、CURRENT_STATUS、plan和quickstart导航。阶段映射、技术架构不变；生产入口prompt、schema、API/SSE、前端、模型配置和预算均未修改，服务没有重启，也没有平台登录或聊天API请求。

夹具仍为 `query-rewrite-v1`、SHA-256 `b2bdf1e0a9328e2f49d90c87fd0a0feb5bde6208f3122abca0779fbacafc5e89`。模型仍为本机Ollama `qwen3:4b-instruct`，digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`，temperature0、seed42；窗口4096/输入3072/输出768/余量256。单次入口1模型、0工具，模型≤120秒、请求≤300秒，无摘要、检索、正式Qdrant加载、会话写入、模型下载或云端切换。

[保护基线](../../output/query-rewrite-v1/engineering/phase-e-resume-20261011/baseline.json)与[最终审计](../../output/query-rewrite-v1/engineering/phase-e-resume-20261011/artifact-audit-final.json)核对147项既有生产源码、前端、夹具、历史报告和E/F真实记录，全部保持哈希；正式数据/索引及已有备份17项与 `.env` 不变。`CURRENT_FAILURES.md`原005/F事实完整保留，本轮RW07新增失败在本报告和CURRENT_STATUS记录，不修改旧题失败状态。没有提交、推送、索引重建或正式数据写入。

## 实际命令与工程验证

| 工作目录 | 命令/操作 | 退出状态与结果 |
|---|---|---|
| 仓库根 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；定位006；requirements清单16/16，只读未改；extensions.yml不存在，无前后钩子 |
| 仓库根 | `D:/newsoft/python.exe output/prepare_query006_e_resume.py` | 0；独占创建保护基线和用户授权审阅补充，不调用模型 |
| 仓库根 | `D:/newsoft/python.exe output/run_query006_phase_e.py resume-01` | **0；97 passed in12.53秒**，runner墙钟22.926秒；fake/scripted工程检查 |
| backend | 本机 `/api/tags` 与 `continuation_cases` 只读预检查 | 0；模型digest、生产代码、配置一致，确认剩余14项RW04–RW16/RW18 |
| 仓库根 | `D:/newsoft/python.exe output/run_query006_e_resume_real.py` | **1**；真实RW07人工验收失败后停止，无重试、无后续题 |
| 仓库根 | `D:/newsoft/python.exe output/check_query006_e_resume.py` | 1；先检查报告到自身尚未生成的审计文件链接，产生一项missing_link；保护文件、配置、数据和代码均未变化，原审计记录保留 |
| 仓库根 | `D:/newsoft/python.exe output/check_query006_e_resume.py artifact-audit-final.json` | 0；核对即将生成的自身审计文件并保存后确认存在，保护文件、冻结代码、调用关联、未运行状态、UTF-8及全部本地链接通过 |
| 仓库根 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

工程runner实际命令（cwd=backend）：

```powershell
D:/newsoft/python.exe -m pytest -p no:cacheprovider -q tests/unit/test_query_rewrite_capture.py tests/unit/test_query_rewrite_v1.py tests/unit/test_v4_query_analysis.py --basetemp ../output/query-rewrite-v1/engineering/phase-e-20261011/resume-01-tmp
```

测试显式fake/deterministic/sparse离线模式、独立DATA_DIR、相对隔离Qdrant目录。没有覆盖 `.env` 或让这些环境设置进入真实子进程。[工程命令与退出记录](../../output/query-rewrite-v1/engineering/phase-e-20261011/resume-01.json)及[原始日志](../../output/query-rewrite-v1/engineering/phase-e-20261011/resume-01.log)保留。97项通过不证明真实补全质量；原D后端494/前端26/build0为历史结果，本轮无相关生产变更，不重复全量回归。

真实子进程实际命令（cwd=backend，仅设置输出编码UTF-8）：

```powershell
D:/newsoft/python.exe -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/e-resume-20261011-01 --stop-on-failure --resume-from ../output/query-rewrite-v1/e-first-20261011-01 --review-addendum ../output/query-rewrite-v1/engineering/phase-e-resume-20261011/review-addendum.json
```

[实际调用记录](../../output/query-rewrite-v1/engineering/phase-e-resume-20261011/invocation.json)与[退出记录](../../output/query-rewrite-v1/engineering/phase-e-resume-20261011/real-exit.json)另存。PTY中文换行显示仍有错位；人工每题另读磁盘UTF-8 JSON，以保存正文为依据，原输出不重写。该记录为现有provider移除私有推理后的首次可见正文，不是完整HTTP传输体。

最终只读审计的首次运行因报告链接指向本次审计文件、而链接检查早于文件创建，退出1。[首次审计](../../output/query-rewrite-v1/engineering/phase-e-resume-20261011/artifact-audit.json)保留，其中生产/历史文件、知识库、配置和冻结代码检查均通过。仅调整忽略尚待本次独占创建的自身审计目标、保存后验证存在；新结果另存final文件，没有覆盖失败记录或改动真实问答。

## 限制、任务与下一阶段

T030/T032保留已完成；T031因RW07真实补全失败和十项未测保持未勾选。F的T034及005的T018状态不变；空格差异接受不能抵消代词补全问题或F恢复条件缺失。

后续可以在用户明确授权后诊断入口prompt对唯一对象与澄清的处理，并另批次复验；本轮没有修改prompt或自动修复后重跑。E通过并获得用户指示后，下一阶段范围仍为F正常API Q16、C-UV和比较题的独立验收，不自动启动005 D或30题。

**报告后暂停，等待用户验收。**
