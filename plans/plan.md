---
title: audit-local-project-support
description: >-
  Add UI path input + sidecar validator so users can audit any local project
  directory, not just CWD
status: completed
priority: P2
branch: main
tags:
  - feature
  - backend
  - frontend
blockedBy: []
blocks: []
created: '2026-06-04T13:13:31.218Z'
createdBy: 'ck:plan'
source: skill
---

# audit-local-project-support

## Overview

Currently `search_codebase` and `list_files` tools grep from CWD (`"."`) — the directory where `adk api_server` is launched. Users have no way to point the agent at an arbitrary local project.

This plan adds:
1. A lightweight FastAPI sidecar (`app/validator.py`, port 8001) with a `GET /validate?path=` endpoint
2. `root_dir` parameter to scanning tools in `app/agent.py`
3. Updated agent system prompts to extract and pass `TARGET_DIR` from the initial message
4. A path input + Validate button in `WelcomeScreen.tsx`
5. `targetDir` state in `App.tsx` prepended to the first outgoing message
6. Second Vite proxy rule `/util → :8001`
7. `run.sh` wrapper to start both processes

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backend Tools](./phase-01-backend-tools.md) | Completed |
| 2 | [Frontend UI](./phase-02-frontend-ui.md) | Completed |
| 3 | [Integration](./phase-03-integration.md) | Completed |

## Non-Goals

- No directory picker (browser can't read filesystem)
- No multi-project sessions
- No persistent path history
- No audit of remote URLs (out of scope for this plan)

## Dependencies

None — no existing plans to coordinate with.
