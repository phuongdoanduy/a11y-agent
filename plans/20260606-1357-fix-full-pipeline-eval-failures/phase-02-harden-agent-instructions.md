---
phase: 2
title: "Harden Agent Instructions"
status: pending
priority: P1
effort: "30m"
dependencies: []
---

# Phase 2: Harden Agent Instructions

## Overview

`interactive_audit_planner`'s instruction treats `scope_analyzer` as advisory — the model reads
"Use `scope_analyzer` tool to create an audit plan" and generates the plan from its own knowledge
instead. This phase rewrites the instruction to make the tool call unambiguously mandatory and
adds a strict output template so `target_dir` can never be omitted from the plan text.

## Requirements

- Functional: Instruction must make `scope_analyzer` a hard prerequisite, not a suggestion.
- Functional: Instruction must include a fill-in-the-blank plan output template with `target_dir`
  as a required field.
- Non-functional: Instruction change must not break existing behavior for the approval/delegation
  flow or the `[TARGET_DIR: ...]` extraction logic.

## Architecture

Single file change: `app/agent.py`, the `instruction` string of `interactive_audit_planner`.

The current instruction has five numbered rules; Rule 2 is the weak link:
> "Use `scope_analyzer` tool to create an audit plan for the user's request."

Replace with explicit mandatory language and a concrete output template. The template approach
is more reliable than instruction alone because it gives the model a deterministic format to fill,
reducing the chance it fabricates content without calling the tool.

## Related Code Files

- Modify: `app/agent.py` — `interactive_audit_planner` `instruction` string only.

## Implementation Steps

1. In `app/agent.py`, locate the `interactive_audit_planner` `instruction` string (around line 633).

2. Replace Rule 2 with mandatory language:

   **Before:**
   ```python
   2. Use `scope_analyzer` tool to create an audit plan for the user's request.
      - ALWAYS include the extracted target directory path in the scope_analyzer `request` argument
        e.g. "Audit the React TypeScript app at /path/to/project for WCAG 2.1 AA..."
   ```

   **After:**
   ```python
   2. MANDATORY FIRST ACTION — before writing ANY text to the user, call the `scope_analyzer`
      tool with the full audit request including the extracted target directory path.
      Do NOT generate a plan from your own knowledge. The `scope_analyzer` tool call is
      required on every new audit request. If you have not called it yet, call it now.
      Example request argument: "Audit the React TypeScript app at /path/to/project for WCAG 2.1 AA compliance."
   ```

3. Replace Rule 3/4 (the loose list of required sections) with a strict output template:

   **Before:**
   ```python
   3. AFTER scope_analyzer returns, you MUST immediately emit a complete text response to the user
      presenting the full audit plan. You MUST NOT stop after the tool call.
   4. The text response MUST include ALL of these sections:
      a) **Platform**: detected platform (ios / android / web / cross-platform)
      b) **Target Directory**: the path being audited
      c) **Scope**: specific file glob patterns to be scanned (e.g. **/*.tsx, **/*.swift)
      d) **WCAG 2.1 AA Criteria**: at least 3 specific success criteria (e.g. 1.1.1, 1.4.3, 2.4.3)
      e) **Priority Areas**: at least 2 platform-specific areas (e.g. forms, images, focus management)
      f) A question asking the user for explicit approval before executing the audit.
   ```

   **After:**
   ```python
   3. AFTER scope_analyzer returns, immediately emit a text response using this EXACT template
      (fill in each field from the scope_analyzer output — do not skip any field):

      **Platform:** <detected platform: ios / android / web / cross-platform>
      **Target Directory:** <the extracted [TARGET_DIR] path — REQUIRED, never omit>
      **Scope:**
      - <glob pattern 1>
      - <glob pattern 2>
      **WCAG 2.1 AA Criteria:**
      - <criterion 1 with name, e.g. "1.1.1 Non-text Content">
      - <criterion 2>
      - <criterion 3>
      (include at least 3 criteria)
      **Priority Areas:**
      - <platform-specific area 1>
      - <platform-specific area 2>
      (include at least 2 areas)

      Shall I proceed with the full accessibility audit?
   ```

4. Verify the rest of the instruction (Rules 5–6 and WORKFLOW section) is unchanged.

5. Run `uv run python -c "from app.agent import root_agent; print(root_agent.name)"` to confirm
   the module still imports without errors after the string edit.

## Success Criteria

- [ ] `app/agent.py` imports cleanly (`uv run python -c "from app.agent import root_agent"`).
- [ ] `interactive_audit_planner.instruction` contains the word "MANDATORY" before any tool reference.
- [ ] `interactive_audit_planner.instruction` contains the output template with `**Target Directory:**`.
- [ ] No other agents or callbacks are modified.

## Risk Assessment

- Low risk — instruction string change only, no API or logic change.
- Risk: overly rigid template causes the model to stall on edge cases (e.g. unknown platform).
  Mitigate: keep `<detected platform>` wording flexible; do not enumerate valid values in the template.
- Risk: instruction length growth may slightly increase token cost per turn. Acceptable tradeoff.
