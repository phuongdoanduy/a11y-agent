# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**epost-a11y-agent** is a multi-platform WCAG 2.1 AA accessibility auditor built on Google ADK (Agent Development Kit). It consists of a Python backend (ADK agent pipeline + validator sidecar) and a React + Vite frontend dashboard.

## Commands

### Install

```bash
make install          # installs Python deps via uv + npm deps for frontend
```

### Backend

```bash
./run.sh              # canonical local dev: starts ADK server (:8000) + validator sidecar (:8001)

make dev              # same as run.sh but via make (backend + frontend concurrently)
make dev-backend      # ADK API server only: uv run adk api_server app --allow_origins="*"
make playground       # ADK web UI on :8501

# Alternative: production FastAPI wrapper (used in Docker/Cloud Run)
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm run dev           # Dev server → http://localhost:3000
npm run build         # TypeScript compile + Vite build
```

### Tests

```bash
uv run pytest                                          # all tests
uv run pytest tests/unit/                             # unit tests only
uv run pytest tests/integration/test_agent.py         # integration: agent stream
uv run pytest tests/integration/test_server_e2e.py    # e2e: starts live server on :8000
uv run pytest tests/path/to/test_file.py::test_func   # single test

# ADK eval (requires eval extras)
uv run adk eval app tests/eval/datasets/basic-dataset.json
```

### Lint

```bash
make lint             # codespell + ruff check + ruff format + mypy
uv run ruff check . --fix
uv run mypy .
```

### Environment Setup

```bash
cp .env.example app/.env
# Set GOOGLE_API_KEY for direct Gemini API access, OR
# Set GOOGLE_GENAI_USE_VERTEXAI=TRUE + GOOGLE_CLOUD_PROJECT for Vertex AI
```

The `.env` file **must** live inside `app/` — `config.py` loads it from `Path(__file__).parent / ".env"`.

## Architecture

### Three-Process Local Stack

```
frontend (3000)
  -> /api   proxy -> ADK FastAPI server (:8000)   [adk api_server / fast_api_app.py]
  -> /util  proxy -> validator sidecar (:8001)     [path_validator.py]
```

- `run.sh` launches both backend processes; `make dev` adds the frontend.
- `app/fast_api_app.py` is the production wrapper (adds `/feedback` endpoint, Cloud Logging, telemetry). Local dev uses `adk api_server app` instead.
- `app/path_validator.py` is a standalone FastAPI service (`GET /validate?path=<abs_path>`) that checks whether a directory exists, counts files (capped at 50k), and detects platforms via file extensions — called by the frontend before starting an expensive LLM audit.

### Backend — Google ADK Agent Pipeline (`app/agent.py`)

```
interactive_audit_planner (LlmAgent) — root agent, HITL: plan → refine → approve
├── AgentTool(scope_analyzer)         — creates structured audit plan
└── sub_agents: [a11y_audit_pipeline] (SequentialAgent)
    ├── platform_detector             → detects ios/android/web, outputs to "audit_checklist"
    ├── a11y_scanner                  → scans codebase, outputs to "audit_scan_result"
    ├── a11y_refinement_loop (LoopAgent, max_iterations=3)
    │   ├── a11y_evaluator            → grades pass/fail, outputs to "audit_evaluation"
    │   ├── ComplianceChecker         → custom BaseAgent; escalates (breaks loop) on pass
    │   └── targeted_scanner          → re-scans gaps, updates "audit_scan_result"
    └── audit_report_composer         → final markdown report, outputs to "final_audit_report"
```

**Key ADK patterns:**

- **`output_key`** — agents communicate via named session state keys; never return values directly.
- **`after_agent_callback`** — `collect_findings_callback` deduplicates violations across passes (keyed by `file_path + wcag_criterion + title`); `build_report_callback` computes final score and injects a summary header.
- **`BuiltInPlanner` + `ThinkingConfig`** — extended reasoning enabled on `a11y_scanner` and `targeted_scanner`.
- **`output_schema=A11yFeedback`** — forces `a11y_evaluator` to emit structured JSON via Pydantic.
- **`EventActions(escalate=True)`** — `ComplianceChecker` yields this to break the `LoopAgent` early.
- **`include_contents="none"`** — set on `audit_report_composer` so it only sees session state, not chat history.
- **`_EvalSequentialAgent` / `_EvalLoopAgent`** — thin wrappers that add `instruction: str = ""` and `tools: list = []` fields required by the ADK eval framework.

### Codebase Scanning Tools

Three `FunctionTool`s power all scanning agents (all accept `root_dir` — agents must always pass it from session state `target_dir`):

- `search_codebase(pattern, file_glob, root_dir)` — `grep -rn` wrapper, returns JSON, capped at 50 results
- `read_file_content(file_path, start_line, end_line)` — line-range reader with `line| content` format
- `list_files(glob_pattern, root_dir)` — `Path.glob` wrapper, capped at 100 files

### Target Directory Injection

The frontend prepends `[TARGET_DIR: <abs_path>]` to every user message. `interactive_audit_planner` strips this prefix, stores the path in session state as `target_dir`, and passes it as `root_dir` to all tool calls. Without it, tools default to `"."` (CWD of the ADK server process).

### Scoring Model

Score starts at 100. Deductions: critical −10, serious −5, moderate −2, minor −1. PR is blocked if: any critical violation, ≥5 serious violations, or any regression. Pass threshold: score ≥ 85. All thresholds are configurable in `app/config.py` via `A11yConfiguration`.

### Frontend — React + Vite (`frontend/src/`)

`App.tsx` is the single state container. All API calls use the ADK REST API at `/api` (proxied to `:8000`). `WelcomeScreen.tsx` calls `/util/validate` before the user starts an audit.

**Session flow:**
1. `createSession()` — `POST /api/apps/app/users/u_999/sessions/{id}`
2. `streamAgentResponse()` — `POST /api/run_sse` with SSE streaming
3. SSE chunks parsed in `parseADKEvent()` — handles text parts, tool calls, and tool results

**Agent detection** is heuristic: `App.tsx` watches streaming text for keywords ("scanning", "platform detect", etc.) to update `ActivityTimeline` — not driven by ADK event metadata.

**Dashboard** (`AuditDashboard.tsx`) activates only when the agent emits a `` ```json `` block parseable by `parseAuditReport()`, expecting shape: `score`, `findings[]`, `severityBreakdown`, `wcagCoverage`.

### Configuration (`app/config.py`)

`A11yConfiguration` dataclass → singleton `config`. Models default to `gemma-4-31b-it` for both `critic_model` and `worker_model`. Auth auto-selects: `GOOGLE_API_KEY` → direct Gemini API; otherwise → Vertex AI via `google.auth.default()`.

### Eval Datasets (`tests/eval/datasets/`)

- `basic-dataset.json` — quick smoke tests
- `full-pipeline-dataset.json` — end-to-end pipeline coverage

Run with: `uv run adk eval app tests/eval/datasets/<file>.json` (requires `pip install -e ".[eval]"` or `uv sync --extra eval`).
