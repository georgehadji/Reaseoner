# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Environment

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd ui-next && npm install

# Start all services (backend, frontend, search)
python start_all.py

# Start backend only
uvicorn asgi:app --reload --host 0.0.0.0 --port 8001

# Start frontend only
cd ui-next && npm run dev

# Start SearXNG search engine
docker-compose -f docker-compose.searxng.yml up -d
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run quick tests (skip slow/integration)
pytest tests/ -v -m "not slow and not integration"

# Run with coverage
pytest tests/ --cov=src/reasoner --cov-report=html

# Run a single test file
pytest tests/unit/test_activity_stream.py -v

# Parallel test execution
pytest -n auto
```

### Linting & Code Quality

```bash
# Python linting with ruff
ruff check src/reasoner/
ruff format src/reasoner/

# Frontend linting
cd ui-next && npm run lint

# Type checking (frontend)
cd ui-next && npx tsc --noEmit
```

### CLI Usage

```bash
# List available presets and models
python main.py --list-presets
python main.py --list-models

# Run a reasoning pipeline
python main.py --problem "How should we prioritize our Q3 product roadmap?" --preset debate-premium

# Load problem from file and export JSON
python main.py --problem-file problem.txt --output result.json --preset multi-perspective-premium

# Sequential mode for rate-limited environments
python main.py --problem "..." --sequential

# Adjust top-k pruning (default: 2)
python main.py --problem "..." --top-k 3

