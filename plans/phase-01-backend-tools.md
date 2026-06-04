---
phase: 1
title: Backend Tools
status: completed
priority: P1
effort: 2h
dependencies: []
---

# Phase 1: Backend Tools

## Overview

Add `root_dir` parameter to scanning tools, update agent system prompts to extract `TARGET_DIR` from the initial message, create the sidecar validator FastAPI app, and write a `run.sh` launcher.

## Requirements

- Functional:
  - `search_codebase(pattern, file_glob, root_dir=".")` runs grep in `root_dir` instead of CWD
  - `list_files(glob_pattern, root_dir=".")` globs from `root_dir` instead of `Path(".")`
  - `read_file_content` already accepts absolute paths — no change needed
  - `interactive_audit_planner` system prompt instructs the LLM to extract `[TARGET_DIR: <path>]` from the first message and pass it as `root_dir` to all tool calls
  - All downstream scanner agents (`a11y_scanner`, `targeted_scanner`, `scope_analyzer`) have their instructions updated to use the extracted path
  - `GET /validate?path=<abs_path>` returns `{exists, file_count, detected_platforms[]}`
  - Platform detection: `*.swift` or `*.xcodeproj` → `"ios"`, `*.kt` or `AndroidManifest.xml` → `"android"`, `*.tsx`/`*.jsx`/`*.html` → `"web"`
  - `run.sh` starts validator on `:8001` then `adk api_server --port 8000`
- Non-functional:
  - Validator response < 500ms for typical project sizes
  - Tool signatures remain backward-compatible (`root_dir` defaults to `"."`)

## Architecture

```
Frontend                Backend
   │  GET /util/validate?path=...    │
   │──────────────────────────────►  app/validator.py  (port 8001)
   │◄─────────────────────────────── {exists, file_count, detected_platforms}
   │
   │  POST /api/run_sse              │
   │  body: "[TARGET_DIR: /path]\n\nAudit …"
   │──────────────────────────────►  interactive_audit_planner
                                      └─ extracts TARGET_DIR from message
                                      └─ passes root_dir="/path" to tools
                                           search_codebase(..., root_dir)
                                           list_files(..., root_dir)
```

**TARGET_DIR extraction strategy:** The `interactive_audit_planner` instruction is updated to parse `[TARGET_DIR: <path>]` from the message before delegating. The extracted path is stored in session state as `target_dir` so all downstream agents can reference it.

## Related Code Files

- Modify: `app/agent.py`
- Create: `app/validator.py`
- Create: `run.sh`
- Modify: `pyproject.toml` (add `fastapi`, `uvicorn` to deps — only if not already provided by `google-adk`)

## Implementation Steps

1. **Check if FastAPI is already available** — `google-adk` bundles FastAPI/uvicorn internally. Run `pip show fastapi uvicorn` inside the venv. If not present, add to `pyproject.toml` `dependencies`.

2. **Modify `search_codebase` in `app/agent.py`:**
   ```python
   def search_codebase(pattern: str, file_glob: str = "*", root_dir: str = ".") -> str:
       result = subprocess.run(
           ["grep", "-rn", "--include", file_glob, "-E", pattern, "."],
           capture_output=True, text=True, timeout=30,
           cwd=root_dir  # ← key change
       )
   ```

3. **Modify `list_files` in `app/agent.py`:**
   ```python
   def list_files(glob_pattern: str, root_dir: str = ".") -> str:
       files = [str(p) for p in Path(root_dir).glob(glob_pattern) if p.is_file()]
   ```

4. **Update `interactive_audit_planner` instruction** — prepend extraction block:
   ```
   IMPORTANT: If the user's message starts with "[TARGET_DIR: <path>]", extract <path>
   as the project root. Pass root_dir=<path> to all search_codebase and list_files calls.
   Store the path in session state key "target_dir".
   Strip the [TARGET_DIR: ...] prefix before treating the rest as the audit request.
   ```

5. **Update scanner agent instructions** (`a11y_scanner`, `targeted_scanner`, `scope_analyzer`) — add to each:
   ```
   NOTE: Use root_dir="{target_dir}" (from session state) in ALL tool calls.
   ```

6. **Create `app/validator.py`:**
   ```python
   from pathlib import Path
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware

   app = FastAPI()
   app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

   @app.get("/validate")
   def validate_path(path: str):
       p = Path(path)
       if not p.exists() or not p.is_dir():
           return {"exists": False, "file_count": 0, "detected_platforms": []}

       all_files = list(p.rglob("*"))
       file_count = sum(1 for f in all_files if f.is_file())

       platforms = []
       exts = {f.suffix for f in all_files if f.is_file()}
       names = {f.name for f in all_files if f.is_file()}
       if ".swift" in exts or any("xcodeproj" in n for n in names):
           platforms.append("ios")
       if ".kt" in exts or "AndroidManifest.xml" in names:
           platforms.append("android")
       if {".tsx", ".jsx", ".html"} & exts:
           platforms.append("web")

       return {"exists": True, "file_count": file_count, "detected_platforms": platforms}
   ```

7. **Create `run.sh`:**
   ```bash
   #!/usr/bin/env bash
   set -e
   cd "$(dirname "$0")"
   uvicorn app.validator:app --port 8001 &
   VALIDATOR_PID=$!
   trap "kill $VALIDATOR_PID 2>/dev/null" EXIT
   adk api_server --port 8000
   ```
   Mark executable: `chmod +x run.sh`

## Success Criteria

- [ ] `search_codebase` runs grep from `root_dir` when provided (manual test: pass `/tmp` as root_dir, confirm grep output matches)
- [ ] `list_files` globs from `root_dir` (manual test: confirm file paths are relative to root_dir)
- [ ] `GET http://localhost:8001/validate?path=/Users/...` returns correct JSON
- [ ] Non-existent path returns `{exists: false, ...}`
- [ ] iOS project path returns `detected_platforms: ["ios"]`
- [ ] `run.sh` starts both processes; Ctrl-C kills both cleanly
- [ ] Tool backward compatibility: calling without `root_dir` still scans from CWD

## Risk Assessment

- **google-adk may already bundle FastAPI** — if it does, adding `fastapi`/`uvicorn` to `pyproject.toml` creates a double-import. Mitigate: check `pip show` first; use same version constraint.
- **Instruction extraction fragility** — LLM-based extraction of `[TARGET_DIR: ...]` could fail if the format isn't exact. Mitigate: front-end must emit the prefix verbatim; the instruction uses exact bracket notation.
- **Root dir security** — validator accepts any absolute path on the machine. For internal tool this is acceptable; document in README that it's not production-safe without auth.
