# 007 补充T：当前版本真实入口17题测试报告

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
日期：2026-10-13。授权：用户了解当前实现/模型准备、结构化首测失败及建议先测入口后要求“开始测试”。本轮只执行入口补充T（T029–T032），沿用此前用户要求的完整输入17题及遇错继续规则；不恢复原C或后续端到端。

**结果：17题全部运行，0通过、17失败、0未运行。覆盖完成，质量验收未通过。28项采集器隔离工程检查通过。**

## 完成范围与冻结条件

复用真实QueryAnalyzer和OllamaProvider直接分析题目，不经过平台HTTP、登录、图/检索或正式会话写入。采集器仅补已授权granite4.1:8b许可、prompt版本/schema指纹/prompt.py源码记录与续测核对，新增两项隔离检查；产品prompt/schema/provider、.env、预算、题集和正式数据保持。

本机模型granite4.1:8b，digest `444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852`；温度0、种子42、窗口4096、输入3072、输出768、安全256，单次120秒、每请求300秒。一题一个独立request_id/thread_id/model_call_id，首次入口最多1次；全批17次，无工具/正式检索/云端/Judge/缓存/重试。

题集 `backend/tests/fixtures/query_rewrite_v1_completed_cases.json`，SHA256 `fa63b42fba32b0d156616b8de61f62553dff11a765572042f9fe9e4287e0c9e9`，顺序RW01–RW16、RW18。四道需要補充的原题已按用户以前指示写成完整输入，本轮未恢复；这些成绩不能证明原代词、待办续补或省略补全能力。

协议query-rewrite-v1，提示rewrite-prompt-v3，prompt.py SHA256 `32a5db37bd5b47368bfe1061cb32bb8e76f90f062cffac1619ad0af25fe6c499`；生成schema SHA256 `1d8efb3ed9057bbf72fd17a84ba0d2f5b92021242cd3b9a1ab8d2962d15218a5`，其他源码指纹见manifest。沿用原采集器的phase=E记录字段，本批归属007补充T，以新目录、版本、模型和指纹独立识别，未续用旧成绩。

## 共同失败原因

17条首次模型答复均为可解析JSON，三个字段的类型/必填/最多三项满足生成结构，均被模型判为is_clear=true；澄清字段却全部非空：**“无”10题、“否”6题、“记录保留期限”1题**。当前QueryAnalysis既有联动validator要求清楚状态澄清字段为空字符串，因此17题均返回invalid_model_output、source=safe_fallback，未取得应用可用的结构化结果。

首答示例RW01：

```json
{
  "is_clear": true
}
```

问题文本已保留，但非空澄清违反当前状态契约。schema字段说明已传入模型，字段联动validator没有自动成为生成语法；本轮没有把“无/否”改成空字符串、放宽校验、改prompt/schema或重试。0通过是完整入口结果的验收，不表示17题问题文本全被改错。

## 逐题首次结果与业务观察

全部首答/attempt已先保存，再离线逐题解析复核联动失败。没有有效结构进入采集器的审阅file gate；另存review-analysis.json记录Codex逐题依据，未改写raw/summary。这里的代理检查等待用户验收，不冒充用户人工批准。

| 题号 | 完整入口 | 澄清字段 | 原始问题部分观察 |
|---|---|---|---|
| [RW01](../../output/prompt007/entrance-20261013/run/RW01.raw.json) | 失败 | 无 | 完整原题保持 |
| [RW02](../../output/prompt007/entrance-20261013/run/RW02.raw.json) | 失败 | 否 | 陌生型号仍判清楚，原题保持 |
| [RW03](../../output/prompt007/entrance-20261013/run/RW03.raw.json) | 失败 | 无 | 双空格合一按用户标准可接受；失败来自澄清字段 |
| [RW04](../../output/prompt007/entrance-20261013/run/RW04.raw.json) | 失败 | 无 | 否定和16 A保持 |
| [RW05](../../output/prompt007/entrance-20261013/run/RW05.raw.json) | 失败 | 无 | 195.5 V/300 ms及目标保持 |
| [RW06](../../output/prompt007/entrance-20261013/run/RW06.raw.json) | 失败 | 无 | 245 V/400 ms及目标保持 |
| [RW07](../../output/prompt007/entrance-20261013/run/RW07.raw.json) | 失败 | 否 | 已补齐PN8733原题保持，不证明原代词补全 |
| [RW08](../../output/prompt007/entrance-20261013/run/RW08.raw.json) | 失败 | 无 | 当前条件式与245 V/400 ms保持 |
| [RW09](../../output/prompt007/entrance-20261013/run/RW09.raw.json) | 失败 | 否 | 已明确PN8733的完整原题保持 |
| [RW10](../../output/prompt007/entrance-20261013/run/RW10.raw.json) | 失败 | 否 | 已补齐MN-42的上电检查目标保持 |
| [RW11](../../output/prompt007/entrance-20261013/run/RW11.raw.json) | 失败 | 否 | 两项目标与两处PX-200型号保持，一般措辞可接受 |
| [RW12](../../output/prompt007/entrance-20261013/run/RW12.raw.json) | 失败 | 无 | 三项目标和每问PX-200保持，一般措辞可接受 |
| [RW13](../../output/prompt007/entrance-20261013/run/RW13.raw.json) | 失败 | 无 | 恢复子问缺共享245 V/400 ms，另有业务失败 |
| [RW14](../../output/prompt007/entrance-20261013/run/RW14.raw.json) | 失败 | 无 | 两对象事实之外多拆第三路比较，另有业务失败 |
| [RW15](../../output/prompt007/entrance-20261013/run/RW15.raw.json) | 失败 | 记录保留期限 | 四需求没有请求选择三项，另有容量失败 |
| [RW16](../../output/prompt007/entrance-20261013/run/RW16.raw.json) | 失败 | 无 | 当前400 ms保持，未复制历史40 ms |
| [RW18](../../output/prompt007/entrance-20261013/run/RW18.raw.json) | 失败 | 否 | 新题原文保持，旧待办未进入当前输入 |

