# Repository Guidelines

## Project Structure & Module Organization
- The Python entry points live at the repo root: `main.py` (CLI), `api.py` (FastAPI/SSE server), `pipeline.py` (phase runner), `llm.py` (provider router), `models.py`, `phases.py`, and supporting modules such as `parsing.py`, `renderer.py`, `presets.py`, and `scraper.py`.
- Shared protocol helpers live under `core/`. The canonical browser interface is `ui-next/` (Next.js/React/TypeScript). Run-related cache belongs in `cache/`, and `.env` should never be committed.
- Tests live at the repo root as `test_*.py` files and target parsing, model routing, and preset configuration logic.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` (or the short list in `../README.md`) to pull in FastAPI, providers, and utility libs before running anything locally.
- `python main.py --list-presets` and `python main.py --list-models` to inspect routing metadata.
- `python main.py --problem "..." --preset <id> [--top-k N] [--sequential] [--source-type <type>]` and `python main.py --resume state.json` cover CLI runs; keep `--sequential` handy for rate‑limited providers. Use `--source-type` to filter searches by category (general, academic, social, news, code).
- `uvicorn asgi:app --reload --port 8000` boots the API server, and the Next.js frontend is started separately via `npm run dev` in `ui-next/` (typically `http://localhost:3000`).
- `python -m pytest -v` is the full test suite; focus runs such as `python -m pytest test_parsing.py test_models.py test_perplexity_config.py` are encouraged when touching those areas.

## Coding Style & Naming Conventions
- Use 4-space indentation, expressive `snake_case` for functions/vars/modules, and `PascalCase` for dataclasses, enums, and test classes. Prefer type hints when the intent is unclear.
- `ui-next/` uses React, TypeScript, Tailwind CSS, and modern component patterns. Preserve the accent color hook (`--method-accent-rgb`) when you adjust gradients or glass panels.
- Document new helper UI blocks in the same file rather than scattering markup elsewhere.

## Testing Guidelines
- `pytest` remains the tool of choice. Name files `test_*.py` and wrap related cases in `Test…` classes. Add regression coverage whenever fixing parsing, routing, or UI rendering bugs, and assert on both happy and fallback paths.

## Working with Neuro & Compression
- **Recall (Bootstrap):** Use `neuro.server.create_neuro_router()` to access the `Recall` endpoint. This is automatically called in `ARAPipeline.run` to fetch relevant context from long-term memory.
- **Learn (Ingest):** Similarly, the `Learn` endpoint is called at the end of the pipeline to save the final synthesis. Use metadata to tag these entries (e.g., `preset`, `task_type`).
- **Compression:** Always consider context density. Use `neuro.compression.smart_compress(text, ext, level)` to reduce token usage. Neuro-Squeeze provides `Aggressive` mode for structural analysis (keeping only signatures) and `Minimal` for general cleanup.
- **Tenant Isolation:** Use `agent_id` in Neuro requests to ensure data is stored in separate directories (`~/.neuro/agents/<id>`).

## Commit & Pull Request Guidelines

- Follow short, imperative subjects with Conventional prefixes (e.g., `feat:`, `fix:`, `docs:`). Describe UI changes (screenshots if layout shifts) and note commands you ran.
- When the feature touches presets, methods, or docs, mention the CRITICAL API keys or `.env` expectations in the PR.

## Method & Preset Expectations
- The UI orders methods (and their Budget → Balanced → Premium presets) from most cost-effective to least and defaults to the first method/preset. Each method shows a short description next to the composer, and both the Top-K input and Sequential toggle explain their behavior inline.
- Keep the presets dropdown, chips, and run-summary footer consistent with these labels and avoid showing legacy aliases unless the CLI or backend requires them.

## Documentation Expectations
- Update `../README.md`, `CLAUDE.md`, and `QWEN.md` whenever new stages, methods, or UI affordances ship. If you adjust how methods are described, mention the change in this guide too so contributors know where to signal on the UI.

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `../tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management
1. **+*Plan First**: Write plan to `../tasks/todo.md` with checkable items
2. **+*Verify Plan**: Check in before starting implementation
3. **+*Track Progress**: Mark items complete as you go
4. **+*Explain Changes**: High-level summary at each step
5. **+*Document Results**: Add review section to `../tasks/todo.md`
6. **+*Capture Lessons**: Update `../tasks/lessons.md` after corrections

## Core Principles
- **+*Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **+*Root Causes**: Find root causes. No temporary fixes. Senior developer standards.
- **+*Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
