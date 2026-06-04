# Codebase Summary — epost-a11y-agent

## Project Structure

```
epost-a11y-agent/
├── app/                          # Python ADK backend
│   ├── __init__.py
│   ├── config.py                 # Configuration singleton (83 LOC)
│   ├── agent.py                  # ADK agent graph + Pydantic models (633 LOC)
│   └── .env                      # (git-ignored) API key configuration
├── frontend/                      # React + Vite frontend
│   ├── src/
│   │   ├── App.tsx               # Main state container (210 LOC)
│   │   ├── main.tsx              # App entry point
│   │   ├── vite-env.d.ts
│   │   ├── lib/
│   │   │   └── utils.ts          # ADK API client + types (189 LOC)
│   │   └── components/           # 8 reusable components (22–154 LOC each)
│   │       ├── WelcomeScreen.tsx
│   │       ├── ChatMessagesView.tsx
│   │       ├── InputForm.tsx
│   │       ├── ActivityTimeline.tsx
│   │       ├── AuditDashboard.tsx
│   │       ├── FindingsList.tsx
│   │       ├── WCAGMatrix.tsx
│   │       └── SeverityBadge.tsx
│   ├── vite.config.ts
│   ├── package.json
│   ├── tailwind.config.js
│   └── tsconfig.json
├── pyproject.toml                # Python dependencies: google-adk, pydantic, pytest
├── README.md                      # Quick start guide
└── docs/                          # This folder: project documentation
```

## Backend Modules

### `app/config.py` (83 LOC)

**Purpose:** Centralized configuration and auth selection.

**Key Exports:**
- `A11yConfiguration` — dataclass with:
  - Model settings: `critic_model`, `worker_model` (both default to `gemini-2.5-pro`)
  - Iteration control: `max_audit_iterations=3`
  - Scoring: `compliance_threshold=85`, `severity_scores` dict
  - PR blocking: `block_on_critical`, `block_on_serious_count=5`, `block_on_regression`
  - WCAG AA criteria list: 25 standardized criteria (1.1.1–4.1.2)
- `config` — singleton instance

**Auth Logic:**
- If `GOOGLE_API_KEY` env var set → use direct Gemini API
- Else → use Vertex AI with `google.auth.default()` (gcloud credentials)
- `.env` file must be in `app/` directory (not root)

### `app/agent.py` (633 LOC)

**Purpose:** ADK agent graph definition + Pydantic models + tool implementations.

**Pydantic Models:**
| Model | Fields | Usage |
|-------|--------|-------|
| `A11yViolation` | id, wcag_criterion, severity, title, file_path, line_number, description, code_snippet, fix_suggestion, fix_template, platform, regression | Single finding; emitted by scanner agents |
| `AuditResult` | platform, total_violations, critical_count, serious_count, moderate_count, minor_count, score, block_pr, violations[], wcag_criteria_checked[], files_scanned | Scan output; input to evaluator |
| `A11yFeedback` | grade (pass/fail), comment, gaps[], follow_up_scans[] | Evaluator output; controls loop iterations |

**Tools (FunctionTools):**
| Tool | Purpose | Limits |
|------|---------|--------|
| `search_codebase(pattern, file_glob)` | Regex search for a11y patterns | 50-result cap; returns JSON with file paths + line numbers + context |
| `read_file_content(file_path, start_line, end_line)` | Read line range from file | No cap; used for context after search |
| `list_files(glob_pattern)` | Glob files in audit scope | 100-file cap |

**Agent Graph:**
```
interactive_audit_planner (LlmAgent, HITL)
├── AgentTool(scope_analyzer)       → LlmAgent
└── SequentialAgent(a11y_audit_pipeline)
    ├── platform_detector           → LlmAgent (output_key="audit_checklist")
    ├── a11y_scanner                → LlmAgent with BuiltInPlanner(ThinkingConfig)
    ├── a11y_refinement_loop        → LoopAgent (max_iterations=3)
    │   ├── a11y_evaluator          → LlmAgent (output_schema=A11yFeedback)
    │   ├── compliance_checker      → CustomBaseAgent (escalate=True on pass)
    │   └── targeted_scanner        → LlmAgent (re-scans gaps)
    └── audit_report_composer       → LlmAgent (output_key="final_audit_report")
```

