# 阶段 D 报告：离线评估工具与诚实在线核验

真实运行原文已移出公开仓库；历史统计与通过/失败结论保留。
> 后续运行（2026-10-07）：题集已获用户批准，首批 15 题/19 轮真实输出已保存；达到 80 次 Judge 上限后结束，22 项评分、13 项超时、15 项预算不足、Q9 的 5 项链路失败及 20 项不适用如实保留。逐题分数、必答点冲突、成本与失败见[首批报告](formal-ragas-report.md)及[观察记录](formal-ragas-observation.json)。T026 的完整评分与人工签收未完成，已暂停。下文保留工具首次交付时的历史结论。

**日期**：2026-10-02。**范围**：任务阶段 6（T022～T026）；只推进本阶段并在报告后暂停。阶段 7 未开始。

## 结论与未完成事项

在线固定百分比评分已移除，改为四项核验状态。离线工具已接入 RAGAS 五项指标并跑通一题合成来源；它没有进入在线请求，也没有修改正式知识库。后端全量 252 项、前端 19 项测试与前端构建通过。

**阶段 D 尚未完成正式验收**：15 题仍为草案，T020 人工审核未通过；本轮没有采集或评估正式 15 题，没有人工必答点或 Judge/人工冲突结论。T026 保持未勾选，不能用合成冒烟代替它。本阶段也没有修复旧 V3 计划中的 Q3 答案生成遗漏。

用户本次说“继续下一个阶段”，授权实现先行；没有将该指令视为对题集逐条确认。题集没有写入 reviewer、reviewed_at 或 review_kind。

## 1. Spec Kit 前置检查

| 清单 | 总项数 | 已检查 | 未检查 | 状态 |
|---|---:|---:|---:|---|
| `checklists/requirements.md` | 16 | 16 | 0 | 通过 |

需求清单只表示规格质量，不是实现进度或题集人工审批。按 `speckit-implement` 核对当前功能的规格、计划、任务、契约、数据模型和宪章；现有 Git 工作区有前阶段未提交改动，全部保留。本阶段使用中文文档技能确保 UTF-8 重读；前端技能用于沿用原有深色工作台，以明确的文字徽标替换分数条，不做整页改版。

实施前后均未发现 `.specify/extensions.yml`，因此没有扩展钩子需执行。`.gitignore` 已覆盖临时虚拟环境、运行 JSON、正式数据和 `.env`，没有提交或推送操作。

## 2. 在线核验：不再给固定“可信度”

服务端发出 `verification`，版本为 2；旧 `evaluation` 数值事件停止发送。前端同时切换为状态卡，并忽略旧评分、未知版本、非法枚举或携带旧分数字段的混合载荷。

| 项目 | 当前实际能力 | 不代表什么 |
|---|---|---|
| 检索证据 | 有本次上下文则显示已取得证据；不足则显示证据不足 | 不证明召回了所有必答事实 |
| 引文定位 | 检查证据编号；实际中文引文格式还检查原文片段、文件、页码和章节 | 不证明回答含义或安全步骤正确 |
| 数值条件 | 暂不做可靠语义核验，显示未评估；无证据时不适用 | 不虚构数值正确率 |
| 步骤完整性 | 暂不做可靠语义核验，始终未评估 | 漏安全步骤不会被标为完整可信 |

未知引用编号或引文/页码不匹配会显示存在问题。没有充分原文记录时保持未评估。在线检查只读本次检索记录，不直接重解析 PDF，不调用 Judge。澄清/取消没有核验卡，新请求清除旧卡；普通 `answer/retrieval/usage/error/complete` 保留。内部节点名 `answer_evaluation` 和结果字段 `evaluation` 暂保留兼容，但内容已不是分数。

专项覆盖了漏掉“断开负载、等待完全放电”的答案：完整性明确为 `not_evaluated`，无 `overall`。这只是移除了错误的可信宣称，不是宣称模型现在会自动识别所有漏步骤。

## 3. 离线工具与参考项目对齐

