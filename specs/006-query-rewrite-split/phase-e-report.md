# 006 阶段 E：有限真实入口验收报告

日期：2026-10-11。用户在 D 报告交付后要求“继续下一个阶段”，本轮仅执行 E（T030–T032），沿用项目内 [speckit-implement](../../.agents/skills/speckit-implement/SKILL.md)。**真实验收未通过：RW03 首次输出失去内部双空格，按顺序失败规则停止。2 项通过、1 项失败、14 项未运行；F 未启动。报告后暂停，等待用户验收。**

## 范围与完成文件

- 新增 [采集脚本](../../backend/scripts/capture_query_rewrite_v1.py)：固定 RW01–RW16、RW18，最多17次入口调用，每项一次。只使用现有 QueryAnalyzer 与本机 Ollama，不执行主图、检索、工具、回答、摘要或会话写入；不加载正式 Qdrant。
- 新增 [采集安全测试](../../backend/tests/unit/test_query_rewrite_capture.py)：scripted provider 验证冻结顺序、拒绝覆盖、原始记录先保存、失败/timeout/审阅中断停止、零重试、用量/ID、上下文隔离以及 provider/model/时间边界；模拟审阅只证明闸门，不证明语义正确。
- [manifest](../../output/query-rewrite-v1/e-first-20261011-01/manifest.json) 保存冻结夹具、代码哈希、模型 digest、非敏感配置；逐题 `.attempt.json`、`.raw.json`、`.review.json` 采用独占创建，不能覆盖。人工审阅有效通过后才提交下一题；失败或无法确认立即停止。
- [summary](../../output/query-rewrite-v1/e-first-20261011-01/summary.json) 保存实际运行状态。RW04–RW16、RW18 为 `not_run`，没有生成请求/调用 ID 或输出。
- 同步 README、CURRENT_STATUS、spec/plan/tasks、quickstart、验收矩阵、数据模型/契约与研究导航文字。没有调整验收标准、入口提示、模型配置、预算、正式 PDF/索引或旧失败证据，没有提交/推送。

原始输出保存的是现有 OllamaProvider 移除私有推理后的首次可见 `ModelResult.content`，不是完整 HTTP 传输体。原始模型结果、解析结果及审阅分别保存；未用程序恢复原句来掩盖本次错误。

## 冻结条件与协议

夹具版本 `query-rewrite-v1`，固定于2026-10-10；SHA-256：`b2bdf1e0a9328e2f49d90c87fd0a0feb5bde6208f3122abca0779fbacafc5e89`。

本机 `http://127.0.0.1:11434`，模型 `qwen3:4b-instruct`，4.0B / Q4_K_M；本地 `/api/tags` 只读核对的 digest：`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`。temperature=0、seed=42，窗口4096、输入3072、输出768、安全余量256，历史输入上限4000。入口隔离请求预算为1次、工具0；整请求≤300秒、模型等待≤120秒；无缓存、无自动重试、无 Judge、无下载或云端切换。

上下文来自 T001 固定夹具，并非生产会话或 PDF 证据。仅原题与 `input` 字段送给模型；预期值保存在本地供推理后人工审阅，未送入模型。每项使用独立的本地采集请求/线程 ID，这些不是正常聊天 API 的请求 ID。人工审阅者标识为 `coding_agent_manual`，并非新增模型 Judge 调用；逐项核对保存文件后才继续。

## 真实首次结果

| 案例 | 结果 | 入口耗时 | 实测输入/输出 Token | 人工核对 |
|---|---|---:|---:|---|
| RW01 | 通过 | 21.455秒 | 498 / 37 | 一问逐字保留 PN8733 原句；没有补写答案；clear=true，澄清为空 |
| RW02 | 通过 | 4.516秒 | 499 / 38 | 陌生但明确的 ZX-900 未纠错；完整单问逐字保留 |
| RW03 | **失败** | 5.336秒 | 505 / 43 | `Guide_V1.PDF` 后的两个空格合成一个，不满足逐字保留 |
| RW04–RW16、RW18 | 未运行 | — | — | 在首次失败后未继续提交，共14项 |

RW03 原题：`Guide_V1.PDF  中 PX-200 的启动电压是多少？`（文件名后两个 U+0020）。首次模型结果：

```json
{
  "is_clear": true,
  "questions": ["Guide_V1.PDF 中 PX-200 的启动电压是多少？"],
  "clarification_needed": ""
}
```

文件名大小写和型号保留，但原题总空格4个、输出3个；原始模型 JSON 已压缩空白，解析结果与其一致。因此这是入口真实保真失败，不能计为“只差格式所以通过”。保存依据：[首次原始记录](../../output/query-rewrite-v1/e-first-20261011-01/RW03.raw.json)、[人工失败审阅](../../output/query-rewrite-v1/e-first-20261011-01/RW03.review.json)。

