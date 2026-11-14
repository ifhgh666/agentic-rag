# Tasks: RAG 八文件收敛

**Input**: spec/plan/research/data-model/contracts/quickstart。
**Status**: A 共 9/9 工程任务完成，待验收；见 [阶段报告](phase-a-report.md)。报告后暂停，等待用户验收。
**Tests**: FR-006 要求完整隔离回归；行为保持重构采用前后基线，不人为制造红测。

## Phase 1: Setup（A 内）

- [x] T001 保存全部 app/tests/scripts/frontend 源码、Git 差异和失败历史到 output/eight014/phase-a/before，完成规格和设计门。

## Phase 2: Foundation（A 内）

- [x] T002 在 output/eight014/phase-a/run.py 与 eight014_guard.py 复用最终保护，运行 before-full，保留旧失败及 24 PDF/2 Dense 未测项。

## Phase 3: US1 八文件（P1，A 内）

**Goal**: 八个实际源文件，全部能力保留且依赖有向无环。
**Independent Test**: 精确文件集合、完整符号映射、归一化算法 AST、隔离全量后端与实际调用契约。

- [x] T003 [US1] 在 backend/app/rag/schemas.py、graph_state.py 归入纯模型/工具契约与会话数据/存储；不含模型摘要或向节点的反向依赖。
- [x] T004 [US1] 将编码/索引/检索/调用治理/缓存/准入/计量归入 backend/app/rag/tools.py，normalize_query 同归 tools；保留 provider/资源生命周期/单飞/共享预算类 seam。
- [x] T005 [US1] 将业务行为归入 backend/app/rag/nodes.py、pipeline 归入 graph.py，保留 edges/prompts/__init__；删除所有被合并旧模块，禁止 sys.modules/forwarding/helper 实现。
- [x] T006 [US1] 迁移 backend/app、backend/scripts、backend/tests 的导入与必要 patch/source 定位，保留业务断言；增加 test_rag_architecture.py 的精确八文件和依赖无环检查。
- [x] T007 [US1] 用 output/eight014/phase-a/run.py 执行定向、完整后端与必要修复后验证，记录全部原始结果，guard 只改新类入口，不放宽保护。

## Phase 4: Polish（A 内）

- [x] T008 审计 output/eight014/phase-a/ 中全部原符号/方法 AST、提示/前端/失败历史保持、旧引用/循环消失，核对源码差异和编译。
- [x] T009 更新 README.md、docs/repository-guide.md 与 specs/014-eight-file-rag/ 文档，保存 phase-a-report.md，列实际布局/行数、命令、旧失败、未测和“报告后暂停，等待用户验收”。

## Dependencies & Execution Order

T001→T002→T003→T004→T005→T006→T007→T008→T009。US1 仅一个交付阶段；不自动进行真实问答或后续优化。

## Parallel Examples

纯数据、工具和节点依赖迁移需按顺序；全量基线期间可准备文档/转换脚本，不修改被测源码。评审可并行只读，生产合并由主代理完成。

## Implementation Strategy

先保存前后可比基线，再按符号归属静态合并，保留原代码片段；必要回归失败修复单列日志。FR-001/002、SC-001→T003–T008；FR-003、SC-002→T003–T006/T008；FR-004/005→T007/T008；FR-006、SC-003/004→T002/T007；FR-007→T001/T008/T009。9 项，US1 五项。
