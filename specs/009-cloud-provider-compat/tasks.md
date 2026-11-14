# Tasks: 云兼容端点的结构化输出兼容

**Input**: Design documents from `/specs/009-cloud-provider-compat/`

**Prerequisites**: plan.md、spec.md、research.md、data-model.md、contracts/cloud-provider.md、quickstart.md

**Tests**: 本项目宪章原则五要求“新增行为必须包含针对性测试”，故本清单包含测试任务。

**Organization**: 按用户故事分组，每个故事可独立实现与验证。

**授权与边界**: 2026-10-15 用户授权“provider 级修复”。本清单不修改前端、配置示例、知识库与索引，不新增依赖，不提高 300/120 秒与 8/12 预算上限。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完依赖）
- **[Story]**: 所属用户故事（US1/US2/US3）
- 描述中给出确切文件路径

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 固定改动前基线与环境事实，避免事后无法区分“本来如此”与“被本次改动影响”。

- [X] T001 记录改前基线：在 `backend` 运行 `python -m pytest -q tests/unit/test_model_provider.py` 与受影响调用方测试（`tests/unit/test_v3_3_query_analysis.py`、`tests/unit/test_v4_query_analysis.py`、`tests/unit/test_model_agent_loop.py`），把退出码与摘要写入 `output/cloud009-baseline/` 下的文本文件。
- [X] T002 [P] 记录环境事实：`openai`、`httpx2`、`brotli` 版本与“端点拒绝严格结构化模式”的真实响应，写入 `specs/009-cloud-provider-compat/phase-a-report.md` 的证据小节（不写入密钥）。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 先落契约字段与失败用例，使回退实现有可判定的目标。

**⚠️ CRITICAL**: 本阶段完成前不得开始用户故事实现。

- [X] T003 [P] 在 `backend/tests/unit/test_model_provider.py` 增加失败用例：云端客户端构造时不使用压缩编码、严格模式被端点拒绝后回退为通用 JSON 模式、同一逻辑调用最多 2 次请求、严格模式未被拒绝时不得回退；先运行并记录这些用例失败。
- [X] T004 在 `backend/app/rag/model_provider.py` 的 `ModelResult` 上增加 `structured_mode`（取值 `json_schema` / `json_object` / `none`，默认 `none`）与 `structured_fallback`（布尔，默认 `false`）字段，保持既有构造调用兼容。

**Checkpoint**: 契约字段与失败用例就位。

---

## Phase 3: User Story 1 - 使用自配云兼容端点完成一次问答 (Priority: P1) 🎯 MVP

**Goal**: 云兼容端点不再整体不可用，且严格结构化模式被拒时能自动回退并完成调用。

**Independent Test**: 配置云兼容端点后提交一个知识库内有依据的问题，得到非空回答与来源，且过程不出现“模型不可用”。

### Implementation for User Story 1

- [X] T005 [US1] 在 `backend/app/rag/model_provider.py` 的 `OpenAICompatibleProvider.__init__` 构造客户端时显式不使用压缩编码（契约 §3）。
- [X] T006 [US1] 在 `backend/app/rag/model_provider.py` 的 `OpenAICompatibleProvider.complete` 中实现：严格模式被端点以“该 response_format 类型不可用”类错误拒绝时，注入 schema 文本并改用通用 JSON 模式重试一次；端点拒绝以外的异常不得触发回退（契约 §2）。
- [X] T007 [US1] 在 `OpenAICompatibleProvider.complete` 回填 `ModelResult.structured_mode` 与 `structured_fallback`，并在 `backend/app/rag/query_analysis.py` 与 `backend/app/rag/agent_loop.py` 的模型轨迹中包含这两个键。
- [X] T008 [US1] 运行 `python -m pytest -q tests/unit/test_model_provider.py`，确认 T003 的 US1 用例通过。

**Checkpoint**: User Story 1 可独立验证。

---

## Phase 4: User Story 2 - 失败原因可区分 (Priority: P1)

**Goal**: 端点能力不足、模型输出非法、超时、传输失败在请求记录中彼此可区分。

**Independent Test**: 分别构造端点拒绝与非法输出两类情形，检查记录中的失败原因不同且指向真实原因。

### Implementation for User Story 2

- [X] T009 [US2] 在 `backend/app/rag/model_provider.py` 中固定归类：严格与通用模式均被端点拒绝时，抛出可被调用方识别为“提供商不可用”的错误；模型内容不合法仍由 `complete_model` 的既有校验处理，不得归为提供商不可用（契约 §5）。
- [X] T010 [US2] 在 `backend/tests/unit/test_model_provider.py` 增加失败分类断言：端点拒绝 ≠ 输出非法；输出非法 ≠ 端点不可用；两次均被拒时不应出现“输出非法”。
- [X] T011 [US2] 在 `backend/app/rag/pipeline.py` 的模型调用事件 `details` 中加入 `structured_mode` 与 `structured_fallback`（仅 `details`，不新增顶层事件字段，契约 §4）。

