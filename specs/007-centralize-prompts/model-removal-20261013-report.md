# 007 旧模型资源清理记录

日期：2026-10-13。授权：用户“之前下载的那个模型可以删除了”。仅删除上一轮已替换的 `qwen3:4b-instruct`，资源清理完成；没有开展新的功能阶段或质量复测。

删除前核对已有.env仍配置 `granite4.1:8b`，安装清单同时有新旧模型，旧模型没有正在加载。通过已运行本机Ollama的官方SDK `Client(host="http://127.0.0.1:11434", trust_env=False).delete("qwen3:4b-instruct")` 调用DELETE /api/delete，返回success；事后安装清单仅保留granite4.1:8b。新模型digest保持 `444af1c4b2fedd6b54041aca558e7300b0b3d5c0468c44619126240323ba2852`。

## 实际操作与验证

| 命令或检查 | 工作目录 | 结果 |
|---|---|---|
| Ollama程序 `rm --help` | 仓库根目录 | 程序启动返回拒绝访问，未发起CLI删除；改用已运行的本机API，未提权 |
| `D:/newsoft/python.exe -B output/remove_old_ollama_model_007.py` | 仓库根目录 | 退出0；指定旧tag删除成功，新模型及其他安装项保持；删除和事后核对阶段1.828秒 |
| 本机安装清单/运行清单、当前非敏感配置核对 | 仓库根目录 | 真实API核对，无模型生成；卸载前旧模型大小2497293803字节，不将它当作实测磁盘释放量 |
| 文件与正式数据指纹核对 | 仓库根目录 | 删除前后4665项已有文件及17项正式数据保持；随后仅README和CURRENT_STATUS更新当前资源事实 |
| `D:/newsoft/python.exe -B output/verify_old_model_removal_007.py` | 仓库根目录 | 退出0；再次确认旧模型不在安装清单、新模型digest保持，配置/代码/历史报告/正式数据指纹保持，UTF-8与git diff --check通过 |

这是实际Ollama资源操作，没有fake/mock测试，也没有运行模型推理、工具、正式检索或自动化测试。没有删除模型目录、手动处理共享blob、覆盖.env、启动/重启服务或修改prompt/schema。失败证据和原始报告保留；上一轮结构化首测失败不因卸载旧模型而变为通过。

证据：[保护基线](../../output/prompt007/model-removal-20261013/baseline.json)、[卸载前安装清单](../../output/prompt007/model-removal-20261013/models-before.json)、[卸载前运行清单](../../output/prompt007/model-removal-20261013/running-before.json)、[删除答复](../../output/prompt007/model-removal-20261013/delete-response.json)、[卸载后清单](../../output/prompt007/model-removal-20261013/models-after.json)、[操作结果](../../output/prompt007/model-removal-20261013/removal.json)、[最终核对](../../output/prompt007/model-removal-20261013/verification.json)。

本轮为用户直接授权的资源清理，未新增/修改实施计划；007的24项已交付任务和旧质量待办状态不变，不修改历史模型配置报告中当时“保留旧模型”的事实。当前状态另记清理结果。没有自动下一阶段。

**报告后暂停，等待用户验收。**
