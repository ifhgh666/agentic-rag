# 007规划交付报告

日期：2026-10-12。授权仅“先写个计划”，要求独立prompt.py、函数按需取得提示、参考GiovanniPasq项目且由用户检查函数。

本轮完成[spec](spec.md)、[plan](plan.md)、[research](research.md)、[data-model](data-model.md)、[函数契约](contracts/prompt-functions.md)、[quickstart](quickstart.md)、[tasks](tasks.md)、[规格检查](checklists/requirements.md)与[改写函数草稿](prompt-review.md)，同步README/CURRENT_STATUS导航。feature指针定位007，实际Git分支仍为codex/model-driven-agent-loop，不创建/切换分支。006文件、报告、题集与失败保留。

计划A创建11个纯文本函数并交付实际get_rewrite_query_prompt全文供检查；B接入现有消费模块、保留非入口行为并隔离缓存/采集提示版本；C同模型17题完整首答，错误继续记录。18项实施任务全部未执行，规格内容检查16/16可规划，宪章研究前/设计后复核通过。

草稿是文档中的代码示意，生产 `backend/app/rag/prompt.py` 尚未创建，调用点和生产prompt未修改。模型/工具/云端/Judge新调用均0，没有工程或真实答题测试、服务启动/重启、模型下载、正式知识库操作、提交或推送。文件组织及prompt调整不被宣称为质量修复。

## 实际操作与验证

| 工作目录 | 实际命令或操作 | 状态 |
|---|---|---|
| 根目录 | git status --short、git diff --stat及相关代码只读核对 | 0；既有大量修改保留 |
| 根目录 | `.specify/scripts/powershell/create-new-feature.ps1 -Json -ShortName centralize-prompts ...` | 0；建立007目录及feature指针，未创建Git分支 |
| 根目录 | `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0；取得新计划模板，按Spec Kit填充设计产物 |
| 根目录 | `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0；取得任务模板及设计目录，生成18项未执行任务 |
| 根目录 | `D:/newsoft/python.exe output/prepare_prompt007_plan.py` | 0；保存既有源码、.env、006文档/首答保护基线 |
| 根目录 | `D:/newsoft/python.exe output/validate_prompt007_plan.py` | 0；UTF-8/本地链接、任务格式、函数草稿语法、门禁/指针和旧文件指纹核对通过；只是规划资料检查 |
| 根目录 | `git -c core.safecrlf=false diff --check` | 0；无whitespace错误 |
| 外部只读 | 上游prompts.py、schemas.py | 已核对职责/澄清边界/格式；本轮只参考，不执行其代码或复制不兼容正文 |

.specify/extensions.yml不存在，因此specify/plan/tasks前后扩展hook均按技能跳过；没有静默跳过必需hook。资料检查记录见[validation](../../output/prompt007/planning-20261012/validation.json)，旧文件保护见[baseline](../../output/prompt007/planning-20261012/baseline.json)。规划校验不代表函数已实现或真实模型通过。

当前实现仍是006规则，已补全17题10通过/7失败，旧指代失败及F首次失败保持。新函数草稿收窄澄清并保留完整问、共享条件、三问和容量例外，实际效果未测。下一范围仅为用户明确要求的A阶段模块创建/函数检查；B接入和C真实验证分别等待阶段指示。**报告后暂停，等待用户验收。**
