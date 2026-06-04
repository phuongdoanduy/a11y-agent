# System Architecture — epost-a11y-agent

## High-Level Overview

epost-a11y-agent is a **multi-agent accessibility audit system** built on Google ADK (Agent Development Kit). It implements a **human-in-the-loop, iteratively-refined audit pipeline** that scans codebases for WCAG 2.1 AA violations across iOS, Android, and Web platforms.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend (Port 3000)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  ChatUI      │  │  AuditResult │  │  ActivityTimeline│  │
│  │  Input Form  │  │  Dashboard   │  │  (Agent Status)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│            │ /api/run_sse (POST + SSE)  │                   │
└─────────────────────────────────────────────────────────────┘
                        │ streams JSON events
                        ↓
┌─────────────────────────────────────────────────────────────┐
│         ADK API Server (Port 8000) + Agent Graph            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  interactive_audit_planner (LlmAgent - HITL root)   │  │
│  │  "Plan the audit scope before scanning"             │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │ AgentTool                           │
│                        ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  scope_analyzer (LlmAgent)                           │  │
│  │  "Create structured audit plan from user request"   │  │
│  │  output_key = "audit_plan"                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │ (SequentialAgent)                   │
│                        ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  a11y_audit_pipeline (SequentialAgent)              │  │
│  │                                                      │  │
│  │  ├─→ platform_detector (LlmAgent)                   │  │
│  │  │   output_key = "audit_checklist"                 │  │
│  │  │                                                  │  │
│  │  ├─→ a11y_scanner (LlmAgent)                        │  │
│  │  │   BuiltInPlanner(ThinkingConfig)                 │  │
│  │  │   output_key = "audit_scan_result"               │  │
│  │  │                                                  │  │
│  │  ├─→ a11y_refinement_loop (LoopAgent, max=3)       │  │
│  │  │   │                                              │  │
│  │  │   ├─→ a11y_evaluator (LlmAgent)                  │  │
│  │  │   │   output_schema = A11yFeedback              │  │
│  │  │   │   output_key = "audit_evaluation"            │  │
│  │  │   │                                              │  │
│  │  │   ├─→ compliance_checker (CustomBaseAgent)       │  │
│  │  │   │   if grade == "pass" → escalate=True         │  │
│  │  │   │   (breaks loop early)                        │  │
│  │  │   │                                              │  │
│  │  │   └─→ targeted_scanner (LlmAgent)                │  │
│  │  │       re-scans gaps identified by evaluator      │  │
│  │  │       updates output_key = "audit_scan_result"   │  │
│  │  │                                                  │  │
│  │  └─→ audit_report_composer (LlmAgent)               │  │
│  │      generates final WCAG markdown report           │  │
│  │      output_key = "final_audit_report"              │  │
│  │                                                      │  │
│  │  Callbacks:                                          │  │
│  │  - collect_findings_callback() → deduplicates       │  │
│  │  - build_report_callback() → computes score/block   │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │ tools                               │
│                        ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FunctionTools (Codebase Scanning)                  │  │
│  │  ├─ search_codebase(pattern, file_glob)             │  │
│  │  ├─ read_file_content(path, start, end)             │  │
│  │  └─ list_files(glob_pattern)                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │ calls                               │
│                        ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Audit Scope (Local Codebase)                       │  │
│  │  iOS, Android, Web files scanned via grep/glob      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Agent Graph Details

### Agent Taxonomy

| Agent | Type | Role | Input | Output | Model |
|-------|------|------|-------|--------|-------|
| `interactive_audit_planner` | LlmAgent | HITL root; plans audit scope | User message | `audit_plan` state key | critic_model |
| `scope_analyzer` | LlmAgent | Creates structured audit plan | `audit_plan` | `audit_plan` state | worker_model |
| `platform_detector` | LlmAgent | Detects platform; loads WCAG checklist | `audit_plan` | `audit_checklist` state | worker_model |
| `a11y_scanner` | LlmAgent | Scans codebase; emits violations | `audit_checklist` + tools | `audit_scan_result` state | worker_model |
| `a11y_evaluator` | LlmAgent | Grades scan quality; identifies gaps | `audit_scan_result` | `audit_evaluation` (A11yFeedback) | critic_model |
| `compliance_checker` | CustomBaseAgent | Checks if audit passes; breaks loop | `audit_evaluation` | escalate=True if pass | — |
| `targeted_scanner` | LlmAgent | Re-scans identified gaps | `audit_scan_result` + gaps | `audit_scan_result` (updated) | worker_model |
| `audit_report_composer` | LlmAgent | Generates final WCAG report | `audit_scan_result` | `final_audit_report` (markdown) | critic_model |

