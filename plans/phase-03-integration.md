---
phase: 3
title: Integration
status: completed
priority: P2
effort: 1h
dependencies:
  - 1
  - 2
---

# Phase 3: Integration

## Overview

Smoke-test the full end-to-end flow: validator sidecar + tool root_dir wiring + frontend UI. Update README with new startup instructions and document the `run.sh` launcher.

## Requirements

- Functional:
  - Full flow works: enter path → validate → enter scope → start audit → agent scans correct directory
  - `run.sh` starts both processes; Ctrl-C terminates both cleanly
  - README updated: replace `adk api_server --port 8000` with `./run.sh`
  - `.env.example` unchanged (no new env vars needed)
- Non-functional:
  - No regressions: URL-based audit prompts (existing example prompts) still work when path is valid

## Related Code Files

- Modify: `README.md`
- Verify: `app/validator.py`, `app/agent.py`, `frontend/src/components/WelcomeScreen.tsx`, `frontend/src/App.tsx`

## Implementation Steps

1. **Verify `run.sh` process management** — run `./run.sh`, confirm both ports respond:
   ```bash
   curl http://localhost:8001/validate?path=/tmp     # → {exists: true, ...}
   curl http://localhost:8000/list-apps              # → ADK apps list
   ```

2. **End-to-end smoke test:**
   - Open `http://localhost:3000`
   - Enter path to any local project (e.g. this repo itself: `/Users/.../epost-workspace/a11y-agent`)
   - Click Validate → confirm green chip shows file count + platforms (should show `web`)
   - Enter scope: `Audit for WCAG 2.1 AA`
   - Click Start Audit
   - Confirm agent begins scanning files from the target path (check that findings reference files under that path, not CWD)

3. **Regression check — existing URL prompt:**
   - Enter any absolute path, validate it
   - In scope field, use one of the existing example prompts (they reference epost.no URLs)
   - Confirm agent still runs without crashing (URL references in scope are fine — agent will scan the local path but describe the audit context from the scope text)

4. **Update `README.md`:**
   - Replace `adk api_server --port 8000` with `./run.sh` in Quick Start section
   - Add note: "The validator sidecar runs on port 8001 (path validation); ADK API server runs on port 8000"
   - Add "Local Project Audit" usage example:
     ```
     # Audit a local iOS project
     1. Run ./run.sh
     2. Open http://localhost:3000
     3. Enter project path (e.g. /Users/you/MyApp) and click Validate
     4. Enter scope: "Audit iOS app for WCAG 2.1 AA"
     5. Click Start Audit
     ```

5. **Update `WelcomeScreen` example prompts** — replace URL-based examples with local path examples:
   ```ts
   const EXAMPLE_PROMPTS = [
     "Audit the iOS app for WCAG 2.1 AA compliance — focus on VoiceOver and Dynamic Type",
     "Run accessibility scan on the Android app — keyboard navigation and TalkBack support",
     "Full WCAG 2.1 AA audit covering forms, images, and focus management",
   ];
   ```
   These no longer reference epost.no URLs since the path is now set separately.

## Success Criteria

- [ ] `curl http://localhost:8001/validate?path=/tmp` returns `{exists: true, ...}`
- [ ] Full audit flow completes with findings referencing files in the entered path
- [ ] `run.sh` Ctrl-C kills both processes (no zombie uvicorn)
- [ ] README Quick Start reflects new `./run.sh` command
- [ ] No TypeScript or Python compile errors after all changes

## Risk Assessment

- **Port conflict** — if port 8001 is already in use, validator fails silently. Mitigate: `run.sh` checks port availability or uses `lsof` before binding.
- **Example prompts now detached from path** — old prompts referenced URLs; new prompts are generic scopes. Acceptable since path is now a separate input.
