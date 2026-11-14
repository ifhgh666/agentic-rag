# Feature Specification: Light Modern Knowledge Workspace

**Feature Branch**: `008-frontend-light-redesign`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: “将现有前端重做为以白色 Light 为主的现代知识工作台，统一登录页、问答台、知识库和运行日志的视觉与信息层级，同时保持现有流程和接口行为。”

## User Scenarios & Testing

### User Story 1 - Enter a coherent workspace (Priority: P1)

As an administrator, I want the login page and the three authenticated pages to feel like one coherent Light workspace so that I can understand where I am and what to do without relearning the interface on each page.

**Why this priority**: A consistent shell and visual language are the foundation for every later task.

**Independent Test**: Open the login page and each authenticated route at desktop width; identify the active page, primary action, service state, and page purpose without relying on implementation details.

**Acceptance Scenarios**:

1. **Given** a user is on the login page, **When** the page loads, **Then** the entry experience uses the same Light visual language as the authenticated workspace.
2. **Given** a user is authenticated, **When** they switch among 问答台、知识库 and 运行日志, **Then** the navigation, active state, page title area and status treatment remain consistent.

### User Story 2 - Ask and inspect an answer (Priority: P1)

As an administrator, I want the question input to be the clear first action and the resulting answer to lead the page, so that evidence and execution details support my reading instead of competing with it.

**Why this priority**: Asking a question and understanding its grounded answer is the primary product journey.

**Independent Test**: Start a new session, submit a question, and inspect the resulting answer, sources, clarification state, loading state and expandable execution details without changing the request behavior.

**Acceptance Scenarios**:

1. **Given** a new session, **When** the question page opens, **Then** the input area is the visual primary action and session/service context is secondary.
2. **Given** an answer has arrived, **When** the user reads the page, **Then** the answer appears before sources, while process and usage details are available on demand.
3. **Given** a request is loading, clarifying, insufficient or failed, **When** the state changes, **Then** the state is clearly visible without changing the existing action semantics.

### User Story 3 - Manage documents and inspect operations (Priority: P2)

As an administrator, I want the document list and operational log to be easy to scan, so that I can upload and monitor knowledge documents and investigate a request without visual clutter.

**Why this priority**: These pages support the primary question flow and must remain reliable during visual changes.

**Independent Test**: On the knowledge page, upload or inspect a document list and its processing states; on the logs page, apply filters and inspect a log row while preserving the current API behavior.

**Acceptance Scenarios**:

1. **Given** the knowledge page, **When** it opens, **Then** the document list is the main content and upload is the single prominent action.
2. **Given** a document is processing, ready or failed, **When** its row is viewed, **Then** the state is legible and visually distinct without hiding the existing error or count information.
3. **Given** the logs page, **When** filters are applied, **Then** the compact filter bar and diagnostic table remain easy to scan, with row details available without changing the query behavior.

## Edge Cases

- Empty knowledge base and empty log results remain understandable and retain their existing next-step actions.
- Long document names, long answers, many sources and dense log messages remain readable without breaking the desktop layout.
- Loading, clarification, processing, ready, failed and insufficient states remain distinguishable.
- Existing confirmation and error behavior, including document deletion confirmation, is preserved.
- The design is desktop-first; mobile-specific redesign is outside this feature.

## Requirements

### Functional Requirements

- **FR-001**: The login page and all three authenticated pages MUST share a Light visual system built around warm white surfaces, deep ink text, restrained borders and orange primary emphasis.
- **FR-002**: The authenticated shell MUST provide a light left navigation and a top context bar with the current page title, service/session state and at most one primary page action.
- **FR-003**: The active navigation state, focus state, disabled state, loading state, success state and error state MUST be visually distinguishable.
- **FR-004**: The question page MUST present the input as the first visual action, place the answer before its sources, and provide execution details through an explicit expandable or secondary presentation.
- **FR-005**: The knowledge page MUST present the document list as the main content and the PDF upload action as the prominent page action.
- **FR-006**: The logs page MUST present a compact filter area and a diagnostic table whose level, time, module and message remain scannable; detailed row information MAY be revealed on demand.
- **FR-007**: Typography MUST use a serif treatment for brand/display headings, a sans-serif treatment for interface text and a monospaced treatment for identifiers and measurements.
- **FR-008**: Motion MUST remain restrained and limited to feedback for loading, success, error and expand/collapse interactions.
- **FR-009**: The redesign MUST preserve existing authentication, navigation, question submission, clarification, document upload/deletion, log filtering and API behavior.
- **FR-010**: The redesign MUST target desktop layouts first and MUST NOT introduce mobile-only functionality or a new backend contract.

### Key Entities

- **Workspace shell**: The shared visual frame containing navigation, page context and service/session state.
- **Question result**: The existing answer, source references, verification state and optional execution details shown after a question.
- **Knowledge document**: An existing uploaded PDF with filename, processing state and counts displayed in the document list.
- **Log record**: An existing operational entry with level, timestamp, module, message and request/thread identifiers.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A reviewer can identify the active page, primary action and service/session state on each of the four redesigned pages within 5 seconds of opening it.
- **SC-002**: The four pages use the same palette, type roles, spacing rhythm, navigation treatment and state vocabulary, with no page-specific visual system that contradicts the shared rules.
- **SC-003**: The existing question, PDF upload, document deletion confirmation and log-filter flows remain completable from the redesigned UI without an API or business-rule change.
- **SC-004**: The answer, source strip and optional execution details appear in the agreed order after a successful question request; no process panel obscures the primary answer by default.
- **SC-005**: Empty, loading, processing, clarification, insufficient and error states are visibly distinguishable in manual desktop review and relevant existing frontend tests/build continue to pass during implementation.
- **SC-006**: The desktop layout remains readable at the repository’s normal development viewport without horizontal clipping of the primary action, answer, document filename or log message.

## Assumptions

- The target user is the existing single administrator using the desktop browser workbench.
- The current authentication, SSE events, document APIs, log APIs and business semantics are reused unchanged.
- Mobile-specific redesign, new search, new dashboard metrics and new product capabilities are out of scope.
- Existing fonts may be retained or replaced by an equivalent local/system-safe role mapping; the plan must avoid introducing a dependency solely for visual polish.
- Visual verification will use the running frontend and existing frontend test/build commands; backend/model evaluation is not part of this feature.
