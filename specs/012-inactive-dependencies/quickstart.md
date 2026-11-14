# P3 隔离验证指南

状态：A/B 工程验证已运行。最新实际结果为后端 802 passed / 2 failed / 24 skipped / 2 deselected、前端 27 passed 与 noEmit 通过；未运行真实模型。实际命令和原始记录见 [A 报告](phase-a-report.md)及[B 报告](phase-b-report.md)；本文件中的命令入口仍是后续复现参考，不自动授权重跑。

## 前提与保护

1. 每个实施阶段先读取 AGENTS、对应任务/报告，保存 git status/diff、未跟踪源码、原失败清单与源文件 hash；使用新证据目录，不覆盖本规划或 P1/P2 记录。
2. 使用已有 Python/Node/依赖，不安装或升级。backend cwd 运行 pytest，frontend cwd 运行消费单测/noEmit。
3. 应用导入前禁用 Settings 默认 dotenv，LLM_PROVIDER=fake、EMBEDDING_BACKEND=deterministic、SPARSE_OFFLINE_FALLBACK=true；DATA_DIR、QDRANT_DB_PATH 与 basetemp 全部指向该阶段隔离 output，禁止正式知识库路径。
4. 先从 P2 [D 的已验证 guard](../../output/governance011/engineering/phase-d-20261021/context011_d_guard.py)和[运行器](../../output/governance011/engineering/phase-d-20261021/context011_d_runner.py)准备本阶段版本，修改证据目录/插件名/环境标签，保存副本并自检。不得直接把 P3 结果写回 011 output。
5. guard 自检须阻止真实 Dense 加载和普通 socket.connect，只允许 Windows socketpair 内部唤醒；验证 dotenv 禁用，预期拒绝与产品测试 blocked_attempts 分开记录。不能只设置 fake 而漏掉旧测试的显式真实后端。

不要直接导入 app.main 作未隔离 smoke，也不通过重启服务/重建索引验证结构清理。

## A：主图与兼容装配

| 场景 | 需要证明 |
|---|---|
| 默认 fake 与 scripted ollama 图初始化/运行 | RuleBased/ModelQueryGenerator、EvidenceSelector 默认构造 0，rewrite 专用缓存分配 0；保留 analysis/request/retrieval cache，不把它们误算成旧缓存 |
| 显式注入 QueryGenerator / ModelQueryGenerator | 对象身份和原 ctor budget/request_cache 绑定保持；原 provider/cache/index_version 不替换，主图不调用 generate |
| 正常子图依赖 | 仍使用原有效 settings 选择、同一 budget/request_cache；正常路径不通过兼容 selector 取值，不重置请求期限 |
| 原 build_agent_subgraph 位置/关键字调用 | 原合法形状能运行 scripted 检索→回答，六个旧参数不新增语义；只一份图构造实现 |
| 兼容属性首次、重复、并发读取 | 主图不触发；显式首次读取只创建/发布一个对象，重复读取身份相同，必要缓存只创建一次 |
| 兼容属性赋值 | 赋值 None/自定义对象后原样返回，不重新创建，不自动重绑定或调用模型；setter 不影响当前图依赖 |
| provider 延迟初始化 | 兼容默认 ModelQueryGenerator 使用 ctor 捕获引用；图运行后初始化 generator.provider 不暗改该绑定 |
| 原图行为 | 单问、多分支、无证据、容量反馈、Parent 实读、批次/cache、部分交付、引用修复、预算和迟到历史保持 |

先保存旧默认构造边界的行为红测，再局部清理。构造计数 spy 必须保留类型关系，避免 mock 破坏 isinstance 变成假失败；不要只断言私有 builder 调用次数。测试新名字在 tasks 中确定，不把建议名字写成已存在。

## B：状态与独立兼容、最终回归

| 场景 | 需要证明 |
|---|---|
| procedure 正常图流转 | 不再固定写入/传递；TypedDict 可选兼容声明仍在，公开结果/诊断白名单不变 |
| Outcome/schema | requires_procedure 默认 False 和缓存命中属性保持；模型 schema 仍三字段，额外 requires_procedure 继续拒绝 |
| 生成两个 bool 的四种组合 | 原 provider 输入、答案、所选引文和逻辑次数相同；空证据零调用、非法引文有限修复/首次候选保持 |
| 独立 EvidenceSelector/procedure/query_planner | 直接调用、段落恢复、去重、候选与缓存等实质断言保持，不删除老能力或恢复为主图策略 |
| 旧 Parent 配置 | 不读取 `.env`，隔离验证字段/环境名/默认 240 和解析；换值不触发额外 Parent 请求，工具 offset/max_chars 与 P1 准入不变 |
| 组合/SSE/诊断 | 复用 P2 delivery 场景：入口→分支→修复→汇总→摘要、慢写/失败/冲突，单终态、历史与用量一致 |

## 命令入口（须先准备当轮 guard）

