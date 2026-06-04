# epost-a11y-agent - Project Overview & PDR

## Product Purpose

epost-a11y-agent is a multi-platform accessibility auditor for iOS, Android, and Web codebases. It helps teams find WCAG 2.1 AA issues, review them through a human-in-the-loop workflow, and produce structured remediation guidance without modifying source code.

## Current State

- ADK agent graph is implemented in `app/agent.py`.
- Backend runtime is split between the ADK FastAPI wrapper on port 8000 and the validator sidecar on port 8001.
- Frontend dashboard is a React 19 + Vite 6 app with Tailwind CSS v4.
- Default backend models are `gemma-4-31b-it` for both worker and critic roles.
- Tests exist, but meaningful unit and frontend coverage remains thin.

## Users

- Developers who need fast accessibility feedback while iterating on UI code.
- QA and accessibility specialists who want structured audit output.
- Platform teams that need to gate releases on critical issues or regressions.

## Scope

### In scope

- Human-approved audits of a local project path.
- Platform detection for iOS, Android, and Web.
- Iterative scanning, evaluation, and follow-up scans.
- Structured findings and score output.
- Local validation of project path before an audit starts.
- Feedback collection from the deployed wrapper.

### Out of scope

- Code fixes or auto-remediation.
- Training users on WCAG theory.
- Full AAA coverage.
- Persistent audit history or findings database.
- A separate frontend router or multi-page app shell.

## Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-1 | The system must validate a local project path before starting an audit. |
| FR-2 | The system must detect the likely target platform from the project contents. |
| FR-3 | The system must scan the codebase using the ADK tool chain and record findings. |
| FR-4 | The system must evaluate audit completeness and run targeted follow-up scans when needed. |
| FR-5 | The system must expose structured audit output to the frontend dashboard. |
| FR-6 | The system must collect feedback through the production FastAPI wrapper. |

## Non-Functional Requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | The local validator must cap directory traversal at 50,000 files. |
| NFR-2 | The agent graph must remain runnable in-memory without external session storage. |
| NFR-3 | The frontend must stream responses from the backend without blocking the UI. |
| NFR-4 | Telemetry must avoid prompt and response content when metadata upload is enabled. |
| NFR-5 | Production deployment must support Cloud Logging and optional GCS artifact storage. |

## Key Product Decisions

| Decision | Rationale |
| --- | --- |
| ADK-based backend | Keeps the agent graph, streaming, and evaluation workflow aligned with Google ADK. |
| Separate validator sidecar | Prevents expensive audits from starting on invalid or mis-targeted paths. |
| FastAPI wrapper around ADK | Adds `POST /feedback`, telemetry, logging, and deployment controls without altering the agent graph. |
| ReadableStream SSE parsing | Matches the current backend stream shape and avoids an EventSource dependency. |
| UI-specific dashboard schema | The frontend dashboard uses its own parsed shape and maps from markdown JSON rather than consuming the backend Pydantic models directly. |

## Success Metrics

- The validator correctly accepts valid local project roots and rejects invalid paths.
- The agent returns structured findings with file, line, severity, and WCAG references.
- The frontend can stream and render an audit without page reloads.
- The production wrapper exposes the ADK app and accepts feedback requests.
- Tests cover more than the current placeholder level for core agent and UI behavior.

## Risks

- The current default model choice changes cost and behavior compared with older docs.
- Frontend and backend audit result schemas are not identical, so documentation must stay explicit about the mapping layer.
- Coverage is still thin, so documentation should not imply production-grade test confidence.

## References

- [System Architecture](./system-architecture.md)
- [Codebase Summary](./codebase-summary.md)
- [Deployment Guide](./deployment-guide.md)