14题问题部分可接受是独立观察，不改变17题整体失败。RW13的第二问实际为“如果触发保护，如何恢复 PX-200？”，缺共享条件；RW14第三问实际为“PN8733 和 PX-200 的过流阈值中，哪个更高？”，属于依赖已检索事实的比较；RW15实际只问启动电压/过流阈值/维护周期，把第四个记录期限放在澄清字段而未请求选择。即使以后处理澄清字段契约，这三项业务问题也仍需另行验证。

与旧006完整输入成绩10通过/7失败相比，本轮prompt/schema/模型均改变。观察到当前RW08不再反问恢复答案、RW11/RW12没有旧型号缺失/失真、RW16保留当前400 ms；不能据此单独归因于换模型，也不能把原题集补全、旧失败或端到端结论改为通过。

## 实际命令、用量和时延

| 工作目录 | 命令 | 实际退出与结果 |
|---|---|---|
| 根目录 | `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0，定位007并保留已有plan |
| 根目录 | `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0，取得模板、保留旧完成任务，追加US6四项 |
| 根目录 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0，已有设计/任务；requirements只读门禁16/16 |
| 根目录 | `D:/newsoft/python.exe -B output/test_prompt007_entrance.py prepare` | 0，保存4677项已有文件和17项正式数据指纹，冻结安装模型 |
| 根目录 | `D:/newsoft/python.exe -B output/test_prompt007_entrance.py engineering` | 0，28 passed，pytest3.34秒、外层15.266秒；scripted和临时目录 |
| 根目录 | `D:/newsoft/python.exe -B output/test_prompt007_entrance.py capture` | 1，completed_with_failures；17题全测，无停止题，外层241.765秒 |
| 根目录 | `D:/newsoft/python.exe -B output/analyze_prompt007_entrance.py` | 0，17首答/独立ID/用量/联动拒绝复核，保存逐题依据和统计，不再次调用模型 |
| 根目录 | `D:/newsoft/python.exe -B output/audit_prompt007_entrance.py` | 0，版本/源码/输入/唯一首答/预算/证据保护和git diff --check通过，不表示质量通过 |

工程子命令在backend执行：`D:/newsoft/python.exe -B -m pytest -q tests/unit/test_query_rewrite_capture.py --basetemp=C:/path/agentic-rag/output/prompt007/entrance-20261013/pytest -o cache_dir=C:/path/agentic-rag/output/prompt007/entrance-20261013/cache`。28项包含新模型许可、prompt变化拒绝续测，以及已有失败继续/停止模式、预算、模型/配置隔离和不覆盖证据；没有扩大为全量工程回归。

17次真实模型，工具/检索/云端/Judge/缓存/重试0。提供方实测输入13872、输出982、总14854 Token；入口请求耗时合计237.981秒，模型trace合计237.947秒，最长单题48.909秒；全批238.09秒，外层241.765秒包括导入/准备。独立请求均在120/300秒上限内，没有真实到期压力场景，不将全批时间当单请求期限。

期间一次只读统计命令误取usage.input_tokens而报KeyError，实际字段为prompt_tokens；随后按真实字段汇总成功，未重新推理、覆盖记录或改变数据。扩展配置不存在，Spec Kit plan/tasks/implement前后hooks按规则跳过，无代理委派、提权或安装依赖。

## 证据、保护与停止点

[manifest](../../output/prompt007/entrance-20261013/run/manifest.json)、[批次summary](../../output/prompt007/entrance-20261013/run/summary.json)、[逐题依据](../../output/prompt007/entrance-20261013/review-analysis.json)、[统计](../../output/prompt007/entrance-20261013/metrics.json)、[工程记录](../../output/prompt007/entrance-20261013/engineering.log)、[工程命令](../../output/prompt007/entrance-20261013/engineering-command.json)、[真实命令](../../output/prompt007/entrance-20261013/capture-command.json)、[保护基线](../../output/prompt007/entrance-20261013/baseline.json)、[最终核对](../../output/prompt007/entrance-20261013/audit.json)可追溯。各raw/attempt包含request_id/thread_id/model_call_id、原始输入、首答、用量和实际时延；这些是采集器内部ID，不是平台HTTP请求ID。

只允许采集器、对应unit测试、当前设计/导航与新证据变化；产品代码、.env/示例、题集、旧报告/首答、CURRENT_FAILURES和17项正式数据/备份保护。未启动/重启后端、重建正式索引、运行RAG图、改模型、提交或推送。

007 T029–T032的采集与交付工作完成，累计28项工作完成不表示质量合格。SC-009覆盖/可追溯完成；真实入口未通过，原006 T031/T034及005 T018仍未完成。原C取消，不自动恢复正式30题。

下一阶段建议先处理当前结构化联动输出与三项拆分/容量问题，再按用户明确范围复验或进入平台端到端；本轮只测试，没有实施修复。**报告后暂停，等待用户验收。**
