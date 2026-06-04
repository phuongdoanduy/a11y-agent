---
phase: 2
title: Frontend UI
status: completed
priority: P1
effort: 2h
dependencies:
  - 1
---

# Phase 2: Frontend UI

## Overview

Add a project path text input + Validate button to `WelcomeScreen.tsx`, wire validation through a new `/util` Vite proxy, store `targetDir` in `App.tsx`, and prepend `[TARGET_DIR: <path>]` to the first outgoing message.

## Requirements

- Functional:
  - `WelcomeScreen` renders a "Project Path" text input above the scope input
  - Clicking "Validate" calls `GET /util/validate?path=<value>` and shows result chip
  - Result chip: green with file count + platforms on success, red "Path not found" on failure
  - "Start Audit" button is disabled until path is validated (chip shows green)
  - `App.tsx` receives `targetDir` from `WelcomeScreen` (alongside the scope string)
  - `sendMessage` prepends `[TARGET_DIR: <path>]\n\n` to the text when `targetDir` is set
  - Example prompts still work: clicking one fills the scope input; path must still be validated first
- Non-functional:
  - Validate button shows a loading spinner during fetch
  - Input re-validation clears the chip (user must click Validate again after editing path)

## Architecture

```
WelcomeScreen
  ├── path input  ──► Validate btn ──► GET /util/validate?path=...
  │                                          ↓
  │                                    ValidationChip (green/red)
  │
  └── scope input + Start Audit btn (disabled until chip is green)
        ↓ onSubmit(scope, path)
App.tsx
  ├── targetDir state (string | null)
  └── sendMessage(text):
        if targetDir → prepend "[TARGET_DIR: {targetDir}]\n\n" to text
```

**`WelcomeScreen` prop change:** `onSubmit(text: string)` → `onSubmit(scope: string, targetDir: string)`.  
`App.tsx` receives both, stores `targetDir`, passes only `scope` into the visible user message, but sends `[TARGET_DIR: ...]\n\n{scope}` to the API.

## Related Code Files

- Modify: `frontend/src/components/WelcomeScreen.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/vite.config.ts`

## Implementation Steps

1. **`vite.config.ts` — add second proxy rule:**
   ```ts
   proxy: {
     "/api": { target: "http://localhost:8000", changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
     "/util": { target: "http://localhost:8001", changeOrigin: true, rewrite: (p) => p.replace(/^\/util/, "") },
   }
   ```

2. **`WelcomeScreen.tsx` — new props interface and state:**
   ```ts
   interface Props {
     onSubmit: (scope: string, targetDir: string) => void;
   }
   // Add state:
   const [path, setPath] = useState("");
   const [scope, setScope] = useState("");
   const [validating, setValidating] = useState(false);
   const [validation, setValidation] = useState<{
     ok: boolean; fileCount: number; platforms: string[]
   } | null>(null);
   ```
   - Reset `validation` to `null` whenever `path` changes (input `onChange`)

3. **`WelcomeScreen.tsx` — validate handler:**
   ```ts
   const handleValidate = async () => {
     setValidating(true);
     setValidation(null);
     try {
       const res = await fetch(`/util/validate?path=${encodeURIComponent(path)}`);
       const data = await res.json();
       setValidation({ ok: data.exists, fileCount: data.file_count, platforms: data.detected_platforms });
     } catch {
       setValidation({ ok: false, fileCount: 0, platforms: [] });
     } finally {
       setValidating(false);
     }
   };
   ```

4. **`WelcomeScreen.tsx` — path input row (insert above existing scope row):**
   ```tsx
   <div className="mb-4">
     <label className="mb-1.5 block text-left text-xs font-medium text-zinc-400">
       Local Project Path
     </label>
     <div className="flex gap-2">
       <input
         value={path}
         onChange={(e) => { setPath(e.target.value); setValidation(null); }}
         placeholder="/Users/you/my-app"
         className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
       />
       <button
         type="button"
         onClick={handleValidate}
         disabled={!path.trim() || validating}
         className="rounded-lg border border-zinc-700 px-4 py-3 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-40"
       >
         {validating ? "…" : "Validate"}
       </button>
     </div>
     {/* Validation result chip */}
     {validation && (
       <p className={`mt-1.5 text-xs ${validation.ok ? "text-green-400" : "text-red-400"}`}>
         {validation.ok
           ? `✓ ${validation.fileCount} files · ${validation.platforms.join(", ") || "unknown platform"}`
           : "✗ Path not found or not a directory"}
       </p>
     )}
   </div>
   ```

5. **`WelcomeScreen.tsx` — update `handleSubmit` and "Start Audit" disabled condition:**
   ```ts
   const handleSubmit = (e: React.FormEvent) => {
     e.preventDefault();
     if (scope.trim() && validation?.ok) onSubmit(scope.trim(), path.trim());
   };
   // Start Audit button: disabled={!scope.trim() || !validation?.ok}
   ```
   - Rename existing `input` state to `scope`; existing `input` onChange → `setScope`

6. **`WelcomeScreen.tsx` — example prompt buttons:**  
   Clicking an example sets `scope` (not `path`) via `setScope(prompt)`. Path still requires manual entry + Validate.
   ```ts
   onClick={() => setScope(prompt)}
   ```

7. **`App.tsx` — update `WelcomeScreen` usage:**
   ```tsx
   // Change WelcomeScreen onSubmit handler:
   <WelcomeScreen onSubmit={(scope, dir) => {
     setTargetDir(dir);
     sendMessage(scope, dir);
   }} />
   ```
   Add state: `const [targetDir, setTargetDir] = useState<string>("");`

8. **`App.tsx` — update `sendMessage` signature and body:**
   ```ts
   const sendMessage = useCallback(async (text: string, dir?: string) => {
     const resolvedDir = dir ?? targetDir;
     const payload = resolvedDir ? `[TARGET_DIR: ${resolvedDir}]\n\n${text}` : text;
     // Use payload (not text) for the API call
     // Display text (not payload) as the user message in chat
     ...
     for await (const chunk of streamAgentResponse(sid, payload, ...))
   ```
   The visible user message bubble shows `text`; the wire payload includes the prefix.

## Success Criteria

- [ ] Path input renders above scope input in `WelcomeScreen`
- [ ] Validate button fetches `/util/validate` and shows green chip on valid path
- [ ] Green chip shows file count and detected platforms
- [ ] Red chip shown for non-existent path
- [ ] Editing path after validation clears the chip
- [ ] "Start Audit" disabled until green chip is showing
- [ ] First agent message in chat does NOT show `[TARGET_DIR: ...]` prefix (only visible in API payload)
- [ ] Example prompt clicks fill the scope field, not the path field

## Risk Assessment

- **`onSubmit` prop signature change** — `App.tsx` currently passes `sendMessage` directly to `WelcomeScreen`. Must update the call site. The `InputForm` `onSubmit` is a separate prop — no change needed there.
- **Displaying vs sending** — The user message bubble must show the clean `scope` text, not the `[TARGET_DIR: ...]` prefixed payload. The split is in `sendMessage`: `text` → display, `payload` → API.
