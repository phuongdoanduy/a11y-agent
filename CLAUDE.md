# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**epost-a11y-agent** is a multi-platform WCAG 2.1 AA accessibility auditor built on Google ADK (Agent Development Kit). It consists of a Python backend (ADK agent pipeline) and a React + Vite frontend dashboard.

## Commands

### Backend (Python ADK)

```bash
# Install (from repo root)
pip install -e .

# Run the ADK API server (required for frontend)
adk api_server --port 8000

# Run tests
pytest

# Run a single test
pytest tests/path/to/test_file.py::test_function_name
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev      # Dev server → http://localhost:3000 (proxies /api → localhost:8000)
npm run build    # TypeScript compile + Vite build
npm run preview  # Preview production build
```

### Environment Setup

```bash
cp .env.example .env
# Add GOOGLE_API_KEY for direct Gemini API access, OR
# Set GOOGLE_GENAI_USE_VERTEXAI=TRUE + GOOGLE_CLOUD_PROJECT for Vertex AI
```

The `.env` file must be placed inside `app/` — `config.py` loads it from `Path(__file__).parent / ".env"`. Copy `.env.example` there accordingly.

## Architecture

### Backend — Google ADK Agent Pipeline

`app/agent.py` defines a 6-agent pipeline orchestrated by ADK primitives:

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

**Key ADK patterns used:**

- **`output_key`** — agents communicate by writing to named session state keys. Never pass data through return values.
- **`after_agent_callback`** — `collect_findings_callback` deduplicates violations across scan passes; `build_report_callback` computes final score and injects summary header.
- **`BuiltInPlanner` with `ThinkingConfig`** — enabled on `a11y_scanner` and `targeted_scanner` for extended reasoning.
- **`output_schema`** — `a11y_evaluator` uses `A11yFeedback` (Pydantic) to force structured JSON output.
- **`EventActions(escalate=True)`** — `ComplianceChecker` yields this to break the `LoopAgent` early.
- **`include_contents="none"`** — set on `audit_report_composer` to prevent it from seeing raw chat history.

### Codebase Scanning Tools

Three `FunctionTool`s power all scanning agents:
- `search_codebase(pattern, file_glob)` — `grep -rn` wrapper, returns JSON with file/line/content, capped at 50 results
- `read_file_content(file_path, start_line, end_line)` — line-range reader
- `list_files(glob_pattern)` — `Path.glob` wrapper, capped at 100 files

### Scoring Model

Score starts at 100. Each violation deducts: critical −10, serious −5, moderate −2, minor −1. PR is blocked if: any critical violation, ≥5 serious violations, or any regression. Threshold for pass: score ≥ 85 (configurable in `app/config.py`).

### Frontend — React + Vite

`frontend/src/App.tsx` is the single state container. All API calls use the ADK REST API at `/api` (proxied to `localhost:8000`).

**Session flow:**
1. `createSession()` — `POST /api/apps/app/users/u_999/sessions/{id}`
2. `streamAgentResponse()` — `POST /api/run_sse` with SSE streaming
3. SSE chunks are parsed in `parseADKEvent()` — text parts, tool calls, tool results all flow through here

**Agent detection** is heuristic: `App.tsx` watches streaming text for keywords ("scanning", "platform detect", etc.) to update `ActivityTimeline`. It is not driven by ADK event metadata.

**Dashboard** (`AuditDashboard`) activates only if the agent emits a ````json` block parseable by `parseAuditReport()`. The frontend expects a specific JSON shape (`score`, `findings[]`, `severityBreakdown`, `wcagCoverage`).

**Vite proxy:** `/api` → `http://localhost:8000` (configured in `vite.config.ts`). Frontend dev port is **3000** (not 5173).

### Configuration (`app/config.py`)

`A11yConfiguration` dataclass is instantiated as the singleton `config`. Auth is auto-selected: if `GOOGLE_API_KEY` is set → direct Gemini API; otherwise → Vertex AI using `google.auth.default()`.
