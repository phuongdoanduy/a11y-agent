# Code Standards — epost-a11y-agent

## Overview

This document establishes code style, architectural patterns, and conventions for the epost-a11y-agent codebase. All code must follow these standards to maintain consistency, readability, and adherence to ADK patterns.

## Python Code Standards

### File Structure & Naming

- **File naming:** `snake_case.py`
- **Module organization:** Group related code logically; keep files under 200 LOC
- **Imports:** Alphabetical within groups (stdlib, third-party, local)
  ```python
  import asyncio
  import json
  from pathlib import Path
  
  from google.adk.agents import BaseAgent, LlmAgent
  from pydantic import BaseModel, Field
  
  from .config import config
  ```

### Pydantic Models

All structured data **must** use Pydantic models. Never use plain dicts for API contracts.

```python
from pydantic import BaseModel, Field
from typing import Literal

class A11yViolation(BaseModel):
    """A single accessibility violation."""
    id: str = Field(description="Unique finding ID, e.g. 'a11y-001'")
    wcag_criterion: str = Field(description="WCAG 2.1 criterion, e.g. '1.1.1'")
    severity: Literal["critical", "serious", "moderate", "minor"] = Field(
        description="Violation severity"
    )
    # Always include Field descriptions for LLM prompts
```

**Patterns:**
- Use `Field(description="...")` for every field; LLM prompts include descriptions
- Use `Literal` types for enums (not enum classes)
- Use `| None` for optional; default=None in Field
- Use `list[T]` for collections (Python 3.10+)
- Always define `__doc__` on model classes

### ADK Agent Definition

All agents follow this pattern:

```python
agent = LlmAgent(
    name="agent_name",
    instructions="""
    You are an agent that does X.
    
    Instructions:
    - Use tools to ...
    - Output ...
    """,
    model=config.worker_model,  # Or config.critic_model for evaluation
    tools=[tool1, tool2, ...],
    output_schema=OutputModel,  # If structured output required
    planner=BuiltInPlanner(ThinkingConfig(...)) if extended_reasoning else None,
)
```

**Key points:**
- Instructions must be clear and specific; don't assume agent knowledge
- `model` must reference `config.worker_model` or `config.critic_model` (never hardcode model name)
- Tools passed as list; agents call tools declaratively
- `output_schema` enforces Pydantic validation; optional
- `planner` only on agents that need extended reasoning (scanners, evaluators)

### Async Generators (Streaming)

Frontend uses async generators for SSE streaming. Backend should support:

```python
async def streamAgentResponse(...) -> AsyncGenerator[ParsedSSEChunk]:
    """Stream agent response as structured chunks."""
    for await event in backend_stream():
        if event.type == "text":
            yield ParsedSSEChunk(type="text", content=event.content)
        elif event.type == "tool_call":
            yield ParsedSSEChunk(type="tool_call", data=event.tool_call)
```

**Patterns:**
- Use `async def` and `yield` for streaming
- Type hint as `AsyncGenerator[T]`
- Yield early/frequently for responsive UI
- Signal end with `ParsedSSEChunk(type="done")`

### Callbacks (Side Effects)

Use callbacks for scoring, deduplication, state mutations:

```python
def collect_findings_callback(context: CallbackContext):
    """Callback: deduplicate violations after scanner agent."""
    scan_result = context.get_output_key("audit_scan_result")
    violations = scan_result.get("violations", [])
    
    # Deduplicate
    unique = {}
    for v in violations:
        key = (v["wcag_criterion"], v["file_path"])
        if key not in unique:
            unique[key] = v
    
    # Update state
    context.set_output_key("audit_scan_result", {
        **scan_result,
        "violations": list(unique.values())
    })

# Register callback
agent.after_agent_callback = collect_findings_callback
```

**Patterns:**
- Use `context.get_output_key()` and `context.set_output_key()` for state
- Never mutate global state; always use context
- Keep callbacks pure (no side effects outside context)
- Callback must handle missing keys gracefully

### Tool Implementation

Tools are pure functions with clear input/output contracts:

```python
def search_codebase(pattern: str, file_glob: str = "*") -> str:
    """Search codebase for accessibility patterns.
    
    Args:
        pattern: Regex pattern to search for
        file_glob: File glob filter (e.g., "*.swift")
    
    Returns:
        JSON string with results
    
    Raises:
        ValueError: If pattern is invalid regex
    """
    import re
    
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return json.dumps({"error": f"Invalid regex: {e}"})
    
    results = []
    # Search logic here
    return json.dumps(results[:50])  # Cap 50 results
```

