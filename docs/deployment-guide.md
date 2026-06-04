# Deployment Guide — epost-a11y-agent

## Local Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- Git
- Google Cloud Project or Gemini API key

### Backend Setup

1. **Clone and navigate to project:**
   ```bash
   git clone https://github.com/epost/epost-a11y-agent.git
   cd epost-a11y-agent
   ```

2. **Create Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .  # Installs package + dependencies (google-adk, pydantic, etc.)
   pip install -e ".[dev]"  # Also install pytest, pytest-asyncio
   ```

4. **Configure authentication:**
   
   **Option A: Direct Gemini API (Recommended for local dev)**
   ```bash
   cp .env.example app/.env
   # Edit app/.env with your GOOGLE_API_KEY
   # Get key from: https://aistudio.google.com/app/apikey
   ```
   
   **Option B: Vertex AI (Requires Google Cloud Project)**
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   # No .env needed; auto-discovers credentials
   ```

   **⚠️ CRITICAL:** `.env` file **must be in `app/` directory**, not root. The config loader uses `Path(__file__).parent / ".env"`.

5. **Run backend API server:**
   ```bash
   adk api_server --port 8000
   # Should output: "ADK API Server listening on http://localhost:8000"
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   # Should output: "Local:   http://localhost:5173/"
   ```

4. **Verify Vite proxy configuration:**
   The `vite.config.ts` includes:
   ```typescript
   server: {
     proxy: {
       '/api': 'http://localhost:8000',
     },
   },
   ```
   This routes `/api/*` requests to the backend API server.

### Verification

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:5173` (or port 3000 if 5173 taken)
- Try an audit: Type "Audit the web app for WCAG 2.1 AA compliance" in the chat

---

## Authentication Methods

### Method 1: Direct Gemini API Key (Development)

**Pros:** Simplest setup; no Google Cloud project required  
**Cons:** API key in plaintext on disk; less secure for production

**Steps:**
1. Get API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create `app/.env`:
   ```
   GOOGLE_API_KEY=your-api-key-here
   ```
3. `config.py` detects key and sets `GOOGLE_GENAI_USE_VERTEXAI=False`

**Cost:** Per 1M input tokens: $0.075; per 1M output tokens: $0.30 (Gemini 2.5 Pro, as of June 2026)

### Method 2: Vertex AI (Production)

**Pros:** Integrated with Google Cloud; better audit logs; enterprise-ready  
**Cons:** Requires Google Cloud project; slightly more setup

**Steps:**
1. Create Google Cloud project (or use existing)
2. Enable Vertex AI API:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```
3. Authenticate:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
4. No `.env` needed; `config.py` auto-detects and calls `google.auth.default()`

**Cost:** Same as direct API; billed to Google Cloud project

**Note:** If both `GOOGLE_API_KEY` and Vertex AI credentials present, `GOOGLE_API_KEY` takes precedence.

---

## Configuration Options

All configuration in `app/config.py`. Modify `A11yConfiguration` dataclass:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `critic_model` | str | `gemini-2.5-pro` | Model for evaluation + reporting |
| `worker_model` | str | `gemini-2.5-pro` | Model for scanning + analysis |
| `max_audit_iterations` | int | 3 | Max refinement loop passes |
| `compliance_threshold` | int | 85 | Min score to pass audit (0–100) |
| `block_on_critical` | bool | True | Block PR if any critical violation |
| `block_on_regression` | bool | True | Block PR if violation reappears |
| `block_on_serious_count` | int | 5 | Block PR if ≥ this many serious violations |
| `severity_scores` | dict | `{"critical": -10, "serious": -5, "moderate": -2, "minor": -1}` | Points deducted per violation type |
| `wcag_aa_criteria` | list | 25 criteria (1.1.1–4.1.2) | WCAG success criteria to audit |

**To override:** Edit `A11yConfiguration()` instantiation at bottom of `app/config.py`:

```python
config = A11yConfiguration(
    critic_model="gemini-2.5-pro",
    max_audit_iterations=2,  # Faster audits, less thorough
    compliance_threshold=80,  # Lower threshold
)
```