### Session State Flow

All inter-agent communication flows through **session state** (immutable key-value store). Each agent writes to specific `output_key`:

```
Session State:
├─ audit_plan (string)
│  └─ scope_analyzer writes after planning
├─ audit_checklist (string)
│  └─ platform_detector writes WCAG checklist
├─ audit_scan_result (AuditResult - Pydantic)
│  ├─ a11y_scanner writes initial findings
│  └─ targeted_scanner updates with follow-up scans
├─ audit_evaluation (A11yFeedback - Pydantic)
│  └─ a11y_evaluator writes grade + gaps
├─ final_audit_report (string)
│  └─ audit_report_composer writes markdown report
└─ compliance_status (bool, implicit)
   └─ compliance_checker reads audit_evaluation.grade
```

### Iterative Refinement Loop (LoopAgent)

```
Loop Control:
  max_iterations = config.max_audit_iterations (default: 3)
  exit condition:
    if audit_evaluation.grade == "pass" AND no regressions:
      compliance_checker → EventActions(escalate=True)
      break loop
    else:
      continue loop

Iteration Flow:
  1. a11y_evaluator grades previous scan
     ├─ reads audit_scan_result
     ├─ outputs A11yFeedback (grade, comment, gaps, follow_up_scans)
     └─ updates output_key="audit_evaluation"
  
  2. compliance_checker checks if pass
     ├─ reads audit_evaluation.grade
     ├─ if "pass" → escalate=True (break loop early)
     └─ else → continue to targeted_scanner
  
  3. targeted_scanner performs follow-up scans
     ├─ reads gaps and follow_up_scans from audit_evaluation
     ├─ calls tools: search_codebase(), read_file_content()
     ├─ merges new findings with previous audit_scan_result
     └─ updates output_key="audit_scan_result"
```

## ADK Design Patterns in Use

### 1. output_key (State-Based Communication)

All inter-agent communication via immutable session state keys. Agents don't call each other; they read/write state:

```python
# Scanner agent writes findings
result = AuditResult(
    platform="ios",
    violations=[...],
    score=72,
    block_pr=True,
)
context.set_output_key("audit_scan_result", result.model_dump())

# Evaluator agent reads findings
scan_result = context.get_output_key("audit_scan_result")
audit_result = AuditResult(**scan_result)
feedback = A11yFeedback(grade="fail", gaps=[...])
context.set_output_key("audit_evaluation", feedback.model_dump())
```

**Benefit:** Agents are loosely coupled; output_key acts as contract; supports easy history/audit trail.

### 2. Callbacks for Side Effects

Callbacks execute **after** agent completes; used for scoring and report finalization:

```python
def collect_findings_callback(context: CallbackContext):
    """Deduplicates violations across iterations."""
    scan_result = context.get_output_key("audit_scan_result")
    violations = scan_result.get("violations", [])
    # Deduplicate by (wcag_criterion, file_path, line_number)
    unique = {}
    for v in violations:
        key = (v["wcag_criterion"], v["file_path"], v.get("line_number"))
        if key not in unique:
            unique[key] = v
    context.set_output_key("audit_scan_result", {
        **scan_result,
        "violations": list(unique.values())
    })

def build_report_callback(context: CallbackContext):
    """Computes score and PR block decision."""
    scan_result = context.get_output_key("audit_scan_result")
    score = compute_score(scan_result["violations"])
    block_pr = should_block_pr(scan_result["violations"], config)
    context.set_output_key("audit_scan_result", {
        **scan_result,
        "score": score,
        "block_pr": block_pr,
    })
```