| 案例 | 采集请求 ID | 模型调用 ID |
|---|---|---|
| RW01 | rw-e-94358dc22c3a4988b937695ae48492b6 | model-3c52a3c540894a42bde58cd1ecf7362b |
| RW02 | rw-e-fb06bc2d2a064e1393da754f4f54a40a | model-ee6d6fdba7254faca518bd88bdee6e03 |
| RW03 | rw-e-b4144c217668411b86971260cf32ee83 | model-cc90d416eabb4b3d927a3c8885133cf1 |

实际模型调用3次（每题 query_analysis=1），工具/云端/重试/Judge均0；实测输入1502、输出118，共1620 Token，`usage_source=provider`。入口耗时合计31.307秒，模型 trace 耗时合计31.302秒。批次墙钟150.600秒包含逐项人工审阅和工具等待，不能当作模型推理时延。没有本次单调用超时；没有实测120秒/300秒到期截断。

终端 PTY 换行曾造成显示错位，人工以磁盘 JSON 核对字符；一次未设 UTF-8 的只读打印乱码随后用 ASCII 转义重读。磁盘证据为有效 UTF-8，未修改原始结果。

## 实际命令、工程检查和退出状态

| 工作目录 | 命令/记录 | 退出状态与结论 |
|---|---|---|
| 仓库根 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；定位006。requirements检查清单16/16完成，只读未改；extensions.yml不存在，无前后钩子 |
| 仓库根 | `python output/run_query006_phase_e.py red-01` | runner退出1；子pytest退出2，采集模块未实现导致1个收集错误，原始记录保留 |
| 仓库根 | `python output/run_query006_phase_e.py green-01` | 0；87 passed in10.76秒，runner墙钟19.885秒；随后仅补充本地模型digest冻结 |
| 仓库根 | `python output/run_query006_phase_e.py green-02` | 0；最终87 passed in10.19秒，runner墙钟19.392秒；fake/scripted工程结果 |
| backend | `python -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/e-first-20261011-01 --stop-on-failure` | **1**；RW03人工验收失败，停止，不重试 |
| 仓库根 | `python output/check_query006_phase_e_artifacts.py artifact-check-before-report.json` | 0；原始记录/停止状态/实测用量、代码冻结、正式库和旧证据指纹核对通过 |
| 仓库根 | `git diff --check` | 0；有既有 LF/CRLF 提示，无 whitespace 错误 |

Python为 `D:/newsoft/python.exe`。工程 runner 实际执行：

```powershell
# cwd=backend；label最终为green-02
python -m pytest -p no:cacheprovider -q tests/unit/test_query_rewrite_capture.py tests/unit/test_query_rewrite_v1.py tests/unit/test_v4_query_analysis.py --basetemp ../output/query-rewrite-v1/engineering/phase-e-20261011/green-02-tmp
```

测试环境显式使用 fake / deterministic / sparse离线模式，DATA_DIR独立，QDRANT路径保持相对隔离；未覆盖`.env`。采集命令在新进程读取原有本地真实配置，未沿用工程fake设置。实际完整参数/工作目录见 [最终工程记录](../../output/query-rewrite-v1/engineering/phase-e-20261011/green-02.json)与[原始日志](../../output/query-rewrite-v1/engineering/phase-e-20261011/green-02.log)；首次采集[命令](../../output/query-rewrite-v1/engineering/phase-e-20261011/invocation.json)及[退出记录](../../output/query-rewrite-v1/engineering/phase-e-20261011/real-exit.json)另存。D的后端494/前端26/build结果保留；本轮没有前端或生产代码修改，未重复全量回归。

## 失败、限制与停止点

- T030/T032完成；T031仅部分运行且未通过，保持未勾选。六个完整单问未达6/6，不能宣布 SC-001 或 E 通过。
- 数字/单位/否定、历史400与40冲突、必要补全、条件式、明确换题、2/3问拆分、容量澄清与比较案例均未运行；不能从前两题结果外推。
- 正式库只做保护指纹核对：11个既有文件、`.env`均与E前基线一致；入口代码/夹具及A–D报告不变。旧 `CURRENT_FAILURES.md` 的005 Q16/C-UV记录完整保留，新006失败在本报告/原始记录和CURRENT_STATUS中说明；005 T018未完成，005 D/30题未启动。
- 本轮不修改提示修复失败，不原句强制覆盖、不扩大预算或换模型、不续跑剩余题。修复RW03及另批次E复验需要新的明确授权，不能覆盖本批次首答。
- 下一阶段原定为F（正常API Q16、C-UV与比较题首次补测），仍依赖E验收和单独授权；E未通过，本轮不进入F。

**报告后暂停，等待用户验收。**
