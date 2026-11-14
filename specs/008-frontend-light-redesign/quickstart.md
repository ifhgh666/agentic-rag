# Quickstart Validation: Light Modern Knowledge Workspace

This guide is for the future implementation and review phase. It records how to validate the redesign; the commands below were **not run while writing this plan**.

## Prerequisites

- Node.js and the existing `frontend/node_modules` or a package install from the checked-in lockfile.
- For authenticated page checks, the existing backend and configured administrator credentials may be used. Do not add credentials to this document.

## Automated checks

From `frontend/`:

```powershell
npm test -- --run
npm run build
```

Expected result: existing frontend behavior tests pass and TypeScript/Vite build completes without changing API or business contracts.

## Local visual review

Start the existing frontend command from `frontend/`:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/` at the normal desktop development viewport and review:

1. Login: Light palette, shared brand/type roles, visible focus, validating state and error state.
2. Navigation: active route, service status, top context title and one primary action.
3. 问答台 idle: input is the first visual action; session hint is secondary.
4. 问答台 result: answer precedes sources; process/usage details are available but do not dominate by default.
5. 知识库: document list is primary; upload is the clear top action; empty/loading/processing/failed states are legible.
6. 运行日志: compact filters and table are scannable; long messages and correlation IDs remain readable.
7. Cross-page: same palette, spacing rhythm, type roles and status vocabulary on all four surfaces.

## Regression scenarios

- Submit a normal question and confirm the existing SSE result, source references and verification card still render.
- Trigger a clarification response and confirm the three existing actions retain their semantics.
- Upload a PDF, observe processing/ready or failure status, and verify delete confirmation remains present.
- Apply a log filter and confirm the existing request/module/level/thread query values are sent unchanged.

Record screenshots and any manual findings in the phase report. If any API/event or business behavior changes, stop the visual phase and open a separate approved scope.
