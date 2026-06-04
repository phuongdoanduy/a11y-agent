# Code Standards - epost-a11y-agent

## Goal

Keep the codebase small, explicit, and aligned with the current runtime:

- Python ADK backend in `app/`
- React 19 + Vite 6 frontend in `frontend/`
- Docs and plans kept in `docs/` and `plans/`

## Python Standards

### File and module style

- Use `snake_case.py`.
- Keep modules focused.
- Prefer small helper functions over large monolithic files.
- Keep generated or deployment glue separate from the agent graph.

### Data models

- Use Pydantic for structured contracts.
- Prefer explicit field descriptions.
- Keep the backend audit schema in Python and the frontend UI schema separate when necessary.

### Configuration

- Read configuration from `app/config.py`.
- Do not hardcode model names in agent definitions.
- Current defaults are `gemma-4-31b-it` for both worker and critic roles.
- Use the `config` singleton rather than creating ad hoc config objects.

### ADK agent rules

- `app/agent.py` is the source of truth for the agent graph.
- Tools should accept `root_dir` / `target_dir` when scanning the codebase.
- `search_codebase()` and `list_files()` must respect their caps.
- Keep callbacks side-effect-free outside ADK session state.
- Use `EventActions(escalate=True)` only for loop control.

### Error handling

- Return structured errors from tools where possible.
- Avoid raising raw exceptions from utility functions that are meant to be agent tools.
- Use the logger instead of ad hoc console output.

## FastAPI and Runtime Standards

- `app.fast_api_app.py` is the production wrapper, not the agent graph.
- `POST /feedback` is the only custom wrapper route currently added.
- Cloud Logging and telemetry are part of the wrapper/runtime layer.
- Keep `ALLOW_ORIGINS` support explicit when exposing the backend across origins.

## Frontend Standards

### Stack

- React 19
- Vite 6
- TypeScript 5.7
- Tailwind CSS v4 via `@tailwindcss/vite`

### Component rules

- Use functional components.
- Use PascalCase for component names.
- Keep components focused and colocated with the feature they render.
- No router is used in this app.

### UI behavior

- The app streams responses with `fetch` and a streamed reader.
- Do not document or introduce EventSource for the current runtime.
- The frontend dashboard schema is UI-specific and should be mapped explicitly from the streamed report JSON.
- Validate local paths through `/util/validate` before starting the audit flow.

### Styling

- Use Tailwind CSS v4 utility classes.
- Keep CSS-first Vite setup intact.
- Avoid introducing NativeWind or router assumptions from unrelated React Native patterns.

## Testing Standards

- Keep integration tests under `tests/integration/`.
- Keep evaluation assets under `tests/eval/`.
- Add real unit tests rather than relying on placeholder assertions.
- Do not claim frontend test coverage that does not exist.
- Verify changes against the actual runtime path, not a mocked approximation.

## Documentation Standards

- Use kebab-case filenames for evergreen docs.
- Keep docs concise and current.
- Update docs when runtime commands, ports, model defaults, or API behavior change.
- Prefer relative links inside `docs/`.
- Do not document commands that are not present in the repository.

## File Size Guidance

- Keep code files small enough to understand in one sitting.
- If a file grows too large, split by responsibility before adding more logic.
- Avoid duplicate implementations of the same helper across frontend and backend.

## Review Checklist

- [ ] Model names match `app/config.py`
- [ ] Runtime ports match `run.sh` and the Docker deployment file
- [ ] Tool caps and path rules match `app/agent.py` and `app/path_validator.py`
- [ ] Frontend API notes match `frontend/src/lib/utils.ts`
- [ ] Docs do not mention nonexistent frontend tests or router behavior
