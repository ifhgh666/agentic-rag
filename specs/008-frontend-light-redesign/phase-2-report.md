# Phase 2 Report: Page Hierarchy and On-demand Details

**Feature**: [008-frontend-light-redesign](.)
**Plan**: [plan.md](plan.md)
**Phase**: Phase 2 — Page hierarchy and disclosure presentation
**Date**: 2026-10-15
**Status**: Completed for this phase; awaiting user acceptance.

## Scope and authorization

The user explicitly authorized the next phase after accepting Phase 1. This phase implemented the approved page hierarchy across the question workspace, process/verification surfaces, knowledge library and operation logs. Existing API calls, SSE event handling, authentication and business semantics were preserved.

## Completed work

- Reordered the question result path in [Chat.tsx](../../frontend/src/pages/Chat.tsx): answer and sources render before verification and the process trace; execution details are available through an accessible native disclosure and open automatically while a request is running.
- Added an embedded presentation mode to [ProcessPanel.tsx](../../frontend/src/components/ProcessPanel.tsx) so the same process, retrieval and usage data can be disclosed without a competing outer card heading.
- Marked [ScoreCard.tsx](../../frontend/src/components/ScoreCard.tsx) as a secondary result surface while preserving all four verification states and the existing limitation wording.
- Promoted the PDF action into the knowledge-page header and made the document list the main content in [Knowledge.tsx](../../frontend/src/pages/Knowledge.tsx). Existing upload validation, polling, deletion confirmation, status counts and error behavior remain.
- Converted log rows into native expandable entries with compact filters and full correlation details in [Logs.tsx](../../frontend/src/pages/Logs.tsx). Existing filter fields and `listLogs` request parameters remain unchanged.
- Added Phase 2 Light hierarchy and disclosure styles in [app.css](../../frontend/src/styles/app.css), including long-message wrapping, log detail grids, open/closed states and an explicit rule keeping hidden file inputs hidden.
- Added focused assertions for execution disclosure ordering in [Chat.test.tsx](../../frontend/src/pages/Chat.test.tsx) and log detail rendering/filter semantics in [Logs.test.tsx](../../frontend/src/pages/Logs.test.tsx).
- Marked T009–T015 complete in [tasks.md](tasks.md).

## Verification performed

All commands ran from `frontend/` on 2026-10-15:

| Command | Exit status | Result |
|---|---:|---|
| `npm test -- --run` (initial Phase 2 run) | 1 | 1 test failed because the new disclosure assertion fixture emitted an answer without a stage event; 25 tests passed |
| `npm test -- --run` (after fixture correction) | 0 | 8 test files, 26 tests passed |
| `npm run build` | 0 | TypeScript/Vite production build passed |
| `git diff --check -- frontend/src/pages/Chat.tsx frontend/src/components/ProcessPanel.tsx frontend/src/components/ScoreCard.tsx frontend/src/pages/Knowledge.tsx frontend/src/pages/Logs.tsx frontend/src/pages/Chat.test.tsx frontend/src/pages/Logs.test.tsx frontend/src/styles/app.css` | 0 | No whitespace errors reported |

Manual desktop review through the existing local browser session checked:

- 问答台 keeps the input as the first action and exposes the new context for execution details.
- 知识库 promotes “选择 PDF” to the header and keeps empty/error/document-list states readable. A first review found the browser file input visible because a global input rule overrode `hidden`; `input[hidden] { display: none !important; }` corrected it and the page was rechecked.
- 运行日志 presents a compact filter card and a readable empty/error state; populated rows render as expandable details with correlation IDs and full messages.

## Real vs simulated checks

- Vitest uses mocked API/SSE behavior and does not call the live model, retrieval pipeline or backend.
- The Vite build is a local static type/bundle check.
- Manual review used the local frontend. The backend was not started in this phase, so knowledge/log pages showed their existing request-error state; no document mutation, log write or production index operation occurred.

## Limitations and findings

- The page headers remain alongside the shared top context bar from Phase 1; the approved design keeps both until a later cleanup decision changes the shell hierarchy.
- No mobile-specific redesign was added, consistent with the desktop-first scope.
- The saved Phase 1 screenshot remains the available file artifact for the Light visual language; Phase 2 page-state review was performed in the existing authenticated browser session.
- Existing unrelated dirty changes in backend, API/type and other frontend files were preserved. This phase directly edited only the Phase 2 presentation files, relevant frontend tests and the 008 report/task artifacts.

## Next phase

Phase 3 is the final desktop visual QA and regression handoff: review the full route/state matrix, capture final screenshots, run the final test/build checks and document any presentation defects. It requires user acceptance of this Phase 2 report before starting.

**报告后暂停，等待用户验收。**