---

## ADK API Server Flags

Run `adk api_server --help` for full options:

| Flag | Default | Use Case |
|------|---------|----------|
| `--port` | 8000 | Change API server port |
| `--host` | 127.0.0.1 | Expose to network (0.0.0.0) for remote access |
| `--log-level` | INFO | Debug: --log-level DEBUG |
| `--timeout-seconds` | 86400 | Session timeout (24 hours) |

**Example: Production setup**
```bash
adk api_server \
  --port 8000 \
  --host 0.0.0.0 \
  --log-level INFO \
  --timeout-seconds 3600  # 1-hour session timeout
```

---

## Frontend Build & Deployment

### Development Build
```bash
cd frontend
npm run dev  # Hot reload, source maps, unminified
```

### Production Build
```bash
cd frontend
npm run build
# Output: frontend/dist/ (static files)
```

### Deployment Options

#### Option 1: Static Hosting (Vercel, Netlify, CloudFront)

```bash
# Build frontend
npm run build

# Deploy dist/ folder to hosting service
# Ensure backend proxy config:
vercel env add API_URL http://your-backend:8000
```

**vite.config.ts for production:**
```typescript
// Use env var for backend URL
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000';
server: {
  proxy: {
    '/api': {
      target: apiUrl,
      changeOrigin: true,
    },
  },
},
```

#### Option 2: Docker Deployment

**Dockerfile (backend):**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENV GOOGLE_CLOUD_PROJECT=${GCP_PROJECT}
EXPOSE 8000
CMD ["adk", "api_server", "--port", "8000", "--host", "0.0.0.0"]
```

**Dockerfile (frontend):**
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend .
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

**nginx.conf (proxy config):**
```nginx
location /api {
  proxy_pass http://backend:8000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection 'upgrade';
  proxy_set_header Host $host;
}
```

#### Option 3: Google Cloud Run

**Backend:**
```bash
gcloud run deploy a11y-agent-backend \
  --source . \
  --runtime python311 \
  --entry-point "python -m google.adk.apps.api_server" \
  --allow-unauthenticated \
  --port 8000
