---
phase: 1
title: "Fix Eval Dataset"
status: pending
priority: P1
effort: "30m"
dependencies: []
---

# Phase 1: Fix Eval Dataset

## Overview

The pre-seeded Turn 0 in `full-pipeline-dataset.json` presents a plan as plain text with no
`scope_analyzer` function_call event. The grader scans the full conversation trace and zeroes out
`tool_use_quality` because the required tool call is absent from history. This phase fixes the
dataset to match what the agent's workflow *should* have produced.

## Requirements

- Functional: Both eval cases must have a `scope_analyzer` function_call + function_response event
  in their pre-seeded Turn 0, before the plan text response.
- Functional: The pre-seeded plan text must include a `**Target Directory:**` section.
- Non-functional: Dataset must remain valid Shape B (`agent_data.turns`) format per the eval schema.

## Architecture

The eval framework (`agents-cli eval generate`) treats `agent_data.turns` as prior conversation
history. It invokes the agent starting from the last user message. The grader evaluates the
**full trace** including pre-seeded events. Adding the missing function_call/function_response
events to the seeded turn makes the history consistent with the agent's required workflow.

Event order within a turn (per eval schema):
```
user message
→ agent: function_call (scope_analyzer)
→ tool: function_response (scope_analyzer result)
→ agent: text response (plan presentation)
→ user message (approval)
```

## Related Code Files

- Modify: `tests/eval/datasets/full-pipeline-dataset.json`

## Implementation Steps

1. Open `tests/eval/datasets/full-pipeline-dataset.json`.

2. For **case `full_audit_web_react_with_approval`**, insert two events between the user message
   and the agent plan text in `turn_index: 0`:

   ```json
   {
     "author": "interactive_audit_planner",
     "content": {
       "role": "model",
       "parts": [{
         "function_call": {
           "name": "scope_analyzer",
           "args": {
             "request": "Audit the React TypeScript dashboard at /Users/ddphuong/Projects/epost-workspace/a11y-agent/frontend for WCAG 2.1 AA compliance."
           }
         }
       }]
     }
   },
   {
     "author": "tool",
     "content": {
       "role": "tool",
       "parts": [{
         "function_response": {
           "name": "scope_analyzer",
           "response": {
             "platform": "web",
             "target_dir": "/Users/ddphuong/Projects/epost-workspace/a11y-agent/frontend",
             "scope": ["src/**/*.tsx", "src/**/*.ts", "index.html"],
             "wcag_criteria": ["1.1.1", "1.3.1", "1.4.3", "2.1.1", "2.4.3", "2.4.6", "3.3.1", "4.1.2"],
             "priority_areas": ["forms and inputs", "interactive controls", "images and icons", "color contrast", "keyboard focus management"]
           }
         }
       }]
     }
   }
   ```

3. In the same case, update the existing agent plan text to add the missing `**Target Directory:**`
   section after `**Platform:**`:

   ```
   **Target Directory:** /Users/ddphuong/Projects/epost-workspace/a11y-agent/frontend
   ```

4. For **case `full_audit_ios_with_approval`**, insert the same pair of events in `turn_index: 0`:

   ```json
   {
     "author": "interactive_audit_planner",
     "content": {
       "role": "model",
       "parts": [{
         "function_call": {
           "name": "scope_analyzer",
           "args": {
             "request": "Audit the SwiftUI iOS app at /tmp/sample-ios-app for WCAG 2.1 AA compliance. Check VoiceOver support and the new onboarding flow."
           }
         }
       }]
     }
   },
   {
     "author": "tool",
     "content": {
       "role": "tool",
       "parts": [{
         "function_response": {
           "name": "scope_analyzer",
           "response": {
             "platform": "ios",
             "target_dir": "/tmp/sample-ios-app",
             "scope": ["**/*.swift", "**/*.xib", "**/*.storyboard"],
             "wcag_criteria": ["1.1.1", "1.3.1", "1.4.3", "2.1.1", "2.4.3", "4.1.2"],
             "priority_areas": ["onboarding flow screens", "image views", "custom controls", "Dynamic Type", "modal focus traps"]
           }
         }
       }]
     }
   }
   ```

5. In the iOS case, add `**Target Directory:** /tmp/sample-ios-app` to the pre-seeded plan text.

6. Validate JSON is well-formed: `python3 -m json.tool tests/eval/datasets/full-pipeline-dataset.json`

## Success Criteria

- [ ] `full-pipeline-dataset.json` is valid JSON (no parse errors).
- [ ] Both cases have a `scope_analyzer` function_call event in `turn_index: 0`.
- [ ] Both cases have a `scope_analyzer` function_response event in `turn_index: 0`.
- [ ] Both pre-seeded plan texts include a `**Target Directory:**` section with the correct path.
- [ ] Event author sequence within turn 0 is: `user → interactive_audit_planner (function_call) → tool (function_response) → interactive_audit_planner (text) → user`.

## Risk Assessment

- Low risk — JSON-only edit, no agent code changes.
- Risk: malformed JSON breaks `eval generate`. Mitigate with `python3 -m json.tool` validation step.
- Risk: `"author": "tool"` vs other author names may vary by eval framework version. Check existing
  traces in `artifacts/traces/` for the exact author string the framework uses for tool responses.
