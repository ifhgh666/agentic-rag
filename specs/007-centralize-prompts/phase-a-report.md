# 007阶段A：独立提示词模块与函数审阅

日期：2026-10-12。用户明确授权“执行阶段A”。本轮仅T001–T006，创建独立模块、按既有行为整理非入口文本、交付实际改写函数供用户检查；不执行B调用接入，不恢复已取消的C真实测试。

**A模块交付完成，静态/等价检查通过，等待用户审阅函数。** [实际prompt.py](../../backend/app/rag/prompt.py)已创建，11个纯文本函数和独立 `REWRITE_PROMPT_VERSION="rewrite-prompt-v2"`。用户重点检查 `get_rewrite_query_prompt()`（第10行）；[审阅文档](prompt-review.md)同步其完整实际代码，返回文本与原规划草稿完全一致。

模块未被业务消费点导入，原query_analysis、Loop、generator等源码未修改，当前运行时仍是原提示。不存在“新函数已上线”或真实质量改善的结论。T001–T006完成，T007–T014八项留待B，取消C不计为通过。

## 已完成文件与来源

| 函数 | 参数及现有来源 | A检查 |
|---|---|---|
| get_rewrite_query_prompt | 无；007审阅草稿 | 返回文本完全一致；正文分角色、允许操作、澄清、保真、输出 |
| get_conversation_summary_prompt | max_chars；conversation_summary的system正文 | 256/2000/4096三个长度均逐字等价，保留summary JSON |
| get_orchestrator_prompt | protocol；agent_loop.LOOP_PROMPT和兼容附文 | native/structured两种逐字等价，不变工具决策 |
| get_context_compression_prompt | 无；Loop._compress | 保留keep/gaps连续引文协议 |
| get_aggregation_prompt | 无；generator._grounded_request | 保留答案、citation、claims及原题完整覆盖 |
| get_answer_generation_prompt | 无；generator.SYSTEM_PROMPT | 原兼容文本逐字等价 |
| get_evidence_selection_prompt | 无；model_compression.compress | 保留独立excerpts/gaps协议 |
| get_retrieval_rewrite_prompt | 无；query_planner.generate_with_result | 旧检索词提示等价，不重新启用旧路径 |
| get_answer_repair_prompt | feedback；generator修正消息 | 两组反馈逐字等价，不增加修正次数 |
| get_loop_repair_prompt | feedback；Loop修正消息 | 两组反馈逐字等价，保留协议/引文反馈区别 |
| get_aggregation_instruction | 无；分支汇总payload.instruction | 原字段内容逐字等价 |

这10个非入口函数合计15个等价场景，对照解析现有源码中的表达式取得原字符串，没有导入业务模块或provider。修正反馈只用合成字符串测试，未记录真实异常或私有数据。函数参数由未来调用方传入既有值，模块不读取设置或会话。

[函数契约](contracts/prompt-functions.md)冻结11项签名/消费者、动态摘要长度、native/structured附文及两类压缩与修正。更新spec/plan/tasks、quickstart、README与CURRENT_STATUS的事实导航，保留原规划和范围修订报告。

## 改写函数供检查的规则

完整单问保留原句；只允许必要指代/回指信息补全和独立需求拆分，最多三问。指代无法唯一确定才语义澄清，未知保护阈值、恢复条件或操作答案不能反过来向用户索要。容量选择单列，不能偷偷删除第四项；相关子问保留共享条件、否定和假设前提，比较仍由原题与最终回答覆盖。

组织参考已核对的GiovanniPasq提示模块；正文按用户要求独立编写，不照搬一般性润色、Markdown答案或provider结构化调用方式。没有添加程序数字/空格语义检测、入口重试或强制按单问恢复原句。实际模型是否遵守本轮未测，且真实测试阶段已取消。

## 实际命令与验证

| 工作目录 | 命令 | 退出状态与结果 |
|---|---|---|
| 根目录 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0；定位007，requirements内容门禁16/16 |
| 根目录 | `D:/newsoft/python.exe output/prepare_prompt007_stage_a.py` | 0；记录986项保护文件、17项正式数据/已有备份哈希及git状态/差异/分支 |
| 根目录 | `D:/newsoft/python.exe -I -B output/check_prompt007_stage_a.py` | 0；11函数语法/返回类型/无导入或顶层副作用、改写草稿等价、非入口15场景逐字等价通过 |
| 根目录 | `D:/newsoft/python.exe output/update_prompt007_stage_a_docs.py` | 0；同步实际函数代码与A状态，不接入消费点 |
| 根目录 | `D:/newsoft/python.exe output/audit_prompt007_stage_a.py` | 0；未接入、UTF-8/本地链接/阶段任务/旧文件与数据指纹核对通过 |
| 根目录 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

检查结果见[module-validation](../../output/prompt007/implementation-20261012-a/module-validation.json)，纯函数实际返回正文见[rewrite-return.txt](../../output/prompt007/implementation-20261012-a/rewrite-return.txt)。原草稿保存为[prompt-review-before](../../output/prompt007/implementation-20261012-a/prompt-review-before.md)，保护基线见[baseline](../../output/prompt007/implementation-20261012-a/baseline.json)，最终核对见[artifact-audit](../../output/prompt007/implementation-20261012-a/artifact-audit.json)。

本轮检查仅AST、编译及纯字符串函数执行，没有新pytest回归、fake/scripted provider、真实模型、检索、平台登录、知识库加载或前端构建。新增模块未接入，必要运行链回归属于B；本轮不增加只重复提示文字的单元测试。产品模型/工具/云端/Judge调用均0，无新请求ID或回答耗时。

忽略规则已核对.env/data/output/pycache/node_modules，未修改；extensions.yml不存在，implement前后hook按技能跳过。正式17项数据只读哈希核对，未重建/写入索引，未重启服务、修改.env、提交或推送。986项已存在保护文件保持，唯一新增生产文件是未接入的prompt.py；006/005报告、失败和原始输出不变。

下一范围仅B：用户检查实际函数并明确继续后，将业务模块改为按函数取提示，隔离新提示缓存并做必要工程检查。B尚未执行，C继续取消，不进入006 F或30题。按既有阶段边界，**报告后暂停，等待用户验收。**
