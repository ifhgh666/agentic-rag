# 问题改写与独立结构定义：供用户检查

2026-10-20 A3收敛后，[实际 prompts.py](../../backend/app/rag/prompts.py)是所有生产提示与模型消息模板的唯一实现；输出结构位于[独立 schemas.py](../../backend/app/rag/schemas.py)。QueryAnalyzer直接使用这两个模块。提示版本为 `rewrite-prompt-v6-zh`，协议仍为 `query-rewrite-v1`；当前没有第二个RAG包或旧prompt/schema转发文件。工程结果为117项定向测试通过；完整后端回归588通过、3失败（两项历史v4措辞断言，一项全量运行时序断言单独复跑通过）。详见[A3报告](phase-single-rag-package-20261018-report.md)，报告后暂停，等待用户验收。

## 实际改写函数全文

```python
def get_rewrite_query_prompt() -> str:
    """Return the constrained query prompt for user review."""
    return """## 角色
你是 RAG 系统中负责文档检索的问题改写专家。

## 指令
- 将当前问题改写为清晰、自包含且适合检索的问题。
- 只使用对话摘要和最近对话来解决指向此前上下文的模糊追问。
- 当存在未解决的问题以及一个或多个用户补充时，将它们合并为一个自包含的检索问题。
- 如果当前问题是追问，只补足使其自包含所需的最少上下文。
- 完整保留产品名、文件名、版本、缩写、数字和技术术语。
- 如果用户询问的是明确命名的主题、产品、文件、缩写、术语或概念，即使之前没有提到，也将问题视为清楚。
- 单独出现的命名术语、缩写或概念也可以作为有效的检索问题；不要求它们必须有此前的对话上下文。
- 只拆分真正独立的信息需求，最多改写为三个问题。

## 澄清边界
- 仅当问题依赖未解决的指代，例如“它”“那个”“这个文件”或“前一个”时，才将问题标记为不清楚。
- 不要因为某个主题之前没有出现过，就将问题标记为不清楚。
- 不要询问新的缩写或术语是否是拼写错误；保留原文并检索它。

## 约束
不要添加事实、展开缩写、臆造上下文或扩大用户原意。
""".strip()
```

## 实际入口schema全文

```python
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _query_clarity_schema(schema: dict) -> None:
    """Express the runtime state invariant in the schema used for generation."""
    clear, unclear = deepcopy(schema), deepcopy(schema)
    clear["properties"]["is_clear"]["const"] = True
    clear["properties"]["questions"]["minItems"] = 1
    clear["properties"]["clarification_needed"]["const"] = ""
    unclear["properties"]["is_clear"]["const"] = False
    unclear["properties"]["questions"]["maxItems"] = 0
    unclear["properties"]["clarification_needed"]["minLength"] = 1
    # Each alternative is a complete object contract. Grammar compilers may
    # process anyOf before sibling properties; partial alternatives would lose
    # the required fields, types and additionalProperties restriction.
    schema["anyOf"] = [clear, unclear]


class QueryAnalysis(BaseModel):
    """Strict model-only entrance contract; runtime action metadata is separate."""

    model_config = ConfigDict(extra="forbid", strict=True, json_schema_extra=_query_clarity_schema)

    is_clear: bool = Field(description=(
        "问题是否能按提供的上下文独立检索，不代表已知道答案。"
        "仅未解决的指代或无法在三问内保留的独立需求需要澄清。"
    ))
    questions: list[str] = Field(max_length=3, description=(
        "清楚时为1至3个非空、不重复、可独立检索的问题；完整单问保留原句。"
        "不清楚时为空数组，不包含答案或未确认事实。"
    ))
    clarification_needed: str = Field(description=(
        "清楚时为空字符串；不清楚时写具体的指代或最多三项需求选择问题。"
        "不得向用户索要需要从资料检索的答案。"
    ))

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, questions: list[str]) -> list[str]:
        cleaned = [question.strip() for question in questions]
        if any(not question or len(question) > 2000 for question in cleaned):
            raise ValueError("questions must contain 1–2000 characters")
        # Normalize only a comparison copy, never the text sent to retrieval.
        keys = [" ".join(question.split()).casefold() for question in cleaned]
        if len(set(keys)) != len(keys):
            raise ValueError("questions must be distinct")
        return cleaned

    @field_validator("clarification_needed")
    @classmethod
    def strip_clarification(cls, clarification: str) -> str:
        return clarification.strip()

    @model_validator(mode="after")
    def check_clarity(self) -> "QueryAnalysis":
        if self.is_clear:
            if not self.questions or self.clarification_needed:
                raise ValueError("clear output requires questions and empty clarification")
        elif self.questions or not self.clarification_needed:
            raise ValueError("unclear output requires empty questions and a clarification")
        return self
```

