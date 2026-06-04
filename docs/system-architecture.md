# System Architecture - epost-a11y-agent

## Overview

epost-a11y-agent has three runtime pieces:

| Component | Port | Responsibility |
| --- | --- | --- |
| Frontend | 3000 | React 19 dashboard, path validation UI, and SSE streaming client |
| Validator sidecar | 8001 | Confirms a local project path and detects likely platforms |
| ADK backend / production wrapper | 8000 in local mode, 8080 in Docker | Runs the agent graph, streams events, and exposes feedback/logging endpoints |

## High-Level Flow

```text
User
  -> frontend welcome screen
  -> GET /util/validate?path=...
  -> if valid, POST /api/run_sse
  -> backend streams ADK SSE events
  -> frontend parses stream with fetch + ReadableStream
  -> dashboard renders parsed report JSON
```

## Backend Agent Graph

`app/agent.py` defines `root_agent = interactive_audit_planner` and wraps the graph in an ADK `App(name="app")`.

### Agent chain

1. `interactive_audit_planner`
   - Human-in-the-loop entry point.
   - Uses `AgentTool(scope_analyzer)` to form an audit plan.
2. `scope_analyzer`
   - Builds the scoped audit plan.
   - Tool inputs must include `target_dir` / `root_dir`.
3. `platform_detector`
   - Detects iOS, Android, Web, or cross-platform scope.
4. `a11y_scanner`
   - Runs the main scan with `search_codebase`, `read_file_content`, and `list_files`.
5. `a11y_refinement_loop`
   - `a11y_evaluator` grades audit completeness.
   - `ComplianceChecker` escalates when `audit_evaluation.grade == "pass"`.
   - `targeted_scanner` runs follow-up scans on gaps.
6. `audit_report_composer`
   - Produces the final markdown report and summary JSON block.

### Tooling

| Tool | Limit | Notes |
| --- | --- | --- |
| `search_codebase(pattern, file_glob, root_dir)` | 50 matches | Uses `grep -rn`; callers must pass the project root. |
| `read_file_content(file_path, start_line, end_line)` | No explicit cap | Returns numbered lines for inspection. |
| `list_files(glob_pattern, root_dir)` | 100 files | Used for scoped discovery. |

## Runtime State

The agent uses session state as the contract between agents:

- `audit_plan`
- `audit_checklist`
- `audit_scan_result`
- `audit_evaluation`
- `final_audit_report`

The refinement loop stops early when the compliance checker escalates after a passing evaluation.

## Models and Defaults

`app/config.py` currently defaults both model roles to `gemma-4-31b-it`:

| Role | Default |
| --- | --- |
| Critic | `gemma-4-31b-it` |
| Worker | `gemma-4-31b-it` |

Authentication selection is:

- `GOOGLE_API_KEY` present: direct Gemini API mode.
- Otherwise: Vertex AI via `google.auth.default()`.

## FastAPI Wrapper

`app.fast_api_app.py` wraps the ADK app with `google.adk.cli.fast_api.get_fast_api_app(...)`.

### Responsibilities

- Expose the ADK app for SSE and session APIs.
- Add `POST /feedback` using the `Feedback` model.
- Enable Cloud Logging.
- Pass `ALLOW_ORIGINS` when supplied.
- Configure optional artifact storage from `LOGS_BUCKET_NAME` as a `gs://` URI.
- Keep sessions in memory (`session_service_uri = None`).
- Route OpenTelemetry export to cloud with `otel_to_cloud=True`.

### Production container

The Docker image runs:

```bash
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080
```

## Validator Sidecar

`app/path_validator.py` is intentionally small and synchronous.

### Behavior

- Endpoint: `GET /validate?path=/absolute/path`
- Uses `Path(path).resolve()` before checking the filesystem.
- Rejects missing or non-directory inputs.
- Walks files recursively while skipping symlinks.
- Stops after 50,000 files.
- Detects:
  - `ios` from `.swift`, `.xcodeproj`, `.xcworkspace`
  - `android` from `.kt`, `.kts`, `AndroidManifest.xml`
  - `web` from `.tsx`, `.jsx`, `.html`

## Frontend Architecture

The frontend is a single-page React app. There is no router.

### Key facts

- React 19 + Vite 6 + Tailwind CSS v4.
- Only `dev`, `build`, and `preview` scripts are defined.
- WelcomeScreen validates the path through `/util/validate` before the audit can start.
- App.tsx adds `[TARGET_DIR: ...]` only to the wire payload, not the visible user message.
- Streaming uses fetch plus a streamed reader, not EventSource.
- `frontend/src/lib/utils.ts` contains a UI-specific parsed result shape, so the dashboard schema should not be assumed to match backend Pydantic models field-for-field.

## Data Flow

1. User enters a local path and audit scope.
2. Frontend validates the path through the validator sidecar.
3. Frontend creates or reuses an ADK session on the backend.
4. Frontend posts the scoped audit request to `/api/run_sse`.
5. ADK streams events back as SSE payloads.
6. Frontend accumulates text, tool events, and final report JSON.
7. Dashboard displays the parsed audit result.

## Observability

- Cloud Logging is enabled in the production wrapper.
- Telemetry is configured in `app/app_utils/telemetry.py`.
- When metadata upload is enabled, the system avoids prompt/response content by forcing `NO_CONTENT`.

## Key Constraints

- The runtime is designed around local codebase audits, not remote repositories.
- The validator is a guardrail, not a deep scanner.
- The frontend must remain in sync with backend event shape changes because it parses the stream manually.
