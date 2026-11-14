# Implementation Plan: Light Modern Knowledge Workspace

**Branch**: `008-frontend-light-redesign` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Status**: Draft plan only. No implementation phase has started.

## Summary

Redesign the existing login page and three authenticated frontend pages as one warm Light, modern knowledge-workbench experience. The implementation will establish shared visual tokens and a light navigation shell, then apply page-specific hierarchy: input-first question flow with answer-led results, document-list-first knowledge management, and troubleshooting-first logs. It is a presentation-only change: existing authentication, API calls, SSE event handling, user actions and business semantics remain unchanged.

## Technical Context

| Area | Decision |
|---|---|
| Language/Version | TypeScript with the repository's existing React 18 toolchain |
| Primary dependencies | Existing React, React DOM, Vite, Vitest and CSS; no new dependency planned |
| Storage | N/A; no persistence or API model changes |
| Testing | Existing Vitest suite, TypeScript/Vite build, manual desktop visual review using the quickstart guide |
| Target platform | Desktop browser at the existing local Vite development URL; Windows development environment |
| Project type | React web application with a FastAPI/SSE backend contract that remains untouched |
| Performance goals | Preserve current interaction responsiveness and avoid runtime-heavy visual dependencies or continuous animation |
| Constraints | Presentation-only scope; no API, SSE, auth, business-rule, model or backend changes; desktop-first; preserve semantic states and evidence wording |
| Scale/Scope | Four visible surfaces, one shared shell, existing pages/components/styles/tests; no new product capability |

## Constitution Check

**Pre-design gate: PASS**

- **阶段边界交付**: The plan is a new, bounded presentation phase and explicitly stops before implementation.
- **RAG 模块单一职责**: No backend, retrieval, model, API or SSE module changes are planned.
- **基于证据回答**: Answer/source/verification content and its truthful wording remain intact; only visual order and disclosure change.
- **安全且一致的数据处理**: No credentials, environment files, documents, indexes or persistent data are changed.
- **可观察且可验证的行为**: Existing status, error, process and verification states remain visible and are covered by existing behavior tests plus manual visual review.

**Post-design gate: PASS**

The design artifacts introduce no new contract or constitution exception. Any future implementation that changes API/event semantics must leave this plan's scope and require a separate approved feature or plan update.

## Project Structure

### Documentation (this feature)

```text
specs/008-frontend-light-redesign/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-visual.md
└── checklists/
    └── requirements.md
```

### Source Code (future implementation scope)

```text
frontend/src/
├── App.tsx                         # route/auth composition; preserve behavior
├── components/
│   ├── AppLayout.tsx               # light shell, left navigation, context bar
│   ├── ProcessPanel.tsx            # secondary execution disclosure and states
│   ├── ScoreCard.tsx               # verification hierarchy and status tokens
│   └── StateView.tsx                # shared empty/loading/error treatment
├── pages/
│   ├── Login.tsx                   # Light entry surface
│   ├── Chat.tsx                    # input-first and answer-led hierarchy
│   ├── Knowledge.tsx                # document-list-first hierarchy
│   └── Logs.tsx                     # compact filters and diagnostic table
└── styles/
    └── app.css                     # shared tokens, layout, states and desktop rules

frontend/src/**/*.test.*             # preserve and extend behavior assertions only where structure changes require it
```

**Structure Decision**: Keep the existing single frontend application and component boundaries. Prefer shared presentational primitives and CSS tokens over a new design-system package. Do not touch `frontend/src/api`, `frontend/src/types/api.ts` or backend files for this feature.

## Design Direction and Decisions

- **Aesthetic**: warm editorial knowledge workbench; white surfaces, deep ink, orange evidence/action accent, calm state colors.
- **Shell**: light left rail/sidebar plus a top context bar. The top bar is deliberately sparse: page title, status and one primary action.
- **Typography**: serif display/brand headings, sans-serif interface text, monospaced IDs/counts/timing. Reuse existing font roles or safe equivalents without adding a visual-only dependency.
- **Question page**: retain the question form as the first visual action. Make the answer and sources the default reading path; move process, retrieval and usage into an explicit secondary/disclosure treatment while keeping all data available.
- **Knowledge page**: make the document list the visual center; make upload the single dominant action. Preserve document status, counts, errors and deletion confirmation.
- **Logs page**: keep the dense diagnostic table but reduce surrounding chrome; compact filters and on-demand row details should improve scanability without changing query parameters.
- **Login**: align its entry art, form, type and state treatment with the same Light token system while preserving credential fields and login behavior.
- **Feedback**: use short transitions only for loading, success, error and expanded/collapsed details; support reduced-motion preferences if an animation is added.