参考[原项目评估 Notebook](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/notebooks/evaluation.ipynb)，使用 RAGAS 0.4.3 的五项 collections 指标。没有照搬 Notebook 的 VertexAI 假模块补丁；使用真实兼容的 LangChain 包路径。指标含义还核对了 [RAGAS NVIDIA 指标文档](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/nvidia_metrics/)和[检索精度](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/context_precision/)、[检索召回](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/context_recall/)文档。

交付 `backend/scripts/evaluate_v4_ragas.py` 与 `backend/requirements-eval.txt`，后者固定干净环境的全部 101 个包版本。评估依赖与生产环境分离，不向生产 requirements 追加旧版 LangChain，也不用评估环境启动后端。

| 指标 | 问题/回答来源 | 证据层级 |
|---|---|---|
| AnswerAccuracy | 实际独立问题、实际回答、已核对标准答案 | 不使用来源引文伪装系统回答 |
| ContextRelevance | 实际独立问题 | Child 工具每次返回的查询及候选原始排序 |
| ResponseGroundedness | 实际回答 | 实际送入生成器的证据记录 |
| ContextPrecision | 实际问题、标准答案 | Child 工具原始排序 |
| ContextRecall | 实际问题、标准答案 | Child 工具原始排序 |

`GraphRunResult.retrieval_batches` 新增只读审计记录，保留每个查询/分支与工具返回排序；不改变检索逻辑。`capture_graph_result()` 导出真实输出、候选、生成记录、来源、模型追踪和系统问答成本；摘要单独登记，不填入原文证据。本阶段没有自动全量问答采集 CLI，正式采集仍须在准入后真实运行对应会话与交互。

正式模式先核对整份题集人工状态，再检查 PDF/索引清单哈希、源文档聚合指纹、模型、题目、历史和两层上下文的一致性；不静默筛掉失配题。只读清单和 PDF，不初始化、迁移或重建向量库；这不等价于对完整向量数据库做一致性扫描。

无答案/交互题的五项指标暂为 `not_applicable`，另待人工或交互回归；超时、无效分数、无穷值、调用失败为 `evaluation_error/value=null`，不补 0。字面必答点探针只提示可能遗漏，显式 `is_semantic_verdict=false`，不是语义判断、顺序检查或人工审批。

## 4. 模型与成本闸门

只使用已有 `qwen3:4b-instruct`，没有下载第二模型或调用云端。回答与 Judge 同模型，因此结果为探索性，不是独立裁判或正式准确率。

SDK 显式连本机回环地址，关闭环境代理和重定向；禁用 RAGAS 遥测及 LangSmith 追踪。模型须在 `/api/tags` 已存在，禁止自动拉取或退回云端。默认总 HTTP 模型调用上限 16、每项超时 60 秒；SDK 不自动重试，Instructor 与评级尝试上限为 1。整批评估预算必须预先设定，默认 16 不是每题额度。

逐项记录服务返回的 prompt/completion Token、调用次数、耗时、HTTP 状态以及 usage 缺失次数；未知成本不当作 0。人工审核默认 pending；`formal_acceptance` 不会由高分自动置真。指标理由/轨迹若库未提供则保持 null。

## 5. 本轮实测

### 5.1 自动化与闸门

- 后端全量：`python -m pytest -q` → 252 passed，61.03 秒；不是正式库模型答题。
- 本阶段专项：离线运行器、Graph 审计与核验事件共 45 passed；无云端调用。
- 前端：19 passed；`npm run build` 通过。
- 草案正式命令：`python -m scripts.evaluate_v4_ragas` → 退出码 1、`review_required`；未导入 Judge、未调用模型。
- 干净评估环境：独立安装成功，`pip check` → `No broken requirements found.`。

先写失败测试，再迁移实现。测试补充发现 PDF 更新未被旧快照拒绝，修复后失配样例通过。首轮合成冒烟因本机 `/api/tags` 端点的来源校验错误而在模型调用前失败；修复后运行如下真实结果，失败记录保留，未改成成功。

### 5.2 第一次合成来源模型冒烟

