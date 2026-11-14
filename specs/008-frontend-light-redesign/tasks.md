# Tasks: Light Modern Knowledge Workspace

**Input**: Design documents from `/specs/008-frontend-light-redesign/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/ui-visual.md`, `quickstart.md`

**Scope rule**: Generic execution is limited to the first unfinished implementation phase. Phase 1 is the only phase authorized in the current turn; later tasks remain unchecked until separately accepted.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing frontend toolchain and preserve the current dependency/API boundary.

- [X] T001 Confirm the existing Vite/React/Vitest scripts and lockfile in `frontend/package.json` and `frontend/package-lock.json`; do not add dependencies.
- [X] T002 Record the presentation-only file boundary in `specs/008-frontend-light-redesign/plan.md` and keep `frontend/src/api/` and `frontend/src/types/api.ts` unchanged.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared visual tokens and shell primitives before page-specific hierarchy work.

- [X] T003 Define shared Light palette, typography roles, state colors, focus treatment and reduced-motion rules in `frontend/src/styles/app.css`.
- [X] T004 Add the authenticated top context bar and accessible active navigation semantics in `frontend/src/components/AppLayout.tsx` without changing hash routing, logout or service status meaning.
- [X] T005 Align the login surface with the shared Light tokens and preserve credential fields, submit behavior and error semantics in `frontend/src/pages/Login.tsx`.

**Checkpoint**: Shared Light foundation and shell are ready; page-specific result/list/log hierarchy remains for later phases.

## Phase 3: User Story 1 - Enter a coherent workspace (Priority: P1) 🎯 MVP

**Goal**: Make login and authenticated navigation feel like one coherent Light workspace.

**Independent Test**: Open login and each authenticated route at desktop width; identify the active page, primary action, service state and page purpose, then verify login/navigation/logout behavior remains unchanged.

### Implementation

- [X] T006 [US1] Review and refine shared shell spacing, focus, active and disabled states in `frontend/src/components/AppLayout.tsx` and `frontend/src/styles/app.css` against `contracts/ui-visual.md`.
- [X] T007 [US1] Review login validation/error/loading presentation in `frontend/src/pages/Login.tsx` and `frontend/src/styles/app.css` without changing the auth API call.
- [X] T008 [US1] Run the Phase 1 shell/login verification commands from `specs/008-frontend-light-redesign/quickstart.md` and record results in `specs/008-frontend-light-redesign/phase-1-report.md`.

**Checkpoint**: User Story 1 is independently reviewable. Stop after the phase report and wait for user acceptance.

## Phase 4: User Story 2 - Ask and inspect an answer (Priority: P1)

**Goal**: Make the question form the first visual action and make answers lead the result view.

**Independent Test**: Submit a question and inspect idle, running, clarification, answer, source, verification and error states without changing SSE/API behavior.

- [X] T009 [US2] Reorder and restyle the question input, session context and clarification card in `frontend/src/pages/Chat.tsx`.
- [X] T010 [US2] Add accessible execution-detail disclosure while preserving process, retrieval and usage content in `frontend/src/components/ProcessPanel.tsx` and `frontend/src/pages/Chat.tsx`.
- [X] T011 [US2] Rebalance answer, source and verification hierarchy in `frontend/src/pages/Chat.tsx`, `frontend/src/components/ScoreCard.tsx` and `frontend/src/styles/app.css`.
- [X] T012 [US2] Update meaningful chat behavior assertions only if changed disclosure structure requires them in `frontend/src/pages/Chat.test.tsx` and `frontend/src/components/ProcessPanel.test.tsx`.

## Phase 5: User Story 3 - Manage documents and inspect operations (Priority: P2)

**Goal**: Make document management and operational diagnostics easy to scan.

**Independent Test**: Inspect empty/loading/processing/ready/failed document states, upload/delete flows, filtered logs and log row details with existing API behavior.

- [X] T013 [US3] Make the document list primary and the upload action prominent while preserving lifecycle states in `frontend/src/pages/Knowledge.tsx` and `frontend/src/styles/app.css`.
- [X] T014 [US3] Make log filters compact and diagnostic rows readable, adding on-demand detail presentation only if it preserves current query fields in `frontend/src/pages/Logs.tsx` and `frontend/src/styles/app.css`.
- [X] T015 [US3] Add focused behavior assertions for any new document/log disclosure semantics in `frontend/src/pages/Logs.test.tsx` and relevant frontend tests.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full visual system and preserve the existing product contracts.

- [X] T016 [P] Run `npm test -- --run` from `frontend/` and record the exact exit status in `specs/008-frontend-light-redesign/phase-3-report.md`.
- [X] T017 [P] Run `npm run build` from `frontend/` and record the exact exit status in `specs/008-frontend-light-redesign/phase-3-report.md`.
- [X] T018 Perform the desktop screenshot/state matrix in `specs/008-frontend-light-redesign/quickstart.md` and record findings in `specs/008-frontend-light-redesign/phase-3-report.md`.
- [X] T019 Confirm `frontend/src/api/`, `frontend/src/types/api.ts`, backend routes and authentication semantics are unchanged for this feature; document any discrepancy before proceeding.

## Dependencies & Execution Order

- T001–T002 are setup checks and do not change runtime behavior.
- T003–T005 are the shared foundation and must precede all user-story work.
- T006–T008 complete the first authorized implementation phase and must stop after the Phase 1 report.
- T009–T012 depend on the accepted Phase 1 foundation.
- T013–T015 depend on the accepted Phase 1 foundation and may follow User Story 2 sequentially because both touch shared styles.
- T016–T019 are final cross-cutting checks after the desired user stories are implemented.

## Parallel Opportunities

- T016 and T017 can run in parallel after implementation because they use different commands and produce independent evidence.
- Future visual review of `Knowledge.tsx` and `Logs.tsx` can be prepared in parallel, but shared `app.css` edits must remain sequential.

## Implementation Strategy

1. Complete the shared Light foundation and shell (T001–T005).
2. Complete and validate User Story 1 only (T006–T008); stop for user acceptance.
3. After acceptance, implement the chat hierarchy (T009–T012), then stop for acceptance.
4. After acceptance, implement document/log hierarchy (T013–T015), then run final polish checks (T016–T019).

## Notes

- Every task includes concrete repository paths and remains unchecked until actually completed.
- No task authorizes API, SSE, backend, model, auth-rule or new-product behavior changes.
- This task list intentionally separates the plan's three implementation phases from the Spec Kit's user-story grouping.



