---
phase: 3
title: "Force Tool Use"
status: pending
priority: P1
effort: "30m"
dependencies: [2]
---

# Phase 3: Force Tool Use

## Overview

Instruction hardening alone is unreliable with `gemma-4-31b-it` — the ADK skill explicitly
documents that models with thinking enabled may bypass tool calls regardless of instruction
wording. This phase adds `tool_config mode=ANY` to `interactive_audit_planner` to structurally
force a tool call on every planning turn, making the behavior deterministic rather than
instruction-dependent.

## Requirements

- Functional: `interactive_audit_planner` must call a tool (specifically `scope_analyzer`) on
  every new audit request turn, not just when the model decides to.
- Non-functional: The config must not break the approval/delegation turn where the agent calls
  `transfer_to_agent` (a different tool) — `mode=ANY` forces *a* tool call, not a *specific* one,
  so delegation still works.

## Architecture

ADK's `LlmAgent` passes `generate_content_config` through to the underlying Gemini API call.
`ToolConfig` with `FunctionCallingConfig(mode="ANY")` instructs the model it must call at least
one function before returning a text response.

Two sub-options within `mode=ANY`:

| Option | Behavior |
|--------|----------|
| `mode="ANY"` alone | Model picks any available tool |
| `mode="ANY"` + `allowed_function_names=["scope_analyzer"]` | Model must call `scope_analyzer` specifically |

Use `allowed_function_names` restriction only during the planning phase. Because `interactive_audit_planner`
has two distinct behavioral phases (planning vs. post-approval delegation), and ADK does not
support per-turn tool configs, the safer approach is `mode="ANY"` without restriction — this
allows `transfer_to_agent` on approval turns while still forcing tool use on planning turns.

If `mode=ANY` without restriction still allows the model to call `transfer_to_agent` on the first
turn (skipping planning), fallback: use a `before_model_callback` to inject `allowed_function_names`
based on whether `audit_plan` is already in session state.

## Related Code Files

- Modify: `app/agent.py` — `interactive_audit_planner` definition only.

## Implementation Steps

1. At the top of `app/agent.py`, confirm `genai_types` is already imported (it is — line 23):
   ```python
   from google.genai import types as genai_types
   ```
   No new imports needed.

2. In the `interactive_audit_planner` `LlmAgent(...)` constructor (around line 625), add
   `generate_content_config`:

   **Before:**
   ```python
   interactive_audit_planner = LlmAgent(
       name="interactive_audit_planner",
       model=config.worker_model,
       description=(...),
       instruction=f"""...""",
       sub_agents=[a11y_audit_pipeline],
       tools=[AgentTool(scope_analyzer)],
       output_key="audit_plan",
   )
   ```

   **After:**
   ```python
   interactive_audit_planner = LlmAgent(
       name="interactive_audit_planner",
       model=config.worker_model,
       description=(...),
       instruction=f"""...""",
       sub_agents=[a11y_audit_pipeline],
       tools=[AgentTool(scope_analyzer)],
       output_key="audit_plan",
       generate_content_config=genai_types.GenerateContentConfig(
           tool_config=genai_types.ToolConfig(
               function_calling_config=genai_types.FunctionCallingConfig(
                   mode="ANY",
               )
           )
       ),
   )
   ```

3. Run `uv run python -c "from app.agent import root_agent; print(root_agent.name)"` to confirm
   the module still imports cleanly.

4. Smoke-test locally with `adk run app` — send a test audit request and verify:
   - The agent calls `scope_analyzer` before responding with a plan.
   - On a follow-up "yes proceed" message, the agent calls `transfer_to_agent` (not stuck).

5. If the smoke test shows the agent is stuck (calling `scope_analyzer` again on the approval
   turn), implement the `before_model_callback` fallback:

   ```python
   from google.adk.agents.callback_context import CallbackContext

   def planning_tool_config_callback(
       callback_context: CallbackContext,
       llm_request,
   ):
       # Only restrict to scope_analyzer if audit_plan not yet set
       if not callback_context.state.get("audit_plan"):
           llm_request.config.tool_config = genai_types.ToolConfig(
               function_calling_config=genai_types.FunctionCallingConfig(
                   mode="ANY",
                   allowed_function_names=["scope_analyzer"],
               )
           )
       return None
   ```

   Then attach it to `interactive_audit_planner` via `before_model_callback=planning_tool_config_callback`
   and remove the static `generate_content_config`.

## Success Criteria

- [ ] `app/agent.py` imports cleanly.
- [ ] `interactive_audit_planner` has `generate_content_config` with `tool_config mode=ANY`
  (or `before_model_callback` if fallback path taken).
- [ ] Smoke test: agent calls `scope_analyzer` on a new audit request (not text-only response).
- [ ] Smoke test: agent calls `transfer_to_agent` on approval ("yes proceed") without looping.

## Risk Assessment

- Medium risk — `mode=ANY` affects every turn of the planner, including edge cases (clarification
  questions, error responses). If the model has no useful tool to call, it may call a tool with
  empty/wrong args. Mitigate: monitor with smoke test and fall back to the `before_model_callback`
  approach if needed.
- Risk: `genai_types.FunctionCallingConfig` field name may differ across `google-genai` versions.
  Check `uv run python -c "import google.genai.types as t; print(dir(t.FunctionCallingConfig()))"`.