```

**Frontend (on same Cloud Run service):**
```bash
# Deploy frontend to Cloud Storage + Cloud CDN
gsutil -m cp -r frontend/dist/* gs://your-bucket/
gcloud compute backend-buckets create a11y-backend \
  --gcs-bucket-name your-bucket
```

---

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-only

# Run specific test
pytest tests/test_agent.py::test_compute_score_critical_violations

# Run with logging
pytest -s --log-cli-level=DEBUG
```

### Frontend Tests

```bash
cd frontend
npm test  # Runs Vitest
npm run test:ui  # Opens Vitest UI
npm run coverage  # Coverage report
```

---

## Troubleshooting

### Backend Issues

**Error: "No module named 'google.adk'"**
```bash
pip install -e .  # Reinstall package
```

**Error: "GOOGLE_API_KEY not found"**
- Ensure `.env` file is in `app/` directory (not root)
- Check file is readable: `cat app/.env`
- Verify key is valid (copy from [Google AI Studio](https://aistudio.google.com/app/apikey))

**Error: "Module not found: google.auth"**
```bash
pip install google-auth  # Installed as google-adk dependency; may need refresh
```

**Error: "ConnectionRefusedError: [Errno 111] Connection refused"**
- Backend not running on port 8000
- Verify: `curl http://localhost:8000/health` (if health check exists)
- Restart: `adk api_server --port 8000`

**Error: "LoopAgent max iterations reached"**
- Audit didn't converge within 3 iterations (set `max_audit_iterations=5` to allow more)
- May indicate vague audit scope; user should refine request

### Frontend Issues

**Error: "404 Not Found" on API calls**
- Verify backend running: `curl http://localhost:8000/api/...`
- Check Vite proxy config in `vite.config.ts`
- Restart frontend: `npm run dev`

**Error: "Failed to fetch" on SSE stream**
- CORS issue: backend must allow frontend origin
- Check ADK server logs for CORS errors
- If behind proxy: ensure proxy supports SSE (keep connections open)

**Error: "Dashboard not appearing after audit"**
- Check browser console (F12) for JSON parsing errors
- Verify markdown report contains ` ```json ` block with AuditResult
- Try refreshing page

### Authentication Issues

**Error: "The caller does not have permission to access this resource"**
- Vertex AI: Service account doesn't have `aiplatform.user` role
  ```bash
  gcloud projects add-iam-policy-binding YOUR_PROJECT \
    --member=serviceAccount:your-sa@PROJECT.iam.gserviceaccount.com \
    --role=roles/aiplatform.user
  ```

**Error: "403 Unauthenticated" with GOOGLE_API_KEY**
- API key is invalid or expired
- Regenerate at [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## Monitoring & Logs

### Backend Logs

ADK server logs to stdout. Example filtering:

```bash
# Stream logs
adk api_server 2>&1 | tee adk.log

# Filter by agent
cat adk.log | grep "a11y_scanner"

# Filter errors
cat adk.log | grep ERROR
```

### Frontend Logs

Browser DevTools (F12 → Console):
- Network tab: Check `/api/run_sse` requests
- SSE events: `ParsedSSEChunk` objects logged
- Errors: Caught in `sendMessage()` try-catch

### Metrics to Monitor

| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| API latency (p95) | Cloud Trace / APM | > 30 seconds |
| Token usage | Cloud Logging | > 50K tokens/day |
| Error rate | Cloud Logging | > 1% |
| Session timeout | ADK logs | If frequent timeouts |

---

## Production Checklist

- [ ] Backend: Use Vertex AI or encrypted API key (not plaintext `.env`)
- [ ] Backend: Set `--log-level INFO` (not DEBUG)
- [ ] Backend: Configure `--timeout-seconds` based on load (default 24h fine for light load)
- [ ] Frontend: Build with `npm run build` (not dev server)
- [ ] Frontend: Set `VITE_API_URL` env var to backend URL
- [ ] Tests: Run full test suite; all passing
- [ ] Security: No hardcoded secrets in source code
- [ ] HTTPS: Frontend + backend behind HTTPS proxy (TLS for API key in transit)
- [ ] Monitoring: Logs aggregated to central service (Cloud Logging, ELK, Datadog)
- [ ] Rate limiting: Add to API server if exposed publicly
- [ ] CORS: Configure allowed origins in ADK server if cross-origin

---

## Performance Tuning

### Reduce Audit Time
- Lower `max_audit_iterations` (trade: less thorough)
- Use cheaper model: `worker_model="gemini-1.5"` (trade: slightly lower accuracy)
- Narrow audit scope: ask for specific platform/component

### Reduce Token Cost
- Compress chat history before feeding to evaluator
- Cache results by file hash (skip re-audit if unchanged)
- Use `gemini-1.5-flash` for initial scan (fast); `gemini-2.5-pro` for evaluation only

### Improve Reliability
- Increase `max_audit_iterations` to 5 (may converge on borderline cases)
- Add retry logic for transient Gemini API errors
- Use Vertex AI (more reliable than direct API for enterprise)

---

## Security Considerations

1. **API Key Safety**
   - Never commit `app/.env` to version control (add to `.gitignore`)
   - Use encrypted secret management in production (AWS Secrets Manager, GCP Secret Manager)
   - Rotate API keys quarterly

2. **Data Privacy**
   - All codebase data sent to Gemini API for analysis (user responsible for compliance)
   - Session state stored in ADK server memory (cleared on timeout)
   - No findings persisted unless explicitly logged

3. **Network Security**
   - Deploy behind HTTPS reverse proxy (nginx, Cloudflare)
   - Restrict backend to internal network if possible
   - Add authentication layer (OAuth2, JWT) if exposing publicly

4. **Secrets in Codebase**
   - Tools may encounter API keys, database passwords in scanned code
   - No explicit masking implemented (user responsible for `.env` patterns)
   - Consider excluding `.env`, `secrets.yaml`, `credentials.json` files via audit scope
