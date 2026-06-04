# Project Roadmap - epost-a11y-agent

## Current State

The core infrastructure is in place:

- ADK agent graph is implemented.
- Validator sidecar exists.
- FastAPI production wrapper exists.
- Docker deployment is wired.
- Makefile targets are available.
- Telemetry support is implemented.
- Evaluation datasets and integration tests exist.

What is still thin:

- Meaningful unit coverage.
- Frontend component coverage.
- Broader end-to-end regression coverage around the streaming UI and dashboard schema mapping.

## Completed Infrastructure

| Area | Status | Notes |
| --- | --- | --- |
| Validator sidecar | Complete | `GET /validate`, 50k cap, platform heuristics. |
| FastAPI wrapper | Complete | ADK app wrapper plus `POST /feedback`, Cloud Logging, telemetry hooks, optional GCS artifact service, `ALLOW_ORIGINS`. |
| Docker runtime | Complete | Production container runs `uvicorn app.fast_api_app:app` on port `8080`. |
| Makefile | Complete | Install, dev, lint, and playground targets exist. |
| Telemetry | Complete | Metadata upload can be enabled without prompt/response content. |

## Near-Term Roadmap

### 1. Strengthen test coverage

- Add real unit tests for scoring, loop control, and path validation.
- Add frontend tests for the path validation gate, streaming parser, and dashboard state.
- Expand integration tests to cover more request shapes and error paths.

### 2. Tighten schema mapping

- Keep the frontend dashboard schema explicitly documented as UI-specific.
- Add tests or fixtures that confirm the markdown JSON parser stays aligned with backend output.

### 3. Improve observability

- Add clearer logging around validation failures and feedback collection.
- Verify telemetry and logging behavior in deployment environments.

## Medium-Term Roadmap

| Area | Goal | Notes |
| --- | --- | --- |
| Coverage | Replace placeholder unit tests with real assertions | Focus on agent tools, scoring, and parser logic first. |
| Frontend quality | Add component coverage | Target the validation gate, SSE parser, dashboard rendering, and findings list. |
| Runtime hardening | Exercise wrapper and validator together | Validate local and Docker paths end-to-end. |
| Docs hygiene | Keep docs in sync with runtime changes | Update model defaults, ports, and API shapes immediately when they change. |

## Backlog

- Improve audit scoring and report confidence checks.
- Add broader integration scenarios for platform detection.
- Add regression checks for the validator and wrapper behavior.
- Expand evaluation datasets as new project patterns appear.

## Milestones

| Milestone | Status | Exit Criteria |
| --- | --- | --- |
| Infrastructure baseline | Done | Local runtime, wrapper, validator, Docker, and Makefile are documented and usable. |
| Meaningful tests | In progress | Core logic is covered by real unit and integration tests. |
| Frontend coverage | In progress | Main dashboard and stream flows are tested. |
| Production readiness | Pending | Observability and runtime confidence are higher and test gaps are reduced. |

## Notes

- The current repository should be treated as an infrastructure-complete MVP with thin verification.
- Documentation must not overstate test confidence until the coverage gap is closed.
