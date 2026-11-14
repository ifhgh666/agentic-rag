# 007规划范围修订：取消阶段C

日期：2026-10-12。用户明确指示“不用阶段C”，本轮只修改规划，不执行A/B。

当前[计划](plan.md)只保留A模块初版/函数审阅和B接入/必要工程验证。移除17题真实模型阶段、执行命令、题集采集任务及仅为此服务的采集器指纹改造；实际改写函数的用户检查仍保留。B交付实际函数、缓存版本、源码指纹及工程结果后结束计划。

同步spec、plan、research、data-model、函数契约、quickstart、tasks及README/CURRENT_STATUS。实施任务由18项调整为14项，全部未执行：A六项、B八项；取消不等于完成。原T015–T017真实任务取消，文档收尾并入B；不将真实测试改名后塞进工程检查。真实模型质量未验证，006/005旧失败不变。

原[规划报告](planning-report.md)和原校验记录保留，表示修订前的三阶段计划；旧规划资料快照另存 `output/prompt007/planning-no-c-20261012/prior-documents/`，当前范围以本报告和更新后的plan/tasks为准。函数草稿保持原文，生产prompt.py仍不存在；生产源码、.env、007原报告及006记录不变。

## 实际命令与结果

| 工作目录 | 命令 | 结果 |
|---|---|---|
| 根目录 | `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0；沿用007计划，未覆盖模板 |
| 根目录 | `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0；按更新后规格/设计调整任务，遵循Spec Kit流程 |
| 根目录 | `D:/newsoft/python.exe output/prepare_prompt007_no_c.py` | 0；930项保护文件及修订前文档快照 |
| 根目录 | `D:/newsoft/python.exe output/update_prompt007_no_c_tasks.py` | 0；14项未执行任务，A/B映射和收尾同步 |
| 根目录 | `D:/newsoft/python.exe output/validate_prompt007_no_c.py` | 0；UTF-8/链接/任务格式、无活动C或真实采集命令、旧文件保护核对通过 |
| 根目录 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |

宪章重新核对：仍按阶段交付、提示与业务分离、不改数据/预算、工程与真实质量分开，没有新未知项。.specify/extensions.yml不存在，plan/tasks前后hook按技能跳过。资料校验见[validation](../../output/prompt007/planning-no-c-20261012/validation.json)，保护基线见[baseline](../../output/prompt007/planning-no-c-20261012/baseline.json)。

本轮没有工程或真实答题测试，没有新的产品模型/工具/Judge调用，没有启动服务、提交或推送。下一个可授权范围仍为A模块与函数审阅；本轮不开始实施。**报告后暂停，等待用户验收。**
