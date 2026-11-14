# 007 模型配置补充M报告

日期：2026-10-13。授权：用户要求“这个模型选择和GitHub项目的一样，改成一样的，现在这个4B的不好”。范围为同款本地聊天模型的配置、首次下载准备和必要检查，T025–T028；原A/B报告、C取消及旧E/F失败不改变。

**结论：模型切换完成；工程检查通过；两次真实合成协议探测1通过、1失败，协议验收未全部通过。等待用户验收。**

## 具体交付

- 上游[实际project/config.py](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/config.py)当前使用 `granite4.1:8b`、temperature=0、seed=42。本机已下载同一tag，实际Settings和OllamaProvider均使用该模型。
- 安装大小5347933017字节（约5.35GB），本机标识8.8B、GGUF/Q4_K_M，capabilities为completion/tools；安装digest为 `444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852`。下载1010.531秒，Ollama完成sha256校验并写入manifest。
- `backend/.env`只改变OLLAMA_MODEL一行，`backend/.env.example`对应行同步；两者其他行逐字节保持，敏感配置不保存正文。README更新当前模型与拉取命令，当前状态和007规格/计划/研究/数据边界/契约/任务同步补充M。
- prompt.py、QueryAnalysis、provider、配置代码、其他生产代码及所有旧报告保持字节一致。温度0、种子42原已一致，模型窗口4096、输入3072、输出768、安全256，单次120秒/整请求300秒、8/12模型与16工具预算保持。
- 新模型加载成功，Ollama运行清单含granite4.1:8b，context_length=4096、size_vram=0，当前使用CPU推理。旧qwen3:4b-instruct安装保留。

## 实际命令与退出状态

以下外层命令均在仓库根目录运行；pytest子进程工作目录为backend，其完整参数、退出码和耗时另存command JSON。Spec Kit未创建或切换分支，实际git分支继续codex/model-driven-agent-loop；setup-plan的BRANCH输出来自功能名解析，不代表实际Git分支。

