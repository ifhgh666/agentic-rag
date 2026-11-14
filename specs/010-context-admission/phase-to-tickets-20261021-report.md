# P1 任务拆分阶段记录

日期：2026-10-21（America/Tijuana）。

## 授权与范围

用户明确要求“拆分”，本轮使用 Matt `/to-tickets` 将已发布规格 #1 拆成可独立验收的任务。此前授权的本事项流程替换继续有效；其他项目边界不变。

本阶段先交付拆分提案；用户随后回复“可以”，确认粒度和依赖后完成子任务发布与核对。本阶段不实施、不运行模型或工程测试。

## 交付与设计判断

- `ticket-breakdown.md`：4 个纵向行为任务，包含各自交付、验收条件、独立演示、依赖理由和覆盖核对。
- 依赖关系：T1 → T2、T3；T2、T3 → T4。
- T1 交付 Child 的最小容量反馈闭环及共同装载 module；T2 处理 Parent 窗口引用；T3 处理复合回复与缓存；T4 完成组合多分支的对外交付。
- T2 与 T3 没有相互业务阻塞，不因都使用相同 module 就增加虚假依赖；可能修改同一实现，实际执行时需协调。
- 没有单独的横向基础设施、schema 或测试任务。每项均包含与自身行为有关的实现及验证，不要求无关 UI 改动。

## 已发布任务与原生关系

| 提案 | 子任务 | GitHub 数据库 ID | 原生 Blocked by |
|---|---|---:|---|
| T1 | [#2](https://github.com/ifhgh666/agentic-rag/issues/2) | 5957272154 | 无 |
| T2 | [#3](https://github.com/ifhgh666/agentic-rag/issues/3) | 5957272958 | #2 |
| T3 | [#4](https://github.com/ifhgh666/agentic-rag/issues/4) | 5957273707 | #2 |
| T4 | [#5](https://github.com/ifhgh666/agentic-rag/issues/5) | 5957274706 | #3、#4 |

四项均为 OPEN、ready-for-agent，均原生关联父规格 #1。回读活跃阻塞数分别为 0、1、1、2；当前没有前置阻塞的任务仅为 T1。

## 实际只读核对

| 操作 | 结果 |
|---|---|
| UTF-8 读取根 AGENTS、README、to-tickets 技能、tracker/label/domain 约定和前阶段报告 | 成功；确认本轮仅拆分提案，发布前须核对粒度与阻塞关系 |
| `gh issue view 1 --repo ifhgh666/agentic-rag --json number,title,body,comments,url,state` | 退出 0；父规格 OPEN，正文 5262 字符，评论 0；按已发布正文拆分 |
| 初次包含父规格读取、功能指针与嵌套 AGENTS 搜索的命令单元 | 末尾 `rg` 无匹配退出 1；其中规格读取成功，不把无匹配视为读取失败；后续独立重读 Issue 退出 0 |
| `Get-Content` 只读检查模型工具回复和分支归并行为 | 成功；确认当前逐个处理工具回复、分支归并与部分失败路径，避免按假设拆分 |
| `git status --short`、定向 `git diff` 与全量 `git status --porcelain=v1 --untracked-files=all` | 退出 0；保留既有修改和未跟踪文件，未清理或还原；Git 对既有 pytest 临时目录发出权限提示 |
| `.specify/feature.json` | 仍指向 009；本轮未切换，不以该指针替代本次用户指定的规格 #1 |
| UTF-8 重新读取提案并核对任务标题、Blocked by 首句和验收项 | 退出 0；4 个任务分别包含 8、6、6、7 项验收条件；依赖为 T1 无前置、T2/T3 依赖 T1、T4 依赖 T2/T3，无未知任务或循环；未发现替换乱码字符 |
| 生成前后全量 Git 状态比较 | 两次命令均退出 0，新增路径仅为本轮提案与本报告，无既有状态条目移除；父规格及上一阶段报告未变更 |
| 用户确认后再次读取根说明、README、拆分及阶段记录，并执行 tracker 只读核对 | 成功；父规格 OPEN，发布前列表只有 #1，未发现重复任务 |
| `gh --version` / `gh issue create --help` | 退出 0；gh 为 2.92.0，未提供 --parent 参数，因此使用项目约定的 REST 子任务接口，无需升级工具 |
| `gh api repos/ifhgh666/agentic-rag/issues/1/sub_issues` 与 `.../dependencies/blocked_by` | 退出 0；确认原生关系接口可用，发布前均为空 |
| `gh issue create --repo ifhgh666/agentic-rag --title <已确认任务标题> --body-file <UTF-8 临时正文文件>` ×4 | 均退出 0；按 T1、T2、T3、T4 顺序创建 #2–#5，正文含父规格、交付行为、验收条件、独立演示及实施边界；先建立关系，再加 ready-for-agent 标签 |
| `gh api --method POST .../issues/1/sub_issues -F sub_issue_id=<子任务数据库ID>` ×4 | 均退出 0；建立四个原生父子关系；未编辑父规格正文或标题 |
| `gh api --method POST .../issues/<子任务号>/dependencies/blocked_by -F issue_id=<阻塞任务数据库ID>` ×4 | 均退出 0；建立 #3←#2、#4←#2、#5←#3、#5←#4；使用数据库 ID 而非 issue number |
| `gh issue edit <子任务号> --repo ifhgh666/agentic-rag --add-label ready-for-agent` ×4 | 均退出 0；所有关系建立后添加标签 |
| 回读四项 issue 正文、状态、标签及 blocked_by | 均退出 0；正文统一换行并忽略末尾换行后与发布正文一致，标签和原生依赖全部匹配确认方案 |
| 回读父规格及 sub_issues | 均退出 0；子任务恰为 #2、#3、#4、#5；父规格正文与标题逐字符未变，仍为 OPEN |

## 未执行及限制

- 初稿交付时未创建子任务；用户确认后才发布，并完成正文、标签与原生关系核对。
- 没有修改父规格 Issue 的正文、标题或关闭状态，仅建立本阶段获准的父子关系；没有改写上一阶段事实报告。
- 未运行 pytest、前端测试、真实模型、正式知识库或索引操作；覆盖表是拆分核对，不是测试通过证明。
- 本地仅维护提案和本报告；发布正文通过 Windows 临时目录中的 UTF-8 文件传递，没有产品代码、配置、旧失败清单或历史测试记录变更，没有提交或推送。

## 下一步与停止点

任务发布阶段已完成，待用户验收。后续若明确授权实施，首个可执行任务为 T1 / #2；不自动实施其他任务，也不把 ready-for-agent 标签解释为自动执行授权。

发布之后仍暂停，实施需要另行明确指示；对整份拆分方案的笼统执行指示只进入首个未完成任务。

报告后暂停，等待用户验收。
