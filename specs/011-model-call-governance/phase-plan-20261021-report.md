# P2 技术方案阶段报告

日期：2026-10-21（America/Tijuana）。状态：**技术方案及设计产物完成，待用户验收；尚未实施。**

## 范围与流程

用户在 [规格报告](phase-spec-20261021-report.md)后明确要求“继续”。本轮按项目内 [speckit-plan](../../.agents/skills/speckit-plan/SKILL.md)执行研究和 Phase 1 设计，只形成方案，不拆任务或修改产品代码。

P1 的四项工程交付已经完成，本轮没有为它增设真实复验阶段。P2 继续围绕调用治理与诊断交付一致性，不扩展到 P3、提示业务调整、模型升级、额度扩大或正式评测。

## 完成文件

| 文件 | 内容 |
|---|---|
| [plan.md](plan.md) | 技术上下文、宪章门禁、目标结构、接入位置、A–D 阶段及未来 tasks Phase 映射 |
| [research.md](research.md) | 7 项设计决策、替代方案、源码与官方标准库依据 |
| [data-model.md](data-model.md) | 请求租约、逻辑调用、发送 attempt、结果及诊断状态模型 |
| [contracts/model-call.md](contracts/model-call.md) | 共同调用 interface、格式回退、严格活动预占、绝对期限、兼容 adapter、计量记录契约 |
| [contracts/diagnostics-and-sse.md](contracts/diagnostics-and-sse.md) | 非阻塞移交、有界快照/队列、完整不覆盖发布、安全回执及关闭契约 |
| [quickstart.md](quickstart.md) | 后续分阶段隔离验证和候选命令，明确尚未执行 |
| [spec.md](spec.md)及[需求清单](checklists/requirements.md) | 只更新已进入规划的状态和文档导航，不变更已确定的业务范围 |
| 本报告 | 命令、证据、限制、下一阶段和停止点 |

功能指针保持 specs/011-model-call-governance。setup-plan 返回的 BRANCH 为功能定位名 011-model-call-governance，而 `git branch --show-current` 的实际检出为 codex/model-driven-agent-loop；本轮没有创建、切换、提交或推送分支。

## 关键方案与后续阶段

共同调用入口隐藏物理容量、原预算、单次/整次期限、provider 执行和记录；业务语义及引用验证继续归原调用者，P1 证据准入不变。真实发送和允许的格式回退均先过 guard，逻辑调用只计一次；过期上下文不能因同 request_id 被重新注册而复活。

诊断采用有界后台队列，主路径不做序列化和文件 I/O、不等待落盘。queued 与 saved 分开，失败不覆盖问答；后台没有会话和 SSE 回调。既有私有 JSON 结构与公开事件保持兼容，最终文件不静默覆盖旧证据。

后续实施按四段拆分：A 诊断故障隔离、B 核心调用治理、C 全部调用者接入、D 组合交付和回归。每段有可演示行为、隔离验证及独立报告停止点；下一轮 tasks 必须按计划映射，不将笼统“执行”解释为全量贯穿。

## 只读研究与复核

speckit-plan 明确要求分发技术研究，故本轮使用两个只读研究代理分别核对模型调用和诊断设计。没有实施代理，没有让子代理运行模型、测试或应用；研究结果合并到 research.md。

方案复核未发现阻断性技术未知，补充并合入四条精确约定：预算锁内核验 lease 代次；关闭 guard 不承诺撤回关闭前已获准的外部请求；writing 在关闭后、发布前可转 skipped；快照拒绝自定义内建类型子类，避免覆写方法绕过有界工作量。

宪章门禁在设计前后均检查满足；需求质量清单原 16/16 项保持。以上是规划和只读设计判断，不是两轴代码审查或产品测试通过。

## 实际命令及证据

cwd：C:/Users/ifhgz/Desktop/agentic-rag。

- 完整读取 AGENTS、README、宪章、开发流程、规格、代码证据、最新报告、相关测试/评测约束与失败清单，核对适用子目录指令。
- Python 标准库脚本保存启动前 [168 个源文件 hash](../../output/governance011/plan-20261021/before-source-manifest.json)、[Git 状态](../../output/governance011/plan-20261021/before-git-status.log)、[完整 diff](../../output/governance011/plan-20261021/before-git-diff.log)、[原功能指针](../../output/governance011/plan-20261021/before-feature.json)及原规格/清单，退出 0。Git 的既有换行和历史测试目录权限提示保留，未清理工作区。
- `.specify/scripts/powershell/setup-plan.ps1 -Json`：退出 0，正确定位 011 并复制模板。未运行新 feature/branch 脚本。
- `git branch --show-current`：退出 0，实际分支如上。其余源码定位使用 Get-Content / rg，未导入应用。
- 读取 Python 3.11 官方 os、futures、threading 文档以核对不覆盖发布、取消及进程退出语义；来源近旁列于 research.md，没有运行真实请求或下载模型。
- 首次替换模板的 apply_patch 因同一补丁同时删除/新增同一路径而在验证阶段拒绝，没有改变文件；随后改为完整 Update 成功，未修改产品源码。
- `python output/governance011/plan-20261021/document-check.py`：退出 0；UTF-8、链接、产物、阶段映射及源码 hash 结果见 [document-check.json](../../output/governance011/plan-20261021/document-check.json)。
- `.specify/extensions.yml` 不存在，规划前后均无 before_plan / after_plan hooks 可执行。

没有运行 pytest、前端测试、类型检查、构建、原型、模型或服务，没有访问正式知识库、索引、密钥配置或修改 .env；没有新增依赖、发布 GitHub 规格/ticket、评论或关闭 issue、提交或推送。

## 限制与保留记录

诊断完整发布不保证断电持久性；有界关闭允许丢失未完成附属记录或遗留本次未发布临时文件。普通模型 executor 与非诊断日志体系不做全局重构，不能宣称任意 I/O、日志或进程退出故障均已解决。

输入附加格式约束得到检查后，原先漏算约束的临界请求可能提前容量失败；不扩大窗口或裁剪已读证据来规避。并发、慢写与 adapter 兼容仍须在实施时用假传输和可控故障证明，不把方案自洽写成可运行成绩。

两项既有提示原句断言、CURRENT_FAILURES.md 的真实失败、009 的真实容量失败及所有旧报告继续保留。P1 的 646 通过等记录不算本轮结果，当前没有新的问答/质量成绩。

## 交付与停止点

本轮完成 speckit-plan 的研究及 Phase 1 设计，没有生成 tasks.md、实施代码或发布任务。下一阶段是按项目内 speckit-tasks 将 A–D 转为依赖明确的工程任务；这仍不是直接实施 A 的授权。

**报告后暂停，等待用户验收。**
