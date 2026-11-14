# Quickstart: 分阶段验证指南

2026-10-11：A–D工程完成；用户接受RW03空格差异后继续E，RW04–RW06通过，RW07补全失败后停止，本轮标准累计6通过、1失败、10未运行；续测工具工程检查97 passed。见[E续测报告](phase-e-resume-20261011-report.md)。原E/F报告保留，F原Q16入口failed、完整答案not_verified，另两题not_run。

执行前必须读取根AGENTS、当前规格/计划/任务及最新报告，确认只获准一个阶段。以下命令是未来操作说明，不是本轮通过记录。

## A–C针对性工程验证

在backend目录，沿用项目现有测试夹具的临时data/Qdrant目录和fake提供者；不占用运行中正式索引。不覆盖backend/.env。

```powershell
D:/newsoft/python.exe -m pytest -q tests/unit/test_v4_query_schema.py tests/unit/test_v4_query_analysis.py tests/unit/test_query_rewrite_v1.py tests/unit/test_conversation_memory.py tests/integration/test_v4_clarification_flow.py
```

`test_query_rewrite_v1.py` 已在 A 阶段创建；B 前端动作检查、C 图/分支/生成相关检查均已有阶段报告。每阶段以 tasks.md 实际任务范围选择检查，不提前实施下一阶段。Windows 临时目录权限受限时使用仓库 output 下独立 `--basetemp`，Qdrant 路径保持相对测试 data_dir 隔离。

## D完整工程回归

```powershell
# backend目录
D:/newsoft/python.exe -m pytest -q tests/unit tests/contract tests/integration tests/security
# frontend目录
npm test -- --run
npm run build
```

记录工作目录、环境隔离、退出码、原始输出路径。fake结果只证明工程协议。

## E真实入口采集

当前结果：新版17题已全测，10通过、7失败、0未运行，见[完整E报告](phase-e-completed-all-20261011-report.md)。本次剩余九题遇错继续已结束，下方命令是执行记录，不得自动重复运行或覆盖目录。

2026-10-11用户已指示本轮E遇错继续，按[继续规则](phase-e-continue-policy-20261011.md)从新版RW09开始，仅运行未提交九题；原RW08保持失败。backend目录执行：

```powershell
D:/newsoft/python.exe -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_completed_cases.json --output ../output/query-rewrite-v1/e-completed-rest-20261011-01 --resume-from ../output/query-rewrite-v1/e-completed-first-20261011-01 --continue-on-failure
```

本次继续模式取代下列历史停止说明，完成全题后保存报告；不执行F。不能复用输出目录或重跑已采集题。

当前后续测试输入按用户要求使用[已补全问题题集](../../backend/tests/fixtures/query_rewrite_v1_completed_cases.json)，RW07–RW10已明确对象/条件/参数。见[调整报告](phase-e-completed-fixture-20261011-report.md)。用户随后授权首次真实测试：7通过、1失败、9未运行，在RW08完整问题误判不清楚处停止，见[新版E首次报告](phase-e-completed-first-20261011-report.md)。原题集保留作历史和工程覆盖，原RW07失败不被新题替代为通过。新题集只测完整问题处理，不能证明原补全与澄清能力；下列新批次命令仍需相应执行指示。

```powershell
# backend目录；仅在用户明确要求执行新题集时使用新输出目录
D:/newsoft/python.exe -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_completed_cases.json --output ../output/query-rewrite-v1/e-completed-<new-run-id> --stop-on-failure
```

题集内容和哈希与旧题集不同，不传旧 `--resume-from` 或复用旧成绩；本轮实际以新目录 `e-completed-first-20261011-01` 执行此采集命令，RW08失败停止，不可覆盖或自动续测。以下旧题集说明保留历史协议。

T030的 `backend/scripts/capture_query_rewrite_v1.py` 已实现。首批 `e-first-20261011-01` 已停止，不可覆盖；用户接受RW03空格差异后，使用新目录与独立人工审阅补充，从未运行后缀续测。本轮 `e-resume-20261011-01` 在RW07实质失败后已停止，不可覆盖或自动续测。下列命令仅供明确授权后的新完整批次使用：

```powershell
# backend目录，仅入口隔离夹具；不是30题评测
D:/newsoft/python.exe -m scripts.capture_query_rewrite_v1 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/<run-id>/ --stop-on-failure
```