**Key ADK Patterns Used:**
- **output_key** — Inter-agent state communication (e.g., `audit_scan_result`, `audit_evaluation`)
- **Callbacks** — `collect_findings_callback()` deduplicates violations; `build_report_callback()` computes score/PR block decision
- **BuiltInPlanner(ThinkingConfig)** — Extended reasoning for scanner agents (internal chain-of-thought)
- **output_schema=A11yFeedback** — Forces evaluator JSON compliance
- **EventActions(escalate=True)** — Breaks LoopAgent early when audit passes
- **include_contents="none"** — Report composer sees only state, not chat history (memory efficiency)

**Scoring Algorithm:**
```python
score = 100
score -= critical_count * 10
score -= serious_count * 5
score -= moderate_count * 2
score -= minor_count * 1
score = max(0, min(100, score))  # clamp 0-100

pr_blocked = (
    (critical_count > 0 and config.block_on_critical) or
    (serious_count >= config.block_on_serious_count) or
    (any(v.regression for v in violations) and config.block_on_regression)
)
complies = score >= config.compliance_threshold and not pr_blocked
```

## Frontend Modules

### `lib/utils.ts` (189 LOC)

**Purpose:** ADK API client + TypeScript interfaces for backend models.

**Key Exports:**

```typescript
// Session management
createSession(userId?, appName?) → { sessionId, userId, appName }

// SSE streaming (async generator)
streamAgentResponse(sessionId, message, userId?, appName?, signal?) → AsyncGenerator<ParsedSSEChunk>

// Parsing
parseAuditReport(text) → AuditResult | null
```

**Interfaces (match Pydantic models):**
- `A11yViolation` (fields match backend exactly)
- `AuditResult` (score, violations[], platform, etc.)
- `ParsedSSEChunk` — union type: `{type: "text" | "tool_call" | "done", content?, data?}`
- `AgentId` — literal union: `"scope_analyzer" | "platform_detector" | ... | "audit_report_composer"`

**API Endpoints Called:**
- `POST /api/apps/{appName}/users/{userId}/sessions/{sessionId}` — create session
- `POST /api/run_sse` — send message, receive SSE stream

**ADK SSE Protocol:**
Lines prefixed `data: ` are parsed as JSON events. Event object has type, content, author, timestamp, metadata fields. `[DONE]` signals stream end.

### `App.tsx` (210 LOC)

**Purpose:** Main state container; orchestrates chat flow and dashboard display.

**State:**
- `sessionId` — Current ADK session
- `messages[]` — Chat history (user/agent messages)
- `isStreaming` — Blocks new messages while streaming
- `activeAgent` — Currently active ADK agent (for ActivityTimeline highlight)
- `agentHistory[]` — Completed agents (for ActivityTimeline status)
- `auditResult` — Parsed AuditResult from streamed JSON
- `showDashboard` — Show AuditDashboard vs. ChatMessagesView

