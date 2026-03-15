# Vibe-Coding Reasoner

This file is a short project snapshot for agent sessions. The main product documentation lives in `README.md`.

## Current product shape

Reasoner is a structured AI reasoning app, not a general-purpose chatbot. It runs a problem through a multi-phase pipeline and returns an executive answer plus the reasoning trail.

Current methods:

- `Multi-Perspective`
- `Iterative`
- `Debate`
- `Scientific`
- `Socratic`
- `Jury`
- `Research`

Current UI preset tiers:

- `Multi-Perspective`: `basic-budget` → `cost-efficient` → `epistemic-diversity` → `western-only` → `max-quality` (cycles through all 5)
- `Iterative`: `iterative-budget` → `iterative-balanced` → `iterative-premium`
- `Debate`: `debate-budget` → `debate-balanced` → `debate-premium`
- `Scientific`: `scientific-budget` → `scientific-premium`
- `Socratic`: `socratic-budget` → `socratic-premium`
- `Jury`: `jury-budget` → `jury-balanced` → `jury-premium`
- `Research`: `research-budget` → `research-balanced` → `research-premium`

Backward-compatible aliases still resolve for older names such as `evolutionary*` and `orchestrated*`.

## What the app can do

- Run structured reasoning with method-specific prompts and renderers
- Mix providers by phase and by role
- Use grounded Perplexity models where grounding helps
- **Iterative RAG**: Universal context vetting phase with iterative loop (LLM decides if more searches needed)
- **Specialized Source Types**: Filter searches by general, academic, social, news, code
- **Deep read_file Phase**: Automatically fetch full content from critical sources
- **External Context API**: API endpoint for microservices architecture with external context
- Show answer-first output in the browser UI
- Stream phase results live over SSE
- Export results as JSON or Markdown
- Save browser history in IndexedDB
- Cache server responses in `cache/`
- Save and resume CLI state files
- Stop active runs from the UI

## Current UI behavior

- Default method: `Multi-Perspective`
- Default preset: `Budget` (`basic-budget`)
- Methods are ordered from more cost-effective to less cost-effective
- Presets are shown as `Budget`, `Balanced`, `Premium`
- Phase cards render vertically in order and `Synthesis` appears last
- The composer shows method-specific guidance plus preset details

## Current CLI/API behavior

CLI:

```bash
python main.py --list-presets
python main.py --list-models
python main.py --problem "..." --preset max-quality
python main.py --problem "..." --preset basic-budget
python main.py --problem "..." --preset research --top-k 3 --sequential
python main.py --problem "..." --source-type academic  # specialized sources
python main.py --problem-file problem.txt --output result.json
python main.py --save-state state.json --problem "..."
python main.py --resume state.json
```

API:

- `POST /api/run`
- `POST /api/stop`
- `DELETE /api/cache`
- `GET /api/presets`
- `GET /api/models`
- `POST /api/run-with-context` (external context integration)
- `GET /api/ui/status`

## Important implementation notes

- `ui/index.html` is the entire browser app: HTML, CSS, and JS in one file.
- `README.md` is the source of truth for capabilities and operator-facing usage.
- `presets.py` is the source of truth for routing and preset metadata.
- `neuro/` handles persistent memory and context optimization.
- `neuro/compression.py` provides Neuro-Squeeze token optimization.
- `renderer.py` and `pipeline.py` are method-aware and must stay aligned with preset naming.
- `llm.py` contains provider-specific handling, including guarded structured-output behavior for Perplexity.
- `scraper.py` provides web scraping for deep reading phase.
- `core/search.py` provides web discovery with source type filtering (general, academic, social, news, code).

## Known operational realities

- Missing API keys are common and surfaced in the UI and `/api/presets`.
- Rate limits still matter on multi-call methods; use sequential mode when needed.
- `Research / Premium` is the heaviest path and uses `sonar-deep-research`.
- CLI default preset is still `claude-only`; UI default is `basic-budget`.

## Reliability fixes applied (2026-03-15, branch: security-fixes-implementation)

All fixes are committed and pushed. Do not re-introduce these patterns:

| # | File(s) | What was wrong | What was fixed |
|---|---------|----------------|----------------|
| 1 | `pipeline.py` | 5 `asyncio.gather()` calls missing `return_exceptions=True` — single LLM failure silently emptied entire phase | Added per-task exception handling with `state.errors` logging |
| 2 | `models.py` | `CritiqueScore` missing `confidence_vs_accuracy_penalty: float` — `TypeError` on every phase-3 run | Added field with `default=0.0` |
| 3 | `pipeline.py` | `SolutionCandidate(content=data.get("core_analysis"))` — `None` propagates to `c.content[:400]` | Guarded: `data.get(...) or ""` |
| 4 | `pipeline.py` | `_phase_debate_rebuttal` indexed `statements[0/1]` without length guard | Early-return guard if `len(statements) < 2` |
| 5 | `phases.py` | `CROSS_VERIFICATION_SYSTEM` and `cross_verification_prompt()` called but not defined — recovery path dead | Added both to `phases.py` |
| 6 | `pipeline.py` | Missing `import json`, `from dataclasses import asdict`; `.to_dict()` called on plain dataclasses | Added imports; replaced `.to_dict()` with `asdict()` |
| 7 | `main.py` | 7 unterminated string/f-string literals — CLI `SyntaxError` on startup | Fixed all with `\n` escape sequences |
| 8 | `api.py` | Global `_cancel_flag: bool` shared across concurrent SSE requests — one stop cancels all | Per-run `_cancelled_runs: dict[str,bool]` keyed by `uuid4()` |
| 9 | `renderer.py` | TOCTOU: `.get("key")` check then `["key"]` subscript — not atomic | Stored `.get()` in local variable before iterating |



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
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
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
1. **+*Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **+*Verify Plan**: Check in before starting implementation
3. **+*Track Progress**: Mark items complete as you go
4. **+*Explain Changes**: High-level summary at each step
5. **+*Document Results**: Add review section to `tasks/todo.md`
6. **+*Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles
- **+*Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **+*Root Causes**: Find root causes. No temporary fixes. Senior developer standards.
- **+*Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