固定RW01–RW16、RW18，最多17次入口模型调用，每项一次；只允许本机 Ollama 与冻结模型 `qwen3:4b-instruct`，拒绝已有输出目录。模型失败、原文/条件失真或人工无法确认时保存输出、耗时/用量和调用ID，停止后续顺序案例；已运行成绩不可覆盖。模型输入只用夹具的原题和上下文，预期值只供推理后的审阅。人工判断清晰度、补全、拆分、否定和条件关系，不能仅用字符串列表数量作语义验收。

每项保存 `.attempt.json` 和 `.raw.json` 后，终端等待审阅 JSON（必填 `status=passed/failed/uncertain`、`reviewer`、`rationale`）。只有有效 `passed` 才提交下一项；失败、无法确认、输入无效或中断均停止，无模型 Judge 或自动重试。`manifest.json` 冻结夹具/代码哈希、非敏感配置和本地模型 digest；`summary.json` 保存实际状态，未运行项没有调用 ID。原始输出是现有提供者移除私有推理后的首次可见正文，不是完整传输体。

报告保存`phase-e-report.md`，结束本轮等待用户，不能继续F。17项每模型等待≤120秒，实际总时长不承诺；失败停止，绝不后台继续。

本轮已执行的续测参数为 `--resume-from ../output/query-rewrite-v1/e-first-20261011-01 --review-addendum ../output/query-rewrite-v1/engineering/phase-e-resume-20261011/review-addendum.json`，输出另存 `e-resume-20261011-01`。采集器核对原夹具、生产入口代码、模型身份与配置，拒绝缺少人工接受依据、已尝试后缀或不连续清单。只读取旧文件，原失败审阅不改写；新批次只计本次实际调用，前三题的原请求/调用ID单独引用。此续测支持不新增产品问题校验；原实质失败、超时和格式失败不能凭空改为成功。

## F正常API三题补测

T033 的 `backend/scripts/capture_query_rewrite_e2e.py` 已实现，只用正常聊天API；凭据隐藏交互读取，不放参数或报告，不新建原始prompt调试接口。用户随后提供本机登录输入，首次批次只提交Q16一次，入口质量失败后停止，正常注销完成；没有后台续测。39项工程检查不能作为三题真实验收。

`e2e-first-20261011-01` 已存在，不能覆盖或从中续跑。新的补测须先获得明确授权、使用新目录；在本机终端提示中隐藏输入平台密码，不加入命令参数。下面仅为未来新批次命令模板，不是继续授权。

```powershell
# cwd=backend；前端5173、后端8000及Ollama需可用
D:/newsoft/python.exe -m scripts.capture_query_rewrite_e2e --url http://127.0.0.1:5173 --cases tests/fixtures/query_rewrite_v1_cases.json --output ../output/query-rewrite-v1/e2e-<new-run-id> --stop-on-failure
```

每题先保存 `.attempt.json`、原始 `.sse.txt` 和 `.raw.json`，再等待审阅JSON：`entrance_status`、`answer_status`（passed/failed/not_verified/uncertain）、`reviewer`及`rationale`；可用`checks`分别记录数字/条件/保护/恢复/比较/引用。只有入口和完整答案均passed才提交下一题；正常澄清也只表示入口行为可验，完整答案未验证时停止。`manifest.json`冻结原题、代码和数据指纹；`summary.json`保存未运行项。用量不可得保留null，不写成0。

`--credential-dialog`可选择本机遮掩密码框。原准备轮该方式未获得输入、采集进程已停止；本次使用getpass隐藏stdin正常登录，登录/认证响应均未保存。

冻结模型、非敏感预算、正式PDF/索引哈希、原题及会话方式；先原Q16一次，再C-UV一次，最后比较触发/恢复电压一次。任一顺序验收失败或需要澄清导致完整回答未验证时，保存报告并暂停，剩余题标未运行，不自动补充对象、追问或重试。若用户另行授权只查入口或继续剩余题，另轮记录。

每题新线程，不发标准答案、历史或提示；最多三请求、每请求≤300秒、总模型≤36。记录完整原始答复和依据、保护/恢复/欠压/比较判断、题设/文档阈值/推导、model/tool次数及provider实测或估算用量来源。答案质量与入口结果分别结论。

服务需要重启时先核对PID/端口并说明进程内会话/缓存清空；不自动扩大超时或换模型。本轮原服务未运行，已隐藏启动后端8000和前端5173，保存PID/日志；没有重启已有活跃服务，也未改`.env`。恢复前仍需重新确认端口、健康状态和真实配置。

F报告后暂停。真实300秒到期截断仍未在本新批次单独验证；005原正式30题D和T018需独立授权，不自动继续。