问题：`测试记录默认保留多久？`；合成来源：`测试记录默认保留三年。`。模型实际回答：`三年。`。此样例未读取正式题集、PDF 或向量库，也未走应用的入口分析/检索链路。

| 指标 | 库返回原始值 | Judge 调用 | 实测 Token | 指标耗时 |
|---|---:|---:|---:|---:|
| AnswerAccuracy | 1.0 | 2 | 1,390 | 22.192 秒 |
| ContextRelevance | 1.0 | 2 | 1,244 | 18.355 秒 |
| ResponseGroundedness | 1.0 | 2 | 1,245 | 18.043 秒 |
| ContextPrecision | 0.9999999999 | 1 | 1,166 | 22.633 秒 |
| ContextRecall | 1.0 | 1 | 1,700 | 33.161 秒 |

Judge 合计 **8 次、6,745 Token**；合成回答 **1 次、45 Token、9.988 秒**；全程 **190.377 秒**（含依赖冷启动）。unknown_usage_calls 为 0，云端调用为 0。

三个指标各使用两种 Judge 提示，不代表运行两个不同模型；五项指标不等于五次 API 请求。该简单合成题高分只说明适配与调用成功，不能推广为真实问答准确率。

原始报告：`backend/tmp/v4-evaluations/eval-[运行标识已移除].json`。其中含实际回答、两层合成上下文、分项、usage、模型 digest 和依赖版本。首次环境继承系统包，只作兼容性调试；最终交付使用无系统包继承的 `backend/tmp/v4-eval-clean-env`。

### 5.3 干净环境重跑

同一模型、同一合成问题和来源再次成功，实际回答仍为“三年。”；五项原始分数与第一次相同，全部为 scored，无指标错误。回答耗时 6.558 秒，整轮 130.794 秒；Judge 仍为 8 次、6,745 Token，回答仍为 1 次、45 Token，unknown_usage_calls=0、cloud_calls=0。只证明此固定样例可重跑，不承诺其他问题无波动。

原始报告：`backend/tmp/v4-evaluations/eval-[运行标识已移除].json`。五项耗时依次为 21.563、17.871、18.003、23.081、32.976 秒。报告显式记录总 HTTP 调用预算 16、每项超时 60 秒、Instructor/评级尝试上限 1；此前调试实例的评级上限是库默认值，本轮重跑使用最终有界配置，未触发重试。

两次成功冒烟累计 **18 次本地模型调用、13,580 Token**，其中 Judge 16 次/13,490 Token；未执行额外正式题目。本机 Ollama 报告模型使用 CPU（size_vram=0），本轮耗时不能与 V3-5 五题应用成本直接比较，亦不是正式性能达标结论。

完整依赖锁定后，`pip install --dry-run --no-index -r requirements-eval.txt` 检查全部 101 项已满足、退出码 0。中文注释文件已增加 UTF-8 编码标记，修复 Windows 旧 pip 按 GBK 读取时的报错。最终源代码额外关闭 LangSmith 追踪；该防护不改变已验证的五项指标或回答。

## 6. 数据保护与剩余工作

本轮前后 SHA-256 一致：正式 PDF、`documents.json`、`index/children.json`、`index/manifest.json`、实际 `.env`、`gold-cases-v1.json`。正式题集仍是 candidate-1.0、15 个 draft，未补填审核记录。生产 Python 的 OpenAI 3.19.2、LangChain Core 1.6.4、LangChain Ollama 1.1.0 均未变。前端构建正常更新了生成文件 `tsconfig.tsbuildinfo`。

T022～T025 已完成；T026 保留未完成。下一步须先由维护者复核[题集审核稿](gold-cases-review.md)，登记真实审核记录后才采集正式输出、运行整批指标、逐项核对 Q3 安全步骤和交互/无答案场景。正式验收前不进入阶段 7，也不把旧 Q3 生成问题写成已修复。

本轮没有浏览器人工视觉验收或工作台真实题目验收；前端证据来自 DOM/SSE 自动化与构建。启用在线新核验逻辑需使用原运行环境重新启动后端并刷新前端，不改登录配置。