**Patterns:**
- Always validate inputs; return error JSON rather than raising
- Return JSON strings (not dicts); ADK serializes
- Include usage limits in docstring
- Test with edge cases: empty input, no matches, huge files

### Error Handling

Use try-catch for external operations; return structured errors:

```python
try:
    response = await gemini_client.generate(message)
except Exception as e:
    return {
        "error": str(e),
        "error_type": type(e).__name__,
        "recoverable": False,
    }
```

**Patterns:**
- Catch broad exceptions; log and return structured error
- Never re-raise; let caller decide handling
- Include error type and message for frontend debugging
- Set `recoverable` flag if user can retry

### Configuration Access

Always use the global `config` singleton:

```python
from .config import config

score = 100
score -= len(critical_violations) * config.severity_scores["critical"]
```

**Patterns:**
- Import `config` once at module level
- Never instantiate `A11yConfiguration` multiple times
- Reference config by dotted notation: `config.critic_model`, `config.compliance_threshold`
- Keep config immutable after initialization

## TypeScript Code Standards

### File Structure & Naming

- **File naming:** `kebab-case.ts` or `PascalCase.tsx` (components)
- **Component naming:** PascalCase for React components
- **Module organization:** Colocate types with usage; one component per file

```
frontend/src/
├── components/
│   ├── AuditDashboard.tsx    # Component + local types
│   ├── FindingsList.tsx
│   └── ...
├── lib/
│   └── utils.ts              # Utilities, API client, shared types
└── App.tsx
```

### Interfaces & Types

Define types to match Pydantic models exactly:

```typescript
// Pydantic in Python:
// class A11yViolation(BaseModel):
//     id: str
//     wcag_criterion: str
//     severity: Literal["critical", "serious", "moderate", "minor"]

// TypeScript equivalent:
export interface A11yViolation {
  id: string;
  wcag_criterion: string;
  severity: "critical" | "serious" | "moderate" | "minor";
  file_path: string;
  line_number?: number;  // Optional in Python = optional in TS
  fix_suggestion: string;
  platform: "ios" | "android" | "web" | "cross-platform";
}
```

**Patterns:**
- Use `interface` for structural types (API contracts)
- Use `type` for unions and complex shapes
- Use `export` for types consumed elsewhere
- Match Python case exactly (snake_case in Python → camelCase in TS is **not** acceptable; keep snake_case for API field names)

### React Hooks & State

Use functional components with hooks. Avoid class components.

```typescript
export function AuditDashboard({ auditResult }: { auditResult: AuditResult }) {
  const [expandedViolation, setExpandedViolation] = useState<string | null>(null);
  
  const handleExpand = useCallback((id: string) => {
    setExpandedViolation(expandedViolation === id ? null : id);
  }, [expandedViolation]);
  
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
}
```

**Patterns:**
- One component per file (except very small utilities)
- Props destructured in function signature
- Use `useCallback` for event handlers
- Use `useMemo` for expensive computations
- No PropTypes; rely on TypeScript inference

### API Client (lib/utils.ts)

ADK API client follows async generator pattern:

```typescript
export async function* streamAgentResponse(
  sessionId: string,
  message: string,
  userId = "u_999",
  appName = "app",
  signal?: AbortSignal,
): AsyncGenerator<ParsedSSEChunk> {
  const res = await fetch(`${API_BASE}/run_sse`, {
    method: "POST",
    body: JSON.stringify({...}),
    signal,  // For abort support
  });
  
  // Parse SSE stream
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Parse lines, yield chunks
  }
}
```

**Patterns:**
- Use `AsyncGenerator` for streaming
- Respect `AbortSignal` for cancellation
- Yield early/frequently for responsive UI
- Handle partial lines in buffer
- Yield `{ type: "done" }` at end

### Event Handling & Streaming UI

App component orchestrates streaming and UI updates:

```typescript
const sendMessage = useCallback(async (text: string) => {
  setIsStreaming(true);
  try {
    for await (const chunk of streamAgentResponse(sessionId, text)) {
      if (chunk.type === "text") {
        setMessages(prev => [...prev, { content: chunk.content, ... }]);
      } else if (chunk.type === "done") {
        break;
      }
    }
  } finally {
    setIsStreaming(false);
  }
}, [sessionId]);
```

**Patterns:**
- Block further messages with `isStreaming` flag
- Abort streaming on user click via `AbortController`
- Update UI on each chunk (not batched)
- Always clear `isStreaming` in finally block

### Tailwind CSS

Use utility-first approach; avoid inline styles:

