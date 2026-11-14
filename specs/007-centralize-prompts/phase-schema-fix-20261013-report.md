# 字段联动生成约束修复R报告

日期：2026-10-13。授权：用户‘修改这个bug，告诉我你怎么修改的？’。只执行补充R，T033–T036工程交付；旧17题、005/006质量待办不改判。报告后暂停，等待用户验收。

## 问题与修复

原QueryAnalysis的model_validator约束‘清楚时澄清为空’，但不会自动生成JSON Schema；Granite首答17次清楚状态都带非空澄清文字，运行后被拒绝。修复在[model_schema.py](../../backend/app/rag/model_schema.py)增加_query_clarity_schema并注册json_schema_extra，生成两个完整对象anyOf分支：true/1–3问/clarification_needed const空字符串，false/零问/minLength=1澄清。每个分支保留三个必填字段、类型与extra禁止，避免编译器仅处理分支时丢失约束。

实际provider仍直接绑定QueryAnalysis，此次没有修改provider、入口消费或prompt，也没有在prompt补输出格式。后置校验保留，不把‘无／否’转换为空串、不修改问题正文、不重试。schema哈希已有缓存隔离和窗口计入机制，修改后自动生效。schema增大仍服从原窗口限制，未提高预算。非空白/重复/长度与语义保真仍由既有校验及业务规则处理；本轮不解决RW13–RW15的业务改写问题。

## 文件与工程验证

修改独立schema、两处单元测试、requirements.txt（登记本机已有jsonschema 4.x供独立工程验证，未安装或升级，未引入生产调用）、007设计/契约/审阅/任务与两处导航。纯UTF-8 helper和证据位于output/prompt007/schema-fix-20261013。Spec Kit setup-plan/setup-tasks/check-prerequisites退出0，功能007正确定位，已有计划保留；16/16规格门禁只读通过。extensions.yml不存在，前后hooks无可执行项。未委派代理。

| 验证 | 命令与工作目录 | 退出状态 | 结果 |
|---|---|---|---|
| 修改前回归 | backend；见[命令记录](../../output/prompt007/schema-fix-20261013/before-command.json) | 1 | 40通过/8失败，复现6个状态反例及2个真实包装器传输断言；工具输出截断，未声称保存完整原始日志 |
| 相关工程 | 根目录 D:/newsoft/python.exe -B output/fix_query_schema_007.py targeted，内部backend pytest | 0 | 133通过；[日志](../../output/prompt007/schema-fix-20261013/targeted.log)、[实际完整命令](../../output/prompt007/schema-fix-20261013/targeted-command.json) |
| 完整后端工程 | 根目录 D:/newsoft/python.exe -B output/fix_query_schema_007.py regression，内部backend pytest tests/unit tests/contract tests/integration tests/security | 0 | 585通过；[日志](../../output/prompt007/schema-fix-20261013/regression.log)、[实际完整命令](../../output/prompt007/schema-fix-20261013/regression-command.json) |
| 真实合成协议与状态 | 根目录 D:/newsoft/python.exe -B output/fix_query_schema_007.py probe | 1 | 结构2/2有效、预期状态1/2通过；[命令记录](../../output/prompt007/schema-fix-20261013/probe-command.json) |
| git diff --check | 根目录 | 0 | 既有修改保留，无新增空白错误 |

上述工程测试使用fake/scripted与mock传输、临时数据/索引；包含生成schema独立验证、实际Ollama包装器发送format、显式兼容API假传输、矛盾输出拒绝/首答保留、缓存隔离、动作/预算/期限/API/SSE/隐私回归。不代表云端或真实检索问答质量通过。真实探测与工程检查分开。

## 真实合成首答（非17题成绩）

本机granite4.1:8b，digest=444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852，temperature=0、seed=42。项目QueryAnalyzer调用实际provider，新线程/请求、无缓存，每题最多一次、120秒模型/300秒请求。两种状态用合成输入检查，不依赖用户实时补充。仅验证结构及预期状态，未进行正式知识库检索/问答。

| 探测 | 结果 | is_clear | 澄清文字 | 端到端秒 | 记录 |
|---|---|---|---|---|---|
| clear | 通过 | True | 空字符串 | 46.847 | [首答](../../output/prompt007/schema-fix-20261013/probe-clear.json) |
| unclear | 失败 | True | 空字符串 | 8.360 | [首答](../../output/prompt007/schema-fix-20261013/probe-unclear.json) |

上表结果要求结构和预期清晰度状态同时正确。两次首答均通过字段联动校验；完整单问原句保留、澄清字段为空，本次bug路径正常。无历史‘它’仍被模型判为清楚并保留代词原句，属于未解决的语义误判，因此第二题及probe命令退出1，不能宣称真实澄清判断通过。独立[分析记录](../../output/prompt007/schema-fix-20261013/probe-analysis.json)区分结构与语义，原始输出未改。未增加模型重试或修改prompt来扩大修复范围。

模型调用2，工具/检索/云端/Judge/重试均0。实际provider输入1604/输出91 tokens，共1695；请求/thread/model_call_id、首答、trace、用量、模型/源码/schema指纹均在独立attempt与首答文件。[实际生成schema](../../output/prompt007/schema-fix-20261013/generation-schema.json)与[保护审计](../../output/prompt007/schema-fix-20261013/audit.json)可追溯。

## 保护、限制与停止点

核对435项当前文件，只有14项授权范围的既有文件变更；8659项历史output文件保持，正式数据/.env/旧报告/17题首答均未变。未启动或重启服务、修改模型配置、下载/安装资源、修改采集器或题集、构建前端、提交/推送。先前诊断曾误读不存在的specs/005/.../CURRENT_FAILURES.md，随后定位并完整查阅根CURRENT_FAILURES.md，仅只读失败。

字段联动生成约束的工程修复已交付，真实完整问路径通过；真实澄清判断尚未通过。修复交付不等于旧17题全部通过。下一步范围是用户另行授权的17题新版本入口复测；端到端、三项业务错误及无历史指代误判另按授权处理。原C仍取消，旧质量任务未勾选。本次运行中的正式后端是否加载新代码未验证，正常启动后读取新源码。

**报告后暂停，等待用户验收。**