# Save and resume state
python main.py --save-state state.json --problem "..."
python main.py --resume state.json
```

### API Endpoints

- `POST /api/run` – Run pipeline (returns SSE stream)
- `POST /api/stop` – Stop active run
- `DELETE /api/cache` – Clear server cache
- `GET /api/presets` – List available presets
- `GET /api/models` – List available models
- `POST /api/run-with-context` – External context integration
- `GET /api/ui/status` – UI health check

## Architecture Overview

Reasoner is a structured AI reasoning orchestrator that runs a problem through a multi-phase pipeline and returns an executive answer plus the reasoning trail. It supports 16+ reasoning methods (Multi‑Perspective, Debate, Scientific, Socratic, Jury, Research, Pre‑Mortem, Bayesian, Dialectical, Analogical, Delphi, etc.) each with Budget/Premium preset tiers.

### High‑Level Structure

- **`src/reasoner/`** – Main Python package (modular monolith with clean‑architecture boundaries)
  - **Interface Layer** (`api/`) – FastAPI app, routing, streaming, serializers, middleware
  - **Application Layer** (`application/`) – Use cases, orchestration helpers, handlers, queries, flows, event bus
  - **Domain/Core Layer** (`domain/`, `core/`) – Domain logic, shared protocols, settings, search primitives
  - **Infrastructure Layer** (`infrastructure/`) – External adapters (LLM providers, persistence, WebSocket, widgets)
  - **Reasoning Runtime** (`pipeline.py`, `phases/`, `models.py`, `presets.py`, `llm.py`) – Pipeline orchestration, phase implementations, data models, preset definitions
  - **Specialized Subsystems** (`subagents/`, `hypergate/`, `neuro/`, `healing/`) – Focused agents, auto‑method selection, persistent memory, self‑healing
- **`ui‑next/`** – Next.js 16 / React 19 frontend (TypeScript, Tailwind CSS, Zustand)
- **`tests/`** – Pytest suite (~800 tests)
- **`cache/`, `history/`, `uploads/`** – Runtime artifacts

### Core Pipeline Flow

1. **HyperGate Pre‑Router** – 6 parallel sub‑agents detect language, complexity, directness, web‑search need, and optimal reasoning method. Simple questions are answered instantly; complex ones are routed to the full pipeline.
2. **Phase 0: Task Classification** – Classifies task type (analytical, strategic, creative, technical) and auto‑detects language.
3. **Phase 1: Problem Decomposition** – Generates ≤5 sub‑problems, assumption audit, failure modes.
4. **Phase 2: Multi‑Perspective Generation** – Constructive, Destructive, Systemic, Minimalist perspectives executed in parallel across diverse models from different labs.
5. **Phase 3: Critique & Pruning** – Independent model scores candidates 0‑10 per criterion; retains top‑k solutions.
6. **Phase 4: Stress Testing** – Evaluates under Optimal, Constraint Violation, Adversarial scenarios.
7. **Phase 5: Synthesis** – Produces `VERIFIED` / `HYPOTHESIS` / `UNKNOWN` labeled output, Action Blueprint with Go/No‑Go criteria, Meta‑Cognitive Audit.

### Architectural Invariants

- **State field pattern**: Method‑specific state uses `dict[str, Any]` fields initialized with `field(default_factory=dict)` in `PipelineState`. Accessed via `.get()`, never direct subscript. Enables `--resume` with partial/older state files.
- **Routing keys**: New methods only use existing routing roles (`primary`, `constructive`, `destructive`, `systemic`, `synthesis`). No new keys added to avoid bloated preset validation.
- **Phase dispatch**: New `_run_*_pipeline()` methods in `pipeline.py` detected by preset name in `_get_method_from_preset()`.
- **Async gather safety**: All parallel LLM calls use `asyncio.gather(*tasks, return_exceptions=True)` + per‑task exception checking.
- **JSON extraction**: All LLM responses parsed via `parsing.extract_json()`, never direct JSON parsing.

### Model Routing Philosophy

- **Cross‑Lab Diversity**: Different model families prevent echo chambers. Phase 2 uses ≥3 different labs in Budget, ≥4 in Premium.
- **Fallbacks**: Failures fall back to a cross‑lab equivalent, not automatically to the preset primary.
- **Scoring**: Scorer must be from a different ecosystem than the dominant Phase‑2 generator.

## Important Implementation Notes

- `presets.py` is the source of truth for routing and preset metadata.
- `renderer.py` and `pipeline.py` are method‑aware and must stay aligned with preset naming.
- `llm.py` contains provider‑specific handling, including guarded structured‑output behavior for Perplexity.
- `neuro/` handles persistent memory and context optimization (`neuro/compression.py` provides Neuro‑Squeeze token optimization).
- `core/search.py` provides web discovery with source‑type filtering (general, academic, social, news, code).
- `scraper.py` provides web scraping for deep‑reading phase.

## Known Operational Realities

- Missing API keys are common and surfaced in the UI and `/api/presets`.
- Rate limits still matter on multi‑call methods; use `--sequential` when needed.
- `Research / Premium` is the heaviest path and uses `sonar‑deep‑research`.
- CLI default preset is still `claude‑only`; UI default is `basic‑budget`.

## Reliability Fixes (Do Not Re‑introduce)

A set of 21 reliability fixes were applied (2026‑03‑15, branch: security‑fixes‑implementation). The full table is in the previous CLAUDE.md snapshot. Key patterns to avoid:

- `asyncio.gather()` without `return_exceptions=True`
- Direct subscript access on `dict` keys without `.get()` guards
- Missing `isinstance(list)` guards when slicing `data.get("queries", [])`
- Using `CritiqueScore(**s)` without default values for required fields
- Global cancellation flags shared across concurrent SSE requests

## Workflow Orchestration (for Claude Code)

1. **Plan First** – Enter plan mode for any non‑trivial task (3+ steps or architectural decisions). Write specs to `../tasks/todo.md`.
2. **Subagent Strategy** – Use subagents liberally to keep main context window clean. Offload research, exploration, and parallel analysis.
3. **Self‑Improvement Loop** – After any correction from the user, update `../tasks/lessons.md` with the pattern.
4. **Verification Before Done** – Never mark a task complete without proving it works (tests, logs, diffs).
5. **Demand Elegance** – For non‑trivial changes, pause and ask “is there a more elegant way?”
6. **Autonomous Bug Fixing** – When given a bug report, just fix it. Point at logs, errors, failing tests – then resolve them.

## Core Principles

- **Simplicity First** – Make every change as simple as possible. Impact minimal code.
- **Root Causes** – Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact** – Changes should only touch what’s necessary. Avoid introducing bugs.

---

*For a detailed product snapshot, reasoning methods, and preset tiers, see the previous version of this file.*