**Checkpoint**: User Story 2 可独立验证。

---

## Phase 5: User Story 3 - 本地路径行为不变 (Priority: P2)

**Goal**: 本地模型与显式测试模型的既有行为、事件与失败原因保持不变。

**Independent Test**: 运行既有本地与假模型测试，结论与 T001 基线一致。

### Implementation for User Story 3

- [X] T012 [US3] 在 `backend/tests/unit/test_model_provider.py` 增加断言：`OllamaProvider` 与 `FakeProvider` 的调用不设置 `structured_mode` 回退、`structured_fallback` 恒为 `false`。
- [X] T013 [US3] 运行 `python -m pytest -q tests/unit tests/contract tests/integration tests/security`（工作目录 `backend`），与 T001 基线比较，确认无新增失败。

**Checkpoint**: 全部用户故事可独立验证。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 真实端点验证与交付记录。

- [X] T014 [P] 按 `specs/009-cloud-provider-compat/quickstart.md` 执行真实端点验证：在 `backend` 启动后端，提交 `PX-200 的过流保护阈值是多少？`，采集请求标识、事件序列、耗时、用量与 `structured_mode`，原始记录写入 `output/cloud009-real-20261015/`。
- [X] T015 [P] 核对不变量：本次运行云端调用次数与记录一致、未突破 300 秒与 120 秒上限、日志与事件未出现密钥或提示词正文。
- [X] T016 交付 `specs/009-cloud-provider-compat/phase-a-report.md`：列出改动文件、实际命令与退出码、真实/离线证据区分、失败与限制、下一阶段范围，并写明“报告后暂停，等待用户验收”。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖
- **Foundational (Phase 2)**: 依赖 Setup，阻塞所有用户故事
- **User Stories (Phase 3+)**: 依赖 Foundational；US1 与 US2 因同处 `model_provider.py`，需串行修改该文件；US3 为回归验证，可在 US1/US2 后执行
- **Polish (Phase 6)**: 依赖 US1–US3 完成

### User Story Dependencies

- **US1 (P1)**: Foundational 之后即可开始，无故事间依赖
- **US2 (P1)**: 与 US1 共享 `backend/app/rag/model_provider.py`，必须在 US1 之后修改同一文件
- **US3 (P2)**: 独立验证，可与 US2 的测试准备并行

### Within Each User Story

- 失败用例先写并确认失败，再实现
- 契约字段先于实现
- 同一文件（`model_provider.py`）的改动必须串行

### Parallel Opportunities

- T002 与 T001 可并行（不同文件）
- T003 与 T004 可并行（测试文件与产品文件）
- T012 的断言与 T010 的断言可在同一测试文件中顺序添加
- T014 与 T015 可并行准备，但 T015 依赖 T014 的实际运行记录

## Implementation Strategy

1. 完成 Setup 与 Foundational（T001–T004）。
2. 完成 US1（T005–T008）→ 独立验证 → 这是最小可用增量。
3. 完成 US2（T009–T011）→ 独立验证。
4. 完成 US3 回归（T012–T013）。
5. 执行 Polish（T014–T016），交付报告后暂停等待用户验收。

## Notes

- 改动前先确认 `backend/.env` 未被覆盖；不得提交、推送或修改用户密钥。
- 真实端点运行会消耗额度，只提交必要次数的问题。
- 未运行的检查不得写成通过；离线通过不等于真实端点问答质量通过。

## 实际执行说明（2026-10-15）

- **T003 偏离 TDD 顺序**：失败用例与实现同批编写，未单独保存“先失败”的快照。测试的证明力来自“全量回归无新增失败 + 新增 7 项断言全部通过”，而非红→绿。如实记录，未事后伪造失败记录。
- **T002 证据位置**：环境事实与两项根因的复现结果写在 `phase-a-report.md` §2，未另存原始命令输出。
- **T013 结果**：591 passed / 2 failed；两处失败均为 007 改写提示词后的既有措辞断言，与本次改动无因果关系（见报告 §6.1）。
- **T015 结果**：两次真实运行均 ≤300 秒（16834 ms / 16573 ms），`cloud_calls` 与 `model_calls` 一致（3/3、4/4），事件与日志未出现密钥或提示词正文。
- **T014 结果**：第 1 次得到答案与来源（主证据）；第 2 次 `budget_exceeded`（如实保留，未重跑挑选成绩）。
