# Codebase Summary - epost-a11y-agent

## Repository at a Glance

```text
epost-a11y-agent/
├── app/
│   ├── agent.py
│   ├── config.py
│   ├── fast_api_app.py
│   ├── path_validator.py
│   └── app_utils/
│       ├── telemetry.py
│       └── typing.py
├── frontend/
│   ├── src/App.tsx
│   ├── src/lib/utils.ts
│   ├── src/components/
│   ├── vite.config.ts
│   └── package.json
├── tests/
│   ├── integration/
│   ├── unit/
│   └── eval/
├── Dockerfile
├── Makefile
├── run.sh
├── pyproject.toml
└── agents-cli-manifest.yaml
```

## Backend Modules

| File | Role | Notes |
| --- | --- | --- |
| `app/agent.py` | ADK agent graph, structured models, and codebase scanning tools | Defines `root_agent = interactive_audit_planner`; uses `scope_analyzer`, `platform_detector`, `a11y_scanner`, `a11y_evaluator`, `targeted_scanner`, and `audit_report_composer`. Tool helpers cap search results at 50 and file listings at 100. |
| `app/config.py` | Auth selection and runtime configuration | Reads the environment file under `app/`; uses `GOOGLE_API_KEY` when present, otherwise `google.auth.default()`. Default `critic_model` and `worker_model` are `gemma-4-31b-it`. |
| `app/fast_api_app.py` | Production FastAPI wrapper around ADK | Wraps the ADK app, enables telemetry, Cloud Logging, optional GCS artifact service, `ALLOW_ORIGINS`, in-memory sessions, and `POST /feedback`. |
| `app/path_validator.py` | Local project validation sidecar | Serves `GET /validate?path=...`, resolves paths, ignores symlinks, caps traversal at 50,000 files, and detects iOS/Android/Web markers. |
| `app/app_utils/telemetry.py` | GenAI telemetry configuration | Switches metadata upload on when `LOGS_BUCKET_NAME` is set and content capture is enabled; forces `NO_CONTENT` mode so prompt/response bodies are not uploaded. |
| `app/app_utils/typing.py` | Shared FastAPI models | Defines the `Feedback` payload used by `POST /feedback`. |

## Frontend Modules

| File | Role | Notes |
| --- | --- | --- |
| `frontend/src/App.tsx` | Top-level UI state container | Manages session creation, SSE streaming, audit display, and the validator-gated start flow. It prepends `[TARGET_DIR: ...]` only in the wire payload. |
| `frontend/src/lib/utils.ts` | API client, SSE parser, and UI-facing types | Uses fetch with a streamed reader for SSE; EventSource is not used. The frontend `AuditResult` shape is UI-specific and does not mirror the backend Pydantic models exactly. |
| `frontend/src/components/WelcomeScreen.tsx` | Landing screen | Calls `/util/validate` before enabling the audit flow. |
| `frontend/src/components/*.tsx` | Chat, timeline, dashboard, findings, matrix, and severity UI | Single-page app with no router. |
| `frontend/vite.config.ts` | Vite dev server and proxies | Serves the app on port 3000 and proxies `/api` to port 8000 and `/util` to port 8001. |
| `frontend/package.json` | Frontend scripts and dependencies | Scripts are `dev`, `build`, and `preview` only. |

## Frontend Stack

- React 19
- React DOM 19
- Vite 6
- TypeScript 5.7
- Tailwind CSS v4 through `@tailwindcss/vite`
- `lucide-react`, `clsx`, `tailwind-merge`

## Test and Evaluation Assets

| Path | Purpose |
| --- | --- |
| `tests/integration/test_agent.py` | Direct ADK runner streaming integration test. |
| `tests/integration/test_server_e2e.py` | End-to-end FastAPI wrapper test covering SSE, invalid payload handling, and `/feedback`. |
| `tests/unit/test_dummy.py` | Placeholder unit test module. |
| `tests/eval/eval_config.yaml` | Evaluation metric configuration. |
| `tests/eval/datasets/*.json` | Evaluation datasets for ADK eval runs. |

## Build and Runtime Files

| File | Role |
| --- | --- |
| `run.sh` | Starts the validator on `8001` and ADK API server on `8000`. |
| Makefile | `install`, `dev`, `dev-backend`, `dev-frontend`, `playground`, and `lint` targets. |
| Dockerfile | Production container that runs `uvicorn app.fast_api_app:app` on port `8080`. |
| `pyproject.toml` | Python package metadata, dependencies, linting, and pytest settings. |
| `agents-cli-manifest.yaml` | Agents CLI manifest for the `app` agent directory. |

## Important Boundaries

- The backend agent graph and the production FastAPI wrapper are separate concerns.
- The frontend dashboard does not consume the backend Pydantic audit schema directly; the parseAuditReport helper maps markdown JSON into a UI-specific structure.
- The validator sidecar is intentionally lightweight and only confirms path validity plus platform heuristics before the audit starts.

## Current Gaps

- Unit coverage is minimal.
- Frontend behavior is not covered by a dedicated test suite yet.
- The codebase still relies on an in-memory ADK session model for runtime state.