下列是复现命令示例，实际 argv/cwd/exit 以 [B 完整命令记录](../../output/cleanup012/engineering/phase-b-20261022/actual-commands.md)为准。已实施的 B 插件为 `context012_b_guard`，由保存的运行器安装到临时 PYTHONPATH，默认配置与真实 Dense/网络/正式数据均受保护；复现必须新建证据标签及目录，不覆盖当前 output。

```powershell
# cwd: C:/Users/ifhgz/Desktop/agentic-rag/backend
# 环境由当阶段运行器隔离并禁用 dotenv；不得跳过模型 guard。
python -m pytest -q tests/unit/test_graph.py tests/unit/test_model_agent_loop.py tests/unit/test_query_planner.py tests/unit/test_v3_4_evidence.py tests/unit/test_model_call_delivery.py tests/contract/test_model_call_delivery_stream.py -p no:cacheprovider -p context012_b_guard --basetemp=../output/cleanup012/engineering/phase-a/pytest-target-01
```

参数/兼容定向还应覆盖已有 test_v3_7_procedure_evidence、test_query_rewrite_v1、test_v4_query_schema、test_model_call_consumers、test_model_loop_budget、test_request_deadline、P1 四组准入及对应 contract；新增构造/旧调用/并发属性测试由 tasks 落实后加入命令。

B 完整后端固定排除两项真实嵌入相关测试，排除不算通过。除此之外，guard 在 setup 明确跳过 24 项依赖正式 PDF 的测试：`test_v4_calibrated_dataset.py::test_optional_facts_also_have_exact_pdf_provenance` 的 23 个参数实例，以及 `test_candidate_provenance_is_valid_but_not_formally_approved`。旧 `test_v3_6_q3_regression.py` 的可选 parents.json 本机核对被屏蔽，固定 fixture 断言仍运行。Python I/O 和 fitz 原生路径打开分别受保护，不通过正式 PDF 读取来获得绿灯：

```powershell
python -m pytest -q tests/unit tests/contract tests/integration tests/security -p no:cacheprovider -p context012_b_guard --basetemp=../output/cleanup012/engineering/phase-b/pytest-full-01 --deselect=tests/integration/test_v3_1_retrieval.py::test_four_baseline_questions_have_facts_in_top5_child_or_parent --deselect=tests/unit/test_embeddings.py::test_missing_real_model_does_not_silently_fall_back_to_hash
```

前端消费兼容与类型检查：

```powershell
# cwd: C:/Users/ifhgz/Desktop/agentic-rag/frontend
node node_modules/vitest/vitest.mjs run
node node_modules/typescript/bin/tsc --noEmit --incremental false
```

无前端源码/配置变更无需构建；如确需构建，保存独立产物、避免覆盖用户 buildinfo，不编造 lint 脚本。

## 对照与报告

- 比较 answer、sources、status、reason、调用/工具次数、缓存、history/pending 和诊断交付边界；不同请求 ID、模型调用 ID、耗时、时间戳及剩余时间只作关联，不能要求整份 JSON 或动态资源提示字节相等。
- 输入/证据 sentinel 不得进入公开日志/SSE，首次候选保留原私有范围。诊断经 status 或受控通知检查，产品不等待 saved。
- 构造审计与行为测试并用，条目逐项记录移除/保留/延期，不按文件名称或文本搜索整模块删。
- 原始红测、补测、完整命令/cwd/exit、guard、源码前后 hash 与原失败字节分别保存；无真实模型成绩。
- P2 D 的 797 passed / 2 failed / 2 deselected 是历史起点，不算本功能运行。两项旧提示词断言继续明示，CURRENT_FAILURES 真实失败不改判。
- A/B 报告分别保存本功能 phase-a-report.md / phase-b-report.md，给出实际结果及限制，并写“报告后暂停，等待用户验收”。不自动进入下一阶段、真实复验、GitHub 或提交/推送。


## 已运行事实与保留限制

- A 的 251 项定向通过是 A 历史成绩；B 新增 10 个展开用例，两份 P3 测试当前共 29 例。B 的 112 项定向回归及最终完整轮均含这些测试，不能把重叠轮次相加。
- B 正常 prepare/Send/agent 不再写入或转发 procedure 两字段；可选声明、Outcome、三字段 schema 和生成旧关键字仍在。原 Parent 配置值/解析保留但不控制正常图工具决策。
- B 的 10 组前后行为记录验证：两种配置的实际 scripted 问答、两种旧阈值、四类生成场景，以及单/三分支 procedure 传递。答案/来源/用量/历史投影一致，差异仅为预期无效字段消失。
- 完整轮仍有两项旧措辞断言失败；正式 PDF 的 24 项和真实嵌入的 2 项未运行。保护完善期间的中止、3-failure 首轮及 Windows 控制台编码错误均保留在 B output/报告，不替换为最终成绩。
- 测试与类型检查未修改前端 src、包/锁文件、tsconfig 或用户已有 tsbuildinfo；没有执行前端构建、安装依赖、模型或服务启动。