## Phased Implementation Plan and Stop Points

### Phase 1 — Shared Light foundation and shell

**Scope**: Define CSS tokens and type roles; convert the authenticated shell to a light left navigation plus top context bar; align login page surfaces; preserve route/auth/logout semantics.

**Likely files**: `frontend/src/styles/app.css`, `frontend/src/components/AppLayout.tsx`, `frontend/src/pages/Login.tsx`, and only the minimal `App.tsx` presentational composition needed by the shell.

**Acceptance**: Login and all authenticated routes share the palette and type roles; active/focus/disabled/status states are legible; navigation and authentication behavior tests remain valid.

**Validation**: `npm test -- --run`, `npm run build`, plus the login/shell checklist in [quickstart.md](quickstart.md).

**Report**: `specs/008-frontend-light-redesign/phase-1-report.md`; after the report, pause for user acceptance before Phase 2.

### Phase 2 — Page hierarchy and disclosure presentation

**Scope**: Apply the agreed hierarchy to `Chat.tsx`, `ProcessPanel.tsx`, `ScoreCard.tsx`, `Knowledge.tsx`, `Logs.tsx` and shared state treatment. Add only presentational disclosure/row-detail interactions required by the UI contract; preserve all existing event handling and API calls.

**Acceptance**: Input-first idle chat, answer-first result, source visibility, accessible execution disclosure, document-list-first library, compact log filters and readable diagnostic rows across loading/empty/error/processing states.

**Validation**: Existing frontend behavior tests, build, and the manual regression scenarios in [quickstart.md](quickstart.md). Add focused tests only where a new disclosure control or changed DOM structure needs a meaningful behavior assertion.

**Report**: `specs/008-frontend-light-redesign/phase-2-report.md`; after the report, pause for user acceptance before Phase 3.

### Phase 3 — Desktop visual QA and regression handoff

**Scope**: Review all four surfaces at the normal desktop viewport, check long-content and state variants, collect screenshots/manual findings, and correct only presentation defects found during review.

**Acceptance**: SC-001 through SC-006 are reviewed; no API/SSE/auth/business behavior changed; the final visual state and known limitations are documented.

**Validation**: `npm test -- --run`, `npm run build`, manual route/state matrix, and screenshot review. No backend/model evaluation is required for this presentation-only feature.

**Report**: `specs/008-frontend-light-redesign/phase-3-report.md`; report delivery is the final stop for this plan and must state “报告后暂停，等待用户验收”.

## Validation Matrix (planned, not executed)

| Check | When | Expected evidence |
|---|---|---|
| `npm test -- --run` | Each implementation phase | Existing behavior contracts remain green; any changed DOM behavior has a focused assertion |
| `npm run build` | Each implementation phase | TypeScript and Vite build complete |
| Manual login/shell review | Phase 1 | Shared Light palette, active navigation, focus and status states |
| Manual chat state review | Phase 2 | Idle, running, clarification, answer, source, verification and error hierarchy |
| Manual library/log review | Phase 2 | Document lifecycle states and log filtering/table readability |
| Desktop screenshot matrix | Phase 3 | Four pages and representative states meet the visual contract |

No command in this matrix has been run as part of plan creation.

## Risks and Mitigations

- **Presentational restructuring can accidentally change behavior**: keep API/event imports and state transitions intact; validate existing tests after each phase.
- **Collapsed process details can hide diagnostic evidence**: use an explicit accessible disclosure and retain all current process, retrieval and usage content.
- **Light surfaces can weaken status contrast**: centralize state tokens, test focus/disabled/error states and review text/icon labels alongside color.
- **Long evidence, filenames and log messages can break the layout**: define wrapping/truncation behavior and inspect representative long-content cases in Phase 3.
- **Current visual tests are sparse**: rely on manual screenshots for appearance and reserve automated tests for meaningful behavior/semantics; do not claim visual coverage that was not run.

## Complexity Tracking

No constitution violations or new architectural components are planned. The existing component boundaries and API contracts are intentionally reused.
