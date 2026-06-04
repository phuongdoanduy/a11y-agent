# epost-a11y-agent

Multi-platform WCAG 2.1 AA accessibility auditor built on Google ADK. The repo contains a Python agent backend, a React 19 + Vite 6 dashboard, and a local validator sidecar used to confirm a project path before an audit starts.

## What it does

- Audits iOS, Android, and Web codebases for accessibility issues.
- Uses a human-in-the-loop agent pipeline: plan, detect platform, scan, evaluate, refine, and report.
- Streams agent output to the frontend over SSE.
- Validates local project paths before the audit begins.

## Architecture

```text
frontend (3000)
  -> /api      -> ADK FastAPI wrapper on 8000
  -> /util     -> validator sidecar on 8001

backend
  app.agent.py        -> ADK agent graph
  app.fast_api_app.py -> FastAPI wrapper + /feedback
  app.path_validator.py -> GET /validate
```

## Quick Start

```bash
# configure the backend environment file under app/
./run.sh
```

- Validator starts on `http://localhost:8001`
- ADK API starts on `http://localhost:8000`
- Frontend starts separately from `frontend/`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite runs on `http://localhost:3000` and proxies:

- `/api` -> `http://localhost:8000`
- `/util` -> `http://localhost:8001`

## Runtime Notes

- `./run.sh` is the canonical local runtime. It starts `uvicorn app.path_validator:app --port 8001` and `adk api_server app --port 8000`.
- The validator exposes `GET /validate?path=/abs/path`, caps traversal at 50,000 files, and detects `ios`, `android`, and `web` using file extensions and project markers.
- The backend wrapper in `app.fast_api_app.py` exposes the ADK app plus `POST /feedback`.
- Production Docker runs `uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080`.

## Configuration

The backend reads the environment file under `app/` and auto-selects auth:

- `GOOGLE_API_KEY` present: direct Gemini API mode.
- Otherwise: `google.auth.default()` with Vertex AI settings.

Current model defaults in `app/config.py`:

| Setting | Default |
| --- | --- |
| `critic_model` | `gemma-4-31b-it` |
| `worker_model` | `gemma-4-31b-it` |
| `max_audit_iterations` | `3` |
| `compliance_threshold` | `85` |

## Build and Run

```bash
make install
make lint
uv run pytest
```

Useful commands:

- `make dev` starts backend + frontend, but not the validator sidecar.
- `make playground` opens the ADK playground on port `8501`.
- `npm --prefix frontend run build` creates the production frontend bundle.

## Tests

The repository includes integration tests, evaluation datasets, and a placeholder unit test module under `tests/`. Coverage is still thin around core agent logic and frontend behavior.

## Docs

- [Project Overview & PDR](./docs/project-overview-pdr.md)
- [Codebase Summary](./docs/codebase-summary.md)
- [System Architecture](./docs/system-architecture.md)
- [Deployment Guide](./docs/deployment-guide.md)
- [Code Standards](./docs/code-standards.md)
- [Project Roadmap](./docs/project-roadmap.md)

## License

MIT
