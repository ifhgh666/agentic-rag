# Presentation Data Model: Light Modern Knowledge Workspace

This feature changes how existing data is presented. It introduces no persisted entity, API field, SSE event or backend model.

## Workspace shell

| Field | Meaning | Source/constraint |
|---|---|---|
| `route` | Current authenticated route | Existing hash route in `App.tsx` |
| `navigationItems` | Links for 问答台、知识库、运行日志 | Existing `AppLayout.tsx` list |
| `activeItem` | Current navigation selection | Derived from `route` |
| `serviceStatus` | Local service status indicator | Existing UI state; no new health contract |
| `logoutAction` | Existing logout control | Existing auth client/session behavior |

The shell hosts one `PageContext` and one page body. It must not own page-specific API calls.

## Page context

| Field | Meaning | Examples |
|---|---|---|
| `eyebrow` | Small section identifier | `问答 / 01`, `LIBRARY / 02` |
| `title` | Current page title | 问答台、知识库、运行日志 |
| `description` | One-sentence purpose | Existing page descriptions, edited only for hierarchy if needed |
| `status` | Session or service context | New session, same session, local service online |
| `primaryAction` | At most one prominent action | Start retrieval, choose PDF, apply filters |

## Chat presentation

The existing chat state remains authoritative:

- `question` and `action` drive the current input form.
- `pending` drives clarification choices.
- `running`, `error` and `notice` drive visible request states.
- `answer` and `sources` form the primary result.
- `verification` is a secondary evidence-status card.
- `stages`, `executionEvents`, `retrieval` and `usage` form optional execution details.

Relationship: one question request may produce zero or one clarification state and zero or one final answer, with sources and verification attached to the answer when available.

## Knowledge presentation

`DocumentItem` remains the source of truth for each row:

- identity: `document_id`, `filename`
- lifecycle: `status`, `error_reason`
- metadata: `uploaded_at`, `size_bytes`
- index counts: `parent_count`, `child_count`

The page state is `loading`, `empty`, `ready`, `busy` or `error`; these are presentation states over the existing document API.

## Log presentation

`LogItem` remains the source of truth for each record:

- classification: `level`, `module`
- timing: `timestamp`, `duration_ms`
- message: `message`
- correlation: `request_id`, `thread_id`

The page state is `loading`, `empty`, `loaded` or `error`; filter values remain the existing level/module/request/thread query fields.

## State transitions

- `unauthenticated -> authenticated`: existing login success and token persistence.
- `chat idle -> running -> answer | clarification | error`: existing SSE event flow; redesign changes ordering and visibility only.
- `documents loading -> empty | ready | error`; `ready -> busy -> ready | error` for upload/delete: existing API lifecycle.
- `logs loading -> empty | loaded | error`; `loaded -> loading -> empty | loaded | error` after filtering: existing API lifecycle.

## Non-goals

No new storage, server state, route, query parameter, API payload, SSE event, authentication rule or model behavior is introduced by this feature.
