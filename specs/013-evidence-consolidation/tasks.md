# Tasks: 第一组证据能力合并

**Input**: spec.md、plan.md、research.md、data-model.md、contracts/compatibility.md、quickstart.md。
**Status**: 阶段 A 共 7/7 工程任务完成，待用户验收；见 [报告](phase-a-report.md)。报告后暂停，等待用户验收。
**Tests**: FR-005 要求隔离工程检查；本次保持行为，以前后基线验证，不人为制造失败。

## Phase 1: Setup（A 内）

- [x] T001 保存源码/Git/原失败基线至 output/merge013/phase-a/，核对 hooks、ignore 与适用 AGENTS。

## Phase 2: Foundational（A 内）

- [x] T002 在 output/merge013/phase-a/ 准备保护及 run.py，禁 dotenv/网络/真实模型/正式数据；运行既有定向集合保存合并前基线。

## Phase 3: US1 证据能力收拢（Priority P1，A 内）

**Goal**: 同文件维护证据能力，旧入口移除且行为保持。
**Independent Test**: 所有搬移函数/常量 AST 保持；原证据与图兼容回归、合成文件和完整单元边界通过。

- [x] T003 [US1] 在 backend/app/rag/evidence.py 原样搬移 procedure_evidence.py 五函数四常量，补 Path 导入；删除 backend/app/rag/procedure_evidence.py。
- [x] T004 [US1] 迁移 backend/tests/unit/test_v3_7_procedure_evidence.py 导入，补合成安全读取与单元筛选边界：同目录/document_id、≤10 MiB、空路径/缺失/读取错误；complete is True 且同时位于 raw_text/content。
- [x] T005 [US1] 使用 output/merge013/phase-a/run.py 执行合并后定向与间接调用回归，保存实际 argv/退出码/guard，不覆盖初次结果。

## Phase 4: Polish（A 内）

- [x] T006 在 output/merge013/phase-a/ 保存 AST/manifest/引用/文件数量审计与差异，核对 backend/app/rag/evidence.py 编译和范围差异。
- [x] T007 更新 specs/013-evidence-consolidation/tasks.md，保存 specs/013-evidence-consolidation/phase-a-report.md，写明真实未测及“报告后暂停，等待用户验收”。

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006 → T007。US1 是唯一故事和 MVP，没有后续自动阶段。

## Parallel Examples

US1 的文件搬移、旧入口删除和导入迁移相互依赖，串行实施；无独立 [P] 任务，不派新代理。

## Implementation Strategy

先基线再组织改动，完成同阶段定向验证和报告。FR-001/003→T003–T006，FR-002→T003/T004/T006，FR-004/006→T001/T006/T007，FR-005→T002/T004/T005。7 项任务，US1 三项；任务勾选不代替用户验收。