## 实际调用与检查重点

QueryAnalyzer使用get_rewrite_query_prompt()及response_schema=QueryAnalysis；[OllamaProvider](../../backend/app/rag/model_provider.py)直接with_structured_output(response_schema, method="json_schema", include_raw=True)。schema经format随请求发送，不把schema文本追加到system/user消息；ModelResult保留raw/usage并提供结构化对象，入口按三个字段读取。

模型返回不清楚后，QueryAnalyzer还会对唯一历史型号和明确中文代词执行受限兜底；该逻辑只补对象名称，不补答案或未确认事实，多对象继续澄清，版本 `unique-reference-fallback-v1` 进入缓存键。真实 RW07 复测已通过，见[兜底报告](phase-reference-fallback-20261015-report.md)。

字段类型/必填/额外字段/最多三项由schema定义，字段联动及非空/重复等现有validator保持；不新增数字/空格语义校验。当前中文 v6 prompt 提供角色、改写、必要上下文、澄清边界、独立拆分和保真规则，不描述JSON格式；D13/D14/D15真实复测仍发现共享条件、比较目标和容量澄清未通过，见[中文prompt复测报告](phase-chinese-prompt-20261014-report.md)。

原A补充20项专门检查和554项回归报告保留。B新增12项实际消费点绑定检查、15项非入口等价场景及566项完整后端工程回归通过，均为fake/scripted与假传输。中文 prompt 三题真实入口复测为0通过、3失败，未进入检索或回答链；完整17题仍未因本次改动重跑。见[最新B报告](phase-b-report.md)、[中文prompt复测报告](phase-chinese-prompt-20261014-report.md)，原[A报告](phase-a-report.md)及[结构化补充](phase-a-structured-output-report.md)不覆盖。报告后暂停，等待用户验收；工程计划结束，C取消。

## 9个固定提示函数实际消费位置

全部固定提示与动态模型消息格式见[完整 prompts.py](../../backend/app/rag/prompts.py)。动态题目、上下文、证据和预算作为参数传入纯函数；schema字段说明和工具description继续由各自职责模块维护。证据侧只使用[context_compression.py](../../backend/app/rag/context_compression.py)的 Token 估算与动态阈值，不依赖压缩提示或模型输出。

| 函数 | 参数 | 已接入消费者 |
|---|---|---|
| [get_rewrite_query_prompt](../../backend/app/rag/prompts.py) | 无 | query_analysis.py |
| [get_conversation_summary_prompt](../../backend/app/rag/prompts.py) | max_chars | conversation_summary.py |
| [get_orchestrator_prompt](../../backend/app/rag/prompts.py) | protocol | agent_loop.py |
| [get_aggregation_prompt](../../backend/app/rag/prompts.py) | 无 | generator.py |
| [get_answer_generation_prompt](../../backend/app/rag/prompts.py) | 无 | generator.py |
| [get_retrieval_rewrite_prompt](../../backend/app/rag/prompts.py) | 无 | query_planner.py |
| [get_answer_repair_prompt](../../backend/app/rag/prompts.py) | feedback | generator.py |
| [get_loop_repair_prompt](../../backend/app/rag/prompts.py) | feedback | agent_loop.py |
| [get_aggregation_instruction](../../backend/app/rag/prompts.py) | 无 | generator.py |

预算提示、schema回退提示以及入口/分支/证据/汇总等动态消息模板也集中在同一文件，通过参数化纯函数调用；业务模块只负责准备结构化数据和消息角色。


## 2026-10-13 字段联动生成约束修复

以上schema全文已同步实际回调。清楚/待澄清联动由完整anyOf分支直接进入Ollama.format，不把格式文字补回prompt，也不清空首答的‘无／否’。后置校验保留；既有schema哈希自动隔离旧缓存。见[修复报告](phase-schema-fix-20261013-report.md)。


## 2026-10-14 业务顺序与通用示例候选P未通过

v4候选在共享条件/比较原题及变体上通过，但容量仍失败，17题回归新增完整问误澄清和历史混入，总成绩12/17低于v3的14/17。因此只撤回本轮prompt候选，当前函数全文/定义行号恢复实际v3；schema修复及其他10函数保持。候选全文保存在[prompt-candidate-v4.py](../../output/prompt007/business-repair-20261014/prompt-candidate-v4.py)，原始首答与两轮工程记录均保留，见[修复报告](phase-business-prompt-20261014-report.md)。
