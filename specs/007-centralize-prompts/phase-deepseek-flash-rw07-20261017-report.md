# DeepSeek Flash 4.1 指代补全真实测试报告

日期：2026-10-17（America/Los_Angeles）
范围：只验证 RW07“唯一对象后的它”入口问题分析，不执行其他题目。

## 结论

入口问题分析通过：在历史唯一对象为 `PN8733`、当前问题为“它的恢复条件是什么？”时，真实 `deepseek-flash` 调用返回 `is_clear=true`，`questions` 只有 1 项且包含 `PN8733`，没有澄清文字；结果来源为 `model`，未使用代码兜底。

这证明当前 DeepSeek Flash 4.1 能完成本题的最少必要对象补全。此次只测入口改写，没有继续检索、回答生成或引文核验，因此不代表完整端到端答案质量。

## 生效配置

- `LLM_PROVIDER=openai_compatible`
- `LLM_MODEL=deepseek-flash`
- `LLM_BASE_URL=https://api.deepseek.com/v1`
- API Key 已存在于本机配置中，未写入报告、命令输出或代码。

## 真实调用记录

- 历史上下文：`PN8733 有哪些保护功能？`
- 当前问题：`它的恢复条件是什么？`
- provider：`openai_compatible`
- model：`deepseek-flash`
- 入口调用耗时：2264 ms
- `is_clear`：`true`
- 改写问题数量：1
- 改写结果包含：`PN8733`
- `clarification`：空
- `source`：`model`
- `reference_fallback`：未使用

## UI 场景证据与限制

按完整 UI 场景先提交历史问题时，DeepSeek 首轮返回动作/答案格式无效，有限修正后失败，因此该轮没有写入会话历史。随后提交“它的恢复条件是什么？”时，系统正确提示没有此前对话上下文并要求澄清。该结果证明 UI 的前置历史失败被诚实处理，不能作为代词补全失败证据；有效的 RW07 结论以上述隔离入口调用为准。

## 实际验证

- 后端健康检查：HTTP 200，`index_ready=true`。
- 真实入口调用：1 次；未重试、未调用检索、未生成回答。
- 代码与提示词：本次没有修改。

报告后暂停，等待用户验收。
