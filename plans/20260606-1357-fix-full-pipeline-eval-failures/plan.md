---
title: "fix-full-pipeline-eval-failures"
description: >-
  Fix three root causes driving zero scores on multi_turn_tool_use_quality and
  final_response_quality in the full-pipeline eval dataset.
status: completed
priority: P1
branch: "main"
tags:
  - eval
  - agent
  - fix
blockedBy: []
blocks: []
created: "2026-06-06T06:57:46.732Z"
createdBy: "ck:plan"
source: skill
---

# fix-full-pipeline-eval-failures

## Overview

The `full-pipeline-dataset.json` eval produces zero scores on `multi_turn_tool_use_quality`
and `final_response_quality` across both cases. Root cause analysis identified three independent
failure drivers that must all be fixed for the eval to pass:

1. **Dataset inconsistency** — pre-seeded Turn 0 shows the agent presenting a plan as plain text
   with no `scope_analyzer` function_call event. The grader scans the full conversation trace,
   finds no tool call, and zeroes out `tool_use_quality`.

2. **Weak agent instruction** — `interactive_audit_planner` treats `scope_analyzer` as advisory
   and generates plans from its own knowledge. The `gemma-4-31b-it` model skips the tool call
   entirely, especially when thinking mode is enabled.

3. **Missing `target_dir` in plan text** — the instruction lists it as required but the model
   omits it, failing a dedicated grader rubric.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Fix Eval Dataset](./phase-01-fix-eval-dataset.md) | Completed |
| 2 | [Harden Agent Instructions](./phase-02-harden-agent-instructions.md) | Completed |
| 3 | [Force Tool Use](./phase-03-force-tool-use.md) | Completed |
| 4 | [Eval Verification](./phase-04-eval-verification.md) | Completed |

## Affected Files

- `tests/eval/datasets/full-pipeline-dataset.json` — Phase 1
- `app/agent.py` — Phase 2 + 3

## Non-Goals

- Do not lower eval thresholds or remove rubrics to make scores pass artificially.
- Do not touch `basic-dataset.json` or `adk-eval-dataset.json`.
- No changes to scoring model, pipeline agents, or frontend.

## Dependencies

No cross-plan dependencies. Previous plan (audit-local-project-support) is completed.
