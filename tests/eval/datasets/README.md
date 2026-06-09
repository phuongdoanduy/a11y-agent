# Evaluation Datasets

Datasets for testing the a11y-agent's planning and audit capabilities.

## Running Evaluations

```bash
# Ensure eval dependencies are installed
uv sync --extra eval

# Run a single dataset
uv run adk eval app tests/eval/datasets/basic-dataset.json \
  --config_file_path tests/eval/eval_config.json --print_detailed_results

# Run all datasets
uv run adk eval app \
  tests/eval/datasets/adk-eval-dataset.json \
  tests/eval/datasets/basic-dataset.json \
  tests/eval/datasets/full-pipeline-dataset.json \
  --config_file_path tests/eval/eval_config.json --print_detailed_results

# Run a specific case from a dataset
uv run adk eval app tests/eval/datasets/basic-dataset.json:audit_plan_web_frontend \
  --config_file_path tests/eval/eval_config.json
```

## Datasets

| File | Cases | Description |
|------|-------|-------------|
| `adk-eval-dataset.json` | 3 | Basic agent interactions (greeting, iOS audit request, web audit request) |
| `basic-dataset.json` | 4 | Single-turn audit planning across web/iOS/Android + capabilities query |
| `full-pipeline-dataset.json` | 2 | Multi-turn: plan → approve → execute (web React, iOS SwiftUI) |

## Metrics

Configured in `tests/eval/eval_config.json`:

| Metric | Threshold | Type | Description |
|--------|-----------|------|-------------|
| `tool_trajectory_avg_score` | 1.0 | Built-in | Verifies tool calls match expected trajectory |
| `final_response_match_v2` | 0.6 | Built-in (LLM-as-judge) | Semantic similarity of actual vs expected response |
| `audit_plan_quality` | 0.6 | Custom (heuristic) | Checks platform detection, scope, WCAG criteria, tool use, priority areas |

## Custom Metric

`tests/eval/custom_metrics.py` implements `audit_plan_quality` — a heuristic
scorer (no LLM call, fast) that awards 1 point each for:

1. Platform detected (ios/android/web/cross-platform)
2. File glob patterns present (`*.tsx`, `**/*.swift`, etc.)
3. 3+ WCAG 2.1 AA success criteria listed
4. `scope_analyzer` tool use evidence
5. 2+ platform-specific priority areas mentioned

Score is normalised to 0–1; threshold is 0.6 (≥3 of 5 criteria).

## Dataset Format (ADK 2.1.0 EvalSet)

```json
{
  "eval_set_id": "a11y_basic",
  "eval_cases": [
    {
      "evalId": "unique_case_id",
      "conversation": [
        {
          "invocationId": "inv-001",
          "userContent": {
            "role": "user",
            "parts": [{"text": "User message"}]
          },
          "finalResponse": {
            "role": "model",
            "parts": [{"text": "Expected agent response (optional)"}]
          }
        }
      ],
      "sessionInput": {
        "app_name": "app",
        "user_id": "eval_user",
        "state": {}
      }
    }
  ]
}
```

Multi-turn cases have multiple `conversation` entries (one per user message).

## Known Limitations

- **`AgentTool` and tool trajectory**: The `scope_analyzer` is wrapped in
  `AgentTool`, which serialises tool calls as text rather than native
  `FunctionCall` parts. This means tool trajectory matching sees empty call
  lists. The `intermediateData` field was removed from `full-pipeline-dataset.json`
  to work around this. For real tool trajectory verification, register
  `scope_analyzer` as a direct `FunctionTool` instead.

- **`final_response_match_v2` and quota**: This metric uses Gemini as an
  LLM judge. On the free tier, the quota (20 req/day for `gemini-2.5-flash`)
  can be exhausted during eval runs. When quota is exceeded, the metric
  returns `NOT_EVALUATED` (doesn't fail the case).

- **Non-deterministic LLM output**: Agent responses vary across runs.
  The LLM-as-judge metric handles semantic variation, but scores may
  fluctuate. Run evals multiple times to establish a baseline.