| 命令 | 退出与结果 |
|---|---|
| `.specify/scripts/powershell/setup-plan.ps1 -Json` | 0，定位007并保留已有plan，不复制覆盖 |
| `.specify/scripts/powershell/setup-tasks.ps1 -Json` | 0，取得当前目录和模板，保留旧完成任务，追加US5四项 |
| `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | 0，定位007；requirements只读门禁16/16，未修改 |
| `D:/newsoft/python.exe -B output/model_alignment_007.py prepare` | 首次1：旧知识指纹路径基准错误，发生在修改前；修正为backend/data后第二次0，保存4631项文件和17项正式数据保护指纹 |
| `D:/newsoft/python.exe -B output/model_alignment_007.py pull` | 0，本机流式pull成功并校验安装，1010.531秒 |
| `D:/newsoft/python.exe -B output/check_model_alignment_007.py engineering` | 0，88 passed，pytest80.27秒，外层90.047秒；下载期间运行，与下载/模型推理独立 |
| `D:/newsoft/python.exe -B output/model_alignment_007.py switch` | 0，安装完成后仅修改实际配置和示例的模型行 |
| `D:/newsoft/python.exe -B output/check_model_alignment_007.py configuration` | 0，新进程Settings/提供方模型及安装一致，其他.env行指纹保持 |
| `D:/newsoft/python.exe -B output/check_model_alignment_007.py structured` | 1，首次真实schema探测失败，模型等待48.766秒、外层55.468秒；首次输出保留，没有重试 |
| `D:/newsoft/python.exe -B output/check_model_alignment_007.py tools` | 0，独立原生工具探测通过，模型等待10.328秒、外层17.734秒 |
| `D:/newsoft/python.exe -B output/model_alignment_007.py runtime` | 0，新模型已实际加载；8000健康检查前后均ConnectError，未启动或重启服务 |
| `D:/newsoft/python.exe -B output/audit_model_alignment_007.py` | 0，保护指纹、其他配置行、分支、UTF-8/链接及git diff --check通过；结果见audit.json |

工程子命令：`D:/newsoft/python.exe -B -m pytest -q tests/unit/test_model_provider.py tests/unit/test_query_analysis_structured_output.py tests/unit/test_query_rewrite_v1.py tests/unit/test_model_call_deadline.py --basetemp=C:/path/agentic-rag/output/prompt007/model-alignment-20261013/pytest -o cache_dir=C:/path/agentic-rag/output/prompt007/model-alignment-20261013/cache`。没有新增镜像实现的测试、升级依赖、跑前端或全量后端回归。

Spec Kit plan/tasks/implement前后扩展配置文件均不存在，hooks依规则跳过。CIM进程/内存只读查询曾拒绝访问；使用普通进程清单和本机API核对所需状态，没有提权、结束任何进程或扩大权限。

## 真实合成探测与失败原因

使用实际项目create_provider/complete_model和当前Settings，无正式知识库、检索、平台认证或评测题集。两次真实模型调用，工具实际执行0、工具调用请求1个、云端推理0、Judge0、重试0；输入971、输出71，共1042 Token，来自提供方usage。两次模型等待合计59.094秒。这是直接提供方探测，没有平台请求ID，不等于端到端RAG质量验收。

| 探测 | 原始首次结果 | 验收 |
|---|---|---|
| 真实QueryAnalysis绑定 | 合成原题“设备PX-DEMO的额定工作电压是多少？”保留；返回is_clear=true、questions为原题、clarification_needed="无" | 失败：现有清楚状态要求clarification_needed为空字符串；Pydantic联动校验拒绝，structured_output=None |
| 原生工具接口 | 模型返回configuration_ping，参数key=model-switch，只有一个原生工具请求；没有执行该合成工具 | 通过：现有Ollama/ChatOllama工具接口可返回标准调用 |

结构化失败不是JSON语法、字段缺失或型号改错；三个字段及类型均已生成，但字段之间的业务状态不一致。生成schema不能自动表达本项目所有自定义validator，现有联动校验没有放宽。本轮只换模型，没有把“无”自动变成空字符串、改prompt/schema或进行第二次尝试。不能据此宣称8B已解决入口或历史七项E失败。

## 证据、限制与停止点

保护基线为4631项已有文件、17项正式数据；本轮只允许实际配置、示例、当前导航及007设计补充变更。模型资源通过已有本机Ollama下载，首次准备有外部网络访问。没有写正式知识库/索引、改变embedding、题集、采集器、旧首答或CURRENT_FAILURES，亦未提交/推送。

证据：[基线](../../output/prompt007/model-alignment-20261013/baseline.json)、[准备首次失败](../../output/prompt007/model-alignment-20261013/prepare-first-failure.json)、[下载原始流](../../output/prompt007/model-alignment-20261013/pull.ndjson)、[安装结果](../../output/prompt007/model-alignment-20261013/pull-result.json)、[安装元数据](../../output/prompt007/model-alignment-20261013/model-metadata.json)、[定点修改](../../output/prompt007/model-alignment-20261013/configuration-edit.json)、[生效配置](../../output/prompt007/model-alignment-20261013/configuration.json)、[工程记录](../../output/prompt007/model-alignment-20261013/engineering.log)、[结构化首次失败](../../output/prompt007/model-alignment-20261013/probe-structured.json)、[原生工具首次结果](../../output/prompt007/model-alignment-20261013/probe-tools.json)、[实际加载](../../output/prompt007/model-alignment-20261013/runtime-models.json)、[服务状态](../../output/prompt007/model-alignment-20261013/health-after.json)、[最终核对](../../output/prompt007/model-alignment-20261013/audit.json)。

后端8000当前不可连接，本轮没有启动或重启；新进程读取和真实提供方已验证，下次正常启动加载新模型。旧模型仍安装，程序按新配置选Granite，未增加回退。

T025–T028工作交付完成，原20项提示任务保持；SC-008真实协议验收未全部通过。006 E仍10通过/7失败，代词补全和F失败、005两题真实失败不勾选。没有恢复已取消的C、E/F或正式30题。后续若修复结构化语义、复测历史题或启动平台，按用户另行明确范围执行。

**报告后暂停，等待用户验收。**