**Benefit:** Decouples scoring logic from agent prompts; auditable; reusable across agents.

### 3. BuiltInPlanner (Extended Reasoning)

Scanner agents use `BuiltInPlanner(ThinkingConfig)` for chain-of-thought reasoning:

```python
a11y_scanner = LlmAgent(
    name="a11y_scanner",
    instructions="Scan codebase for WCAG violations...",
    model=config.worker_model,
    planner=BuiltInPlanner(
        ThinkingConfig(
            type="enabled",
            budget_tokens=8000,  # internal reasoning token budget
        )
    ),
    tools=[search_codebase, read_file_content, list_files],
)
```

**Benefit:** Model uses internal chain-of-thought before tool calls; more thorough analysis; better findings quality.

### 4. output_schema (Structured Output)

Evaluator agent forced to emit structured JSON via Pydantic schema:

```python
a11y_evaluator = LlmAgent(
    name="a11y_evaluator",
    instructions="Evaluate audit quality...",
    model=config.critic_model,
    output_schema=A11yFeedback,  # Pydantic model
)
```

**ADK automatically:**
- Appends schema definition to system prompt
- Parses response JSON
- Validates against Pydantic model
- Retries on validation failure

**Benefit:** Guarantees evaluator output matches LoopAgent expectations; eliminates parsing errors.

### 5. EventActions(escalate=True)

Custom compliance_checker agent breaks loop early:

```python
class ComplianceChecker(BaseAgent):
    async def run(self, context: InvocationContext):
        evaluation = context.get_output_key("audit_evaluation")
        if evaluation["grade"] == "pass":
            yield Event(actions=EventActions(escalate=True))
            return
        # else: fall through (loop continues)
```

**Benefit:** Breaks LoopAgent without max iterations; saves tokens/latency when audit passes early.

### 6. include_contents="none"

Report composer sees **only** session state, not chat history:

```python
audit_report_composer = LlmAgent(
    name="audit_report_composer",
    instructions="Compose final WCAG report from audit state...",
    model=config.critic_model,
    include_contents="none",  # Don't include message history
)
```

**Benefit:** Memory efficient; report logic doesn't depend on conversation history; repeatable outputs.

## Scoring Algorithm

```python
def compute_score(violations: list[A11yViolation]) -> int:
    """Score 0-100; higher is better."""
    score = 100
    for v in violations:
        if not v.regression:  # Don't double-penalize regressions
            score -= config.severity_scores.get(v.severity, 0)
    return max(0, min(100, score))

def should_block_pr(violations: list[A11yViolation]) -> bool:
    """True if PR should be blocked."""
    critical_count = sum(1 for v in violations if v.severity == "critical")
    serious_count = sum(1 for v in violations if v.severity == "serious")
    has_regression = any(v.regression for v in violations)
    
    return (
        (critical_count > 0 and config.block_on_critical) or
        (serious_count >= config.block_on_serious_count) or
        (has_regression and config.block_on_regression)
    )

def compliance_passed(score: int, block_pr: bool) -> bool:
    """True if audit passes WCAG AA."""
    return score >= config.compliance_threshold and not block_pr
```

### Scoring Example

**Input:** 1 critical, 3 serious, 2 moderate violations

```
score = 100
score -= 1 * 10 = 90
score -= 3 * 5 = 75
score -= 2 * 2 = 71
```

**Output:** score=71, block_pr=True (critical violation), passes=False

## Tool Architecture

### FunctionTools

Three tools available to all agents:

#### 1. search_codebase(pattern: str, file_glob: str = "*") → str

**Purpose:** Find accessibility-related patterns in files.

```python
def search_codebase(pattern: str, file_glob: str = "*") -> str:
    """
    Args:
        pattern: Regex pattern (e.g., r"accessibility|a11y|aria")
        file_glob: File glob filter (e.g., "*.swift", "*.tsx")
    
    Returns:
        JSON string with matches: [{"file": path, "line": num, "content": text}, ...]
    
    Limits:
        - 50-result cap per call
        - Returns line number and context window (3 lines before/after)
    """
```

