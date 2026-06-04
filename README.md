# epost-a11y-agent

Multi-platform WCAG 2.1 AA accessibility auditor built on **Google ADK** (Agent Development Kit).

Architecture inspired by [google/adk-samples/deep-search](https://github.com/google/adk-samples/tree/main/python/agents/deep-search) — adapted from research pipeline to accessibility audit pipeline.

## Architecture

```
interactive_audit_planner (LlmAgent) — HITL: plan → refine → approve
├── tools: [AgentTool(scope_analyzer)]
└── sub_agents: [a11y_audit_pipeline] (SequentialAgent)
    ├── platform_detector          → detect platform, load checklist
    ├── a11y_scanner               → scan codebase for violations
    ├── a11y_refinement_loop       (LoopAgent, max 3 iterations)
    │   ├── a11y_evaluator         → grade pass/fail + gaps
    │   ├── ComplianceChecker      → break loop if pass (custom BaseAgent)
    │   └── targeted_scanner       → follow-up scans on gaps
    └── audit_report_composer      → final WCAG report with findings
```

### Deep-Search → A11y Mapping

| Deep-Search Agent | A11y Agent | Role |
|---|---|---|
| `plan_generator` | `scope_analyzer` | Create audit plan from request |
| `section_planner` | `platform_detector` | Detect platform, build checklist |
| `section_researcher` | `a11y_scanner` | Scan codebase for violations |
| `research_evaluator` | `a11y_evaluator` | Grade audit quality |
| `EscalationChecker` | `ComplianceChecker` | Break loop on pass |
| `enhanced_search_executor` | `targeted_scanner` | Follow-up gap scans |
| `report_composer` | `audit_report_composer` | Final report with findings |
| `google_search` | `codebase_search` | grep/file-glob tools |

### Key Design Patterns (from deep-search)

1. **Human-in-the-Loop Planning** — User approves audit scope before scanning begins
2. **Iterative Refinement Loop** — Evaluator grades → ComplianceChecker breaks or continues → targeted scanner fills gaps
3. **State-Based Communication** — Agents communicate via `output_key` (session state)
4. **Callbacks for Side Effects** — `collect_findings_callback` deduplicates, `build_report_callback` computes scores
5. **Structured Output (Pydantic)** — `A11yFeedback` schema forces evaluator to output structured JSON
6. **Custom BaseAgent** — `ComplianceChecker` yields `Event(escalate=True)` to break loop

## Quick Start

### Backend (Python ADK)

```bash
cd epost-a11y-agent
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY

# Run API server
adk api_server --port 8000
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev    # → http://localhost:5173
```

Frontend proxies `/api` → `localhost:8000` (ADK API server).

## Frontend Components

| Component | Description |
|---|---|
| `WelcomeScreen` | Landing page with audit scope input + example prompts |
| `ChatMessagesView` | Chat interface with markdown rendering |
| `InputForm` | Textarea with Enter-to-send, Stop button |
| `ActivityTimeline` | 6-agent pipeline with active/completed/pending states |
| `AuditDashboard` | Score card (0-100), severity breakdown bar chart |
| `FindingsList` | Filterable findings (severity, platform, WCAG) with fix suggestions |
| `WCAGMatrix` | Grid of WCAG 2.1 AA criteria color-coded by issue count |
| `SeverityBadge` | Color-coded severity pills |

## Usage

```
# Audit iOS app
> Audit the iOS app for WCAG 2.1 AA compliance

# Fix specific violation
> Fix violation a11y-003: missing accessibilityLabel on login button

# Review compliance
> Review web accessibility for the checkout flow
```

## Configuration

See `app/config.py`:

| Setting | Default | Description |
|---|---|---|
| `critic_model` | gemini-2.5-pro | Model for evaluation |
| `worker_model` | gemini-2.5-pro | Model for scanning |
| `max_audit_iterations` | 3 | Max refinement passes |
| `compliance_threshold` | 85 | Min score to pass |
| `block_on_critical` | True | Block PR on critical violations |
| `block_on_regression` | True | Block PR on regressions |
| `block_on_serious_count` | 5 | Block PR if >= 5 serious |

## License

MIT
