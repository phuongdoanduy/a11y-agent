# Deployment Guide - epost-a11y-agent

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+
- `uv`
- A Google API key or Google Cloud Application Default Credentials

### Environment

Configure the backend using the environment file under `app/`.

Set one of the following:

- `GOOGLE_API_KEY`
- or Vertex AI credentials via `google.auth.default()`

Optional runtime variables:

- `ALLOW_ORIGINS`
- `LOGS_BUCKET_NAME`
- `COMMIT_SHA`

## Canonical Local Runtime

Use `./run.sh` when you want the full local stack:

```bash
./run.sh
```

This starts:

- Validator sidecar on `http://localhost:8001`
- ADK API server on `http://localhost:8000`

### What each service does

| Service | Endpoint | Purpose |
| --- | --- | --- |
| Validator | `GET /validate?path=...` | Checks that the selected local path is a directory, caps traversal at 50,000 files, and detects likely platform markers. |
| ADK API | ADK session + SSE routes | Runs the `app` agent graph and streams audit output. |

## Frontend Runtime

The frontend runs separately:

```bash
cd frontend
npm install
npm run dev
```

Vite listens on port `3000` and proxies:

- `/api` -> `http://localhost:8000`
- `/util` -> `http://localhost:8001`

Frontend scripts currently defined in `frontend/package.json`:

- `dev`
- `build`
- `preview`

There is no frontend `test` script in the current repository.

## Production Runtime

The Docker image is the production deployment path.

### Build

```bash
docker build -t epost-a11y-agent .
```

### Run

```bash
docker run --rm -p 8080:8080 \
  -e GOOGLE_API_KEY=... \
  -e ALLOW_ORIGINS=https://your-frontend.example \
  -e LOGS_BUCKET_NAME=your-gcs-bucket \
  epost-a11y-agent
```

The container runs:

```bash
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080
```

### Production wrapper behavior

`app.fast_api_app.py`:

- wraps the ADK app
- exposes `POST /feedback`
- enables Cloud Logging
- supports optional GCS artifact storage via `LOGS_BUCKET_NAME`
- applies `ALLOW_ORIGINS` when set
- uses in-memory sessions
- enables cloud telemetry export

## Makefile Targets

| Target | Purpose |
| --- | --- |
| `make install` | Installs Python and frontend dependencies |
| `make dev` | Runs backend and frontend, but not the validator sidecar |
| `make dev-backend` | Starts the ADK API server only |
| `make dev-frontend` | Starts the frontend only |
| `make playground` | Starts the ADK playground on port 8501 |
| `make lint` | Runs the Python lint/type-check toolchain |

## Validator Details

The validator is intentionally lightweight and should stay that way.

- Endpoint: `GET /validate`
- Traversal cap: 50,000 files
- Symlinks are skipped
- Platform heuristics are based on file extensions and project markers, not static analysis

## Deployment Notes

- Use `LOGS_BUCKET_NAME` only when you want telemetry or artifact upload to GCS.
- If you set `ALLOW_ORIGINS`, pass a comma-separated list of allowed origins.
- The production container listens on `8080`; do not publish the ADK or validator ports directly from Docker.
- Keep the frontend and backend schema mapping in mind: the frontend dashboard parses a UI-specific JSON shape from the streamed report.

## Troubleshooting

| Symptom | Likely Cause |
| --- | --- |
| Path validation never enables the audit | The selected path is not a readable directory or contains no detectable platform markers. |
| API requests fail in the browser | The frontend proxy is not reaching port 8000 or 8001. |
| Feedback posts return errors | The production wrapper is not the process serving the request. |
| Telemetry uploads too much data | `NO_CONTENT` mode is not configured. |

## Related Docs

- [System Architecture](./system-architecture.md)
- [Code Standards](./code-standards.md)
- [Project Roadmap](./project-roadmap.md)