#### 2. read_file_content(file_path: str, start_line: int | None = None, end_line: int | None = None) → str

**Purpose:** Read line ranges from files (for context after search).

```python
def read_file_content(file_path: str, start_line: int = None, end_line: int = None) -> str:
    """
    Args:
        file_path: Path relative to audit scope
        start_line: Starting line (1-indexed); default: 1
        end_line: Ending line (inclusive); default: EOF
    
    Returns:
        File content as string with line numbers
    
    Limits:
        - No cap; but model context limited to ~8K tokens per tool response
    """
```

#### 3. list_files(glob_pattern: str) → str

**Purpose:** Discover files matching glob.

```python
def list_files(glob_pattern: str) -> str:
    """
    Args:
        glob_pattern: Glob pattern (e.g., "src/**/*.tsx", "app/**/*.swift")
    
    Returns:
        JSON string: ["file1.tsx", "file2.tsx", ...]
    
    Limits:
        - 100-file cap per call
    """
```

## Frontend-Backend Integration

### Session Creation Flow

```
Frontend                           Backend
────────────────────────────────────────────

User clicks "Audit" →
                      POST /api/apps/{app}/users/{user}/sessions/{id}
                      ├─ Creates ADK session
                      └─ Returns 200 OK
← response ←

store sessionId
```

### Message Streaming Flow

```
Frontend                           Backend (ADK)
────────────────────────────────────────────────

User sends message →
                      POST /api/run_sse
                      {
                        "app_name": "app",
                        "user_id": "u_999",
                        "session_id": "<sessionId>",
                        "new_message": {
                          "role": "user",
                          "parts": [{"text": "..."}]
                        }
                      }
                      ├─ Route to interactive_audit_planner
                      ├─ Execute agent graph
                      ├─ Stream events via SSE
                      └─ Keep connection open

← "data: {...}" (SSE events) ←

async generator yields
ParsedSSEChunk objects
```

### AuditResult Extraction

Backend's audit_report_composer outputs markdown report. Report includes JSON block:

```markdown
# Final WCAG 2.1 AA Audit Report
...
## Findings

```json
{
  "platform": "web",
  "score": 71,
  "violations": [...],
  "block_pr": true
}
```

...
```

Frontend's `parseAuditReport()` extracts the JSON block and hydrates AuditResult object. Dashboard then displays score, findings, WCAG matrix.

## Configuration & Auth

### Authentication

`app/config.py` implements auto-selection:

```python
if os.getenv("GOOGLE_API_KEY"):
    # Direct Gemini API
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
else:
    # Vertex AI (requires gcloud auth)
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
```

**`.env` placement:** Must be in `app/` directory (not root), because `config.py` loads via `Path(__file__).parent / ".env"`.

### Configuration Singleton

```python
config = A11yConfiguration(
    critic_model="gemini-2.5-pro",
    worker_model="gemini-2.5-pro",
    max_audit_iterations=3,
    compliance_threshold=85,
    block_on_critical=True,
    block_on_regression=True,
    block_on_serious_count=5,
)
```

All agents reference global `config` instance. No per-request overrides.

## Scalability & Deployment

### Stateless Backend

- Each session isolated; no shared state between sessions
- ADK API server is stateless; can run multiple instances behind load balancer
- Sessions expire after timeout (ADK default: 24 hours)

### Frontend Deployment

- Static site; React + Vite compiled to `/frontend/dist/`
- Can be served from CDN or static hosting
- Single `/api` proxy route to backend ADK server

### Production Considerations

- **Rate limiting** — Add to ADK API server to prevent abuse
- **Session timeout** — Configure ADK server timeout (default 24h)
- **Model costs** — Gemini 2.5 Pro charges per million tokens; monitor usage
- **Error handling** — ADK server returns 500 on agent graph failure; frontend should handle gracefully
- **Logging** — ADK server logs to stdout; pipe to aggregation service (Cloud Logging, ELK)
