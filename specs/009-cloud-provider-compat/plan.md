# Implementation Plan: 云兼容端点的结构化输出兼容

**Branch**: `009-cloud-provider-compat` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-cloud-provider-compat/spec.md`

**授权**：2026-10-15 用户选择“授权我做 provider 级修复（推荐）”，并要求按项目流程新建规格单独记录。本功能不重开 005/007/008 的既有结论，也不改变 008 展示层。

## Summary

让用户自备的云兼容端点真正可用。当前该路径整体不可用，有两个已复现的独立原因：

1. 环境中的 `brotli 1.0.9` 与 `openai 3.19.2` 依赖的 `httpx2 2.13.0` 不兼容：解码器调用 `process(..., output_buffer_limit=...)` 抛 `TypeError`，任何**压缩返回**都会中断调用（复现：`process(kwarg)` 失败、`process()` 成功）。
2. 端点的结构化输出能力差异：`OpenAICompatibleProvider` 对 `response_schema` 固定发送严格 JSON Schema 模式，而端点（实测 DeepSeek）返回 400 `This response_format type is unavailable now`；入口分析的结构约束**只**依赖该模式（schema 文本未进入 messages），因此必失败并被归为 `model_unavailable`。

方案：在 provider 层做两处最小改动——(a) 云端 HTTP 客户端显式不使用压缩编码，绕开损坏的解压绑定；(b) 严格结构化模式被端点拒绝时，改用通用 JSON 模式并只重试一次，同时把 schema 要求注入提示词，使同一结构校验继续生效，并记录实际模式与回退事实。本地与测试 provider 行为不变，预算/超时数值不变。

## Technical Context

**Language/Version**: Python 3.12.4（本机 `D:\newsoft\python.exe`，项目要求 3.11+）

**Primary Dependencies**: FastAPI、LangGraph、`openai` SDK（3.19.2，经 `httpx2` 2.13.0 传输）、pydantic、langchain-core。本功能**不新增依赖**。

**Storage**: N/A（不改索引格式、不改知识库 JSON、不迁移数据）

**Testing**: pytest（`backend/tests`）；前端不涉及，无需 Vitest/构建

**Target Platform**: Windows 本地开发环境；后端 127.0.0.1:8000

**Project Type**: web service（后端）+ SPA（前端，本功能不动）

**Performance Goals**: 不提高任何既有上限。回退后同一逻辑调用最多 2 次实际请求；整次请求仍受 300 秒绝对期限与单次模型等待 120 秒约束。

**Constraints**: 请求级预算（简单 8 / 总 12）不变；密钥、完整提示词与私有推理不得进入日志或对外事件；本地模型不可用时不得自动切云端，云端失败时不得自动回退程序规则。

**Scale/Scope**: 单管理员本地系统；改动集中在 `backend/app/rag/model_provider.py` 与调用方轨迹字段。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 判定 | 依据 |
|---|---|---|
| 一、阶段边界交付 | PASS | 本功能作为独立规格 009 承接，未把能力带入 005/007/008；008 仍以其自身报告为准 |
| 二、RAG 模块单一职责 | PASS | 改动只在提供商适配层与其轨迹字段；解析、分块、索引、检索、生成、核验职责不变 |
| 三、基于证据回答 | PASS | 不改变证据、引用定位与“证据不足要说明”的语义；回退只影响结构化约束的实现方式，不降低校验 |
| 四、安全且一致的数据处理 | PASS | 不触碰知识库、索引与密钥；仅调整 HTTP 传输与失败归类 |
| 五、可观察且可验证的行为 | PASS | 新增“实际结构化模式 / 是否回退”轨迹字段；新增针对性单元测试 |

设计后复核：无新增违例，无需 `Complexity Tracking` 条目。

## Project Structure

### Documentation (this feature)

```text
specs/009-cloud-provider-compat/
├── plan.md              # 本文件
├── spec.md              # 需求规格
├── research.md          # Phase 0 输出
├── data-model.md        # Phase 1 输出
├── quickstart.md        # Phase 1 输出
├── contracts/           # Phase 1 输出
│   └── cloud-provider.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 输出（$speckit-tasks 生成）
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── rag/
│       ├── model_provider.py      # 本功能主要改动：客户端构造 + 结构化回退 + 模式记录
│       ├── query_analysis.py      # 入口分析：记录实际模式与回退事实
│       ├── agent_loop.py          # 循环内模型调用：轨迹字段透传
│       └── generator.py           # 汇总/修正调用：轨迹字段透传
└── tests/
    └── unit/
        └── test_model_provider.py # 新增回退、单次重试、编码与失败分类断言
```

**Structure Decision**: 采用仓库既有布局。改动限制在 `backend/app/rag/` 的提供商与轨迹字段，测试放在既有 `backend/tests/unit/test_model_provider.py`。前端 `frontend/`、配置 `backend/.env*`、知识库与索引均不修改。

## 设计要点

1. **传输层兼容（FR-006）**：`OpenAICompatibleProvider` 构造云端客户端时显式声明不使用压缩编码，使远端返回不再经过损坏的解压路径。理由：缺陷位于第三方绑定，产品侧不应要求用户改环境；该设置对 JSON 接口的传输体积影响可忽略。
2. **结构化模式回退（FR-001~003）**：`response_schema` 存在时先按严格模式请求；仅当端点以“该 response_format 类型不可用”类错误拒绝时，注入 schema 文本后改用通用 JSON 模式重试一次。`complete_model` 仍用同一 schema 校验返回内容，校验强度不变。
3. **失败分类（FR-005）**：端点能力拒绝在两次尝试后仍失败时，归为提供商不可用，**不得**归为模型输出非法；模型返回内容不合法仍按既有 `invalid_model_output` 路径处理。
4. **可观测（FR-004）**：`ModelResult` 增加实际使用的结构化模式与是否回退字段，写入既有模型轨迹与执行事件 `details`，不新增对外顶层字段，不记录提示词正文。
5. **边界不变（FR-007/008/009/010）**：本地与测试 provider 代码路径不进入回退分支；不新增调用预算；不改变 300/120 秒与 8/12 上限；不改变脱敏规则与“不自动切云端/不用规则兜底”的既有约束。
