# Research: Light Modern Knowledge Workspace

**Feature**: [spec.md](spec.md)
**Date**: 2026-10-15
**Status**: Planning-only research; no frontend implementation has started.

## Repository findings

The optional delegated read-only research attempt was unavailable because the selected model was at capacity. The findings below were verified directly from the repository; no external research claim depends on that attempt.

- The frontend is a React 18 + TypeScript + Vite application under `frontend/src`.
- `App.tsx` selects the login screen or the authenticated shell by local token state and hash routes (`/chat`, `/knowledge`, `/logs`).
- `AppLayout.tsx` owns the shared brand, navigation, service status and logout affordance.
- `Login.tsx`, `Chat.tsx`, `Knowledge.tsx` and `Logs.tsx` own the four user-facing pages in scope.
- `ProcessPanel.tsx`, `ScoreCard.tsx` and `StateView.tsx` own reusable answer-process, verification and loading/empty/error states.
- `frontend/src/styles/app.css` is the current global style surface. It defines the existing dark editorial palette, layout, component classes and desktop/narrow-screen media rules.
- API and SSE behavior is isolated in `frontend/src/api` and the event/data contracts are in `frontend/src/types/api.ts`. The visual redesign can avoid changing these files.
- Existing tests cover chat clarification and result behavior, SSE parsing, process-panel wording, verification semantics, login/session contracts and a log-filter contract. There is no visual regression harness in the current repository.
- `frontend/package.json` exposes only `npm run dev`, `npm run build` and `npm test`; there is no lint script.

## Design decisions resolved with the user

- A modern knowledge-workspace direction with a predominantly white Light treatment.
- All four visible surfaces are in scope: login, question workspace, knowledge library and operation logs.
- The shell uses a light left navigation and a top context bar. The top bar contains the current title, status and one primary action at most.
- The question page is input-first; after submission, answer comes before sources and execution details are secondary/expandable.
- The knowledge page is document-list-first with upload as the primary action.
- The logs page is troubleshooting-table-first with compact filters and details on demand.
- The palette uses warm white, deep ink, orange emphasis, green ready states and red error states.
- Typography uses serif display headings, sans-serif interface text and monospaced identifiers/measurements.
- Motion is restrained and limited to loading, success, error and expand/collapse feedback.
- The work is desktop-first. Mobile-specific redesign and new product capabilities are out of scope.
- The implementation boundary is presentation-only: React presentation structure and CSS may change, but APIs, business rules and existing user flows remain unchanged.

## Design guidance applied

The `frontend-design` skill was used as a planning constraint: choose one coherent aesthetic direction, keep tokens centralized, use purposeful typography and a memorable but restrained visual cue, and avoid generic white/purple SaaS styling. For this feature, the differentiator is a warm editorial knowledge-workbench treatment carried through the shared shell and evidence states.

## Open questions resolved

No blocking unknowns remain for the plan. Font loading, exact spacing values and component decomposition are implementation choices to be evaluated during the first implementation phase without changing the approved product scope.

## Alternatives considered

- A top-only navigation was rejected because the three operational pages benefit from a stable route anchor.
- A dashboard-first home was rejected because the primary value is asking a grounded question, not viewing aggregate metrics.
- A full mobile redesign was rejected for this desktop-first phase.
- Backend/API changes were rejected because the requested outcome is visual hierarchy and the current contracts already support the required states.