**Key Logic:**
1. `ensureSession()` — lazy-create session on first message
2. `detectAgentFromContent()` — heuristic keyword matching to detect agent from streamed text (not event metadata; ADK SSE doesn't provide agent change events)
3. `sendMessage()` — stream agent response via async generator; collect chunks; detect agent changes; parse JSON blocks for AuditResult; update UI in real time
4. Dashboard activates when streamed text contains ` ```json ` block matching AuditResult schema

**Component Hierarchy:**
```
<App>
  showDashboard ? <AuditDashboard /> : <>
    <ChatMessagesView />
    <InputForm />
  </>
  <ActivityTimeline />  // Always visible
</App>
```

### Components (22–154 LOC each)

| Component | Role | Key Props |
|-----------|------|-----------|
| `WelcomeScreen` | Landing page; scope input; example prompts | `onAudit(scope)` callback |
| `ChatMessagesView` | Renders messages array; markdown formatting; scrolls to latest | `messages`, `isStreaming` |
| `InputForm` | Textarea + Send button; Enter-to-send; Stop button on streaming | `onSend(text)`, `onStop()` |
| `ActivityTimeline` | Shows 6-agent pipeline status (pending/active/completed) | `activeAgent`, `agentHistory` |
| `AuditDashboard` | Score card (0–100) + severity bar chart; filtering UI | `auditResult` |
| `FindingsList` | Filterable table of violations; severity pills; fix suggestions | `violations`, severity/platform filters |
| `WCAGMatrix` | Grid of 25 WCAG AA criteria; color-coded by issue count (0=green, 1-2=yellow, 3+=red) | `violations` |
| `SeverityBadge` | Colored pill (critical=red, serious=orange, moderate=yellow, minor=gray) | `severity` |

## Connection Points (Backend ↔ Frontend)

| Flow | Details |
|------|---------|
| **Session Creation** | Frontend calls `POST /api/apps/{appName}/users/{userId}/sessions/{sessionId}` (ADK REST) |
| **Message Streaming** | Frontend `streamAgentResponse()` → `POST /api/run_sse` → ADK SSE server → async generator |
| **Model Alignment** | Backend Pydantic models exported as TypeScript interfaces in `utils.ts` |
| **AuditResult Parsing** | Backend composes markdown report; frontend extracts ` ```json ` blocks; `parseAuditReport()` validates |
| **Agent Detection** | Frontend heuristic (keyword matching); ADK doesn't expose agent metadata in SSE |

## File Size Summary

| File | LOC | Purpose |
|------|-----|---------|
| `app/agent.py` | 633 | Agent graph + models + tools |
| `app/config.py` | 83 | Configuration + auth |
| `frontend/src/App.tsx` | 210 | State container |
| `frontend/src/lib/utils.ts` | 189 | API client |
| `ActivityTimeline.tsx` | 68 | Agent pipeline UI |
| `FindingsList.tsx` | 154 | Violations table |
| `AuditDashboard.tsx` | 104 | Score + chart |
| `WCAGMatrix.tsx` | 94 | WCAG criteria grid |
| `ChatMessagesView.tsx` | 56 | Chat display |
| `InputForm.tsx` | 56 | Message input |
| `WelcomeScreen.tsx` | 72 | Landing page |
| `SeverityBadge.tsx` | 22 | Severity pill |
| **Total** | **1,741** | |

## Dependencies

**Backend:**
- `google-adk >=1.8.0` — Agent framework, ADK REST + SSE servers
- `pydantic >=2.0.0` — Model validation
- `python-dotenv` — `.env` loading (already in google-adk)

**Frontend:**
- `react 19` — UI framework
- `react-dom 19` — DOM rendering
- `typescript 5.7` — Type safety
- `vite 6` — Build tool
- `tailwind 4` — CSS framework
- `lucide-react` — Icons
- `clsx` + `tailwind-merge` — Class merging

## Key Architectural Decisions

1. **ADK as agent backbone** — Leverages Google's HITL infrastructure, session state, callbacks, tool management
2. **Pydantic + TypeScript alignment** — Ensures type safety across Python/JavaScript boundary
3. **SSE for streaming** — Avoids polling; real-time chat feel; browser-native EventSource
4. **Heuristic agent detection** — ADK SSE doesn't expose agent metadata; frontend uses keyword matching (acceptable for 6-agent pipeline)
5. **Session-based state** — Each session isolated; no cross-session pollution; stateless backend scaling possible
6. **Component over page** — All UI in single React component; no routing; chat-centric UX
7. **Callbacks for side effects** — Score/block decision computed async during agent pipeline; not in frontend
