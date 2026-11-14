# UI Visual Contract: Light Modern Knowledge Workspace

This contract defines the user-visible shell and hierarchy for the presentation-only redesign. Existing API and behavior contracts remain authoritative.

## Global visual tokens

- **Surface**: warm white page background with slightly elevated white panels.
- **Ink**: deep charcoal for headings and primary text; muted slate for supporting text.
- **Accent**: warm orange for primary actions, active indicators and evidence emphasis.
- **State**: green for ready/verified, red for error/issue, amber/orange for processing/warning.
- **Type roles**: serif for brand/display headings, sans-serif for controls and explanatory text, monospaced for IDs, counts, timing and token data.
- **Motion**: short, purposeful transitions only for state feedback and disclosure controls.

Exact values are implementation details, but every page must consume the same token set.

## Shared shell contract

1. Login and authenticated routes use the same Light palette and type roles.
2. Authenticated routes show a stable left navigation with an unambiguous active item.
3. The top context bar contains the page title, a concise status and no more than one primary action.
4. Focus, hover, disabled, loading, success and error states remain distinguishable without relying on color alone.
5. Logout and service status remain available from the existing shell location or an equally discoverable replacement.

## Route contracts

| Route | Primary visual task | Secondary content | Required states |
|---|---|---|---|
| Login | Enter the local workbench | Credential explanation and error | idle, validating, invalid credentials |
| `/chat` | Write and submit a question | Session context, answer sources, optional execution details | idle, running, clarification, answer, insufficient, error |
| `/knowledge` | Scan documents and upload a PDF | Counts, processing status, errors | loading, empty, processing, ready, failed |
| `/logs` | Filter and inspect operational records | Correlation IDs and duration | loading, empty, loaded, error |

## Behavior contract

- Existing submit, clarification action, new-session, upload, delete-confirmation and log-filter interactions keep their current semantics.
- Execution details may be collapsed or disclosed, but their existing diagnostic content must remain available and must not be rewritten to imply stronger guarantees.
- Answer sources and verification wording remain truthful; visual emphasis must not imply that source location proves answer completeness.
- Long content wraps or truncates with an accessible way to inspect the full value; the primary action remains visible at the target desktop viewport.

## Accessibility contract

- Preserve semantic headings, labels, form controls, `aria-live` status regions, alert roles and accessible button names.
- Maintain visible keyboard focus and sufficient text/control contrast on warm white surfaces.
- Disclosure controls for execution details expose their expanded/collapsed state.
- Status meaning is conveyed by text or icon plus color, never color alone.

## Regression contract

A compliant implementation leaves `frontend/src/api`, `frontend/src/types/api.ts`, backend routes, authentication semantics and SSE event handling unchanged unless a future approved scope explicitly says otherwise.