```typescript
<div className="flex items-center justify-between gap-4 p-6 bg-white rounded-lg shadow-sm">
  <h2 className="text-lg font-semibold text-gray-900">
    {title}
  </h2>
  <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
    Action
  </button>
</div>
```

**Patterns:**
- Use `cn()` utility from `lib/utils.ts` to merge classes conditionally
- Use Tailwind v4 syntax (no `@apply`)
- Prefer semantic color names: `text-gray-900`, `bg-blue-600`
- Use gap utilities for spacing; avoid margin on children
- Use `shadow-sm`, `rounded-lg` for consistent elevation

### Component Props

Props should be typed explicitly:

```typescript
interface FindingsListProps {
  violations: A11yViolation[];
  onSelectViolation?: (id: string) => void;
  filterBySeverity?: "critical" | "serious" | "moderate" | "minor" | null;
}

export function FindingsList({
  violations,
  onSelectViolation,
  filterBySeverity,
}: FindingsListProps) {
  // Component logic
}
```

**Patterns:**
- Define Props interface with explicit optional/required fields
- Use `?:` for optional props with defaults
- Use callback types for event handlers: `(id: string) => void`
- Pass null/undefined explicitly; don't rely on defaults for filtering

## Shared Principles

### Code Comments

Comments explain **why**, not what. Code reads like documentation:

```python
# Bad:
# Set score to 100
score = 100
# Subtract 10 for each critical
for v in violations:
    if v.severity == "critical":
        score -= 10

# Good:
score = 100
# WCAG AA scoring: deduct points per severity to incentivize fixes
# (prevents "one critical violation is OK" mindset)
for violation in violations:
    if violation.severity == "critical":
        score -= config.severity_scores["critical"]
```

### Naming Conventions

| Context | Style | Example |
|---------|-------|---------|
| Python functions | `snake_case` | `search_codebase`, `collect_findings_callback` |
| Python classes | `PascalCase` | `A11yViolation`, `ComplianceChecker` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_AUDIT_ITERATIONS`, `WCAG_AA_CRITERIA` |
| TypeScript functions | `camelCase` | `streamAgentResponse`, `createSession` |
| TypeScript interfaces | `PascalCase` | `ParsedSSEChunk`, `AuditResult` |
| React components | `PascalCase` | `AuditDashboard`, `FindingsList` |
| React props object | `PascalCase` | `FindingsListProps` |
| CSS classes | `kebab-case` | `audit-dashboard`, `violation-item` |

### Type Safety

**Python:**
- Always use type hints on function signatures
- Use Pydantic for data models (not dataclasses alone)
- Run `mypy` before commit (if configured)

**TypeScript:**
- Strict mode enabled; no `any` without explicit `// @ts-ignore` + comment
- Export types for cross-module usage
- Use `unknown` instead of `any` when type is genuinely unknown

### Testing Patterns

**Python (pytest):**
```python
import pytest
from app.agent import compute_score, A11yViolation

def test_compute_score_critical_violations():
    """Score penalizes critical violations."""
    violations = [
        A11yViolation(severity="critical", ...),
        A11yViolation(severity="minor", ...),
    ]
    assert compute_score(violations) == 89  # 100 - 10 - 1
```

**TypeScript (Vitest):**
```typescript
import { describe, it, expect } from "vitest";
import { parseAuditReport } from "./utils";

describe("parseAuditReport", () => {
  it("extracts JSON from markdown code block", () => {
    const markdown = "# Report\n```json\n{\"score\": 95}\n```";
    const result = parseAuditReport(markdown);
    expect(result?.score).toBe(95);
  });
});
```

## Review Checklist

Before committing:

- [ ] Type hints present on all functions (Python)
- [ ] Type safety enforced (TypeScript: no `any`)
- [ ] No hardcoded model names; uses `config.worker_model` or `config.critic_model`
- [ ] All Pydantic models have Field descriptions
- [ ] Error handling returns structured JSON, not exceptions
- [ ] Comments explain why, not what
- [ ] File size < 200 LOC (or justified)
- [ ] Imports alphabetized and grouped
- [ ] No console.log() or print() in production code (use logger)
- [ ] Tests pass locally before push

## Size Limits

- **Python files:** 200 LOC soft limit; exceeding requires justification
- **TypeScript components:** 150 LOC soft limit
- **Pydantic models:** 50 fields max (consider splitting if larger)

If a file exceeds limits, modularize:
- Extract utility functions to separate module
- Split large components into smaller sub-components
- Extract Pydantic models into dedicated schema file
