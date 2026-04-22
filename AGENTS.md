# AGENTS.md — Reasoner (ARA Pipeline v2.2)

> This file is written for AI coding agents. It assumes you know nothing about this project.
> Read this first before making any changes.

---

## 1. Project Overview

**Reasoner** (also called ARA — Adaptive Reasoning Architecture) is a production-grade AI reasoning orchestrator written in Python with a Next.js frontend. It decomposes complex problems into structured multi-phase pipelines, leverages multiple LLMs from diverse training ecosystems in parallel, applies independent critique, stress-tests solutions, and synthesizes actionable recommendations with epistemic labeling.

- **Version:** 2.1.0 (Python package), v2.2 (project)
- **Python:** 3.12+
- **License:** MIT

### What This Project Is NOT

It is not a chatbot. It is a **reasoning orchestrator** that treats reasoning as a first-class engineering problem: classify → decompose → vet context → generate (parallel, cross-lab) → critique → stress-test → synthesize → epistemic label → action blueprint.

---

## 2. Technology Stack

### Backend
| Layer | Technology |
|-------|------------|
| Runtime | Python 3.12+ |
| Web Framework | FastAPI 0.109+ with uvicorn |
| Data Validation | Pydantic v2 |
| HTTP Client | httpx |
| LLM Routing | OpenRouter (primary, 350+ models); direct adapters for Anthropic, OpenAI, Google, Perplexity, DeepSeek, Mistral, xAI, Qwen, Kimi, GLM, MiniMax, Ollama |
| Search | SearXNG (self-hosted via Docker Compose), Perplexity Sonar |
| Database | SQLite (event store), PostgreSQL support via asyncpg, aiosqlite for async SQLite |
| File Processing | PyPDF2, python-docx |
| Web Scraping | newspaper3k, lxml |
| Financial Data | yfinance, yahooquery |
| Math | simpleeval |
| Memory/Cache | Custom token cache, Neuro-based long-term memory with embedding search |
| Security | Custom auth manager, token-bucket rate limiter, circuit breaker, input sanitization, prompt-injection filtering |

### Frontend (`ui-next/`)
| Layer | Technology |
|-------|------------|
| Framework | Next.js 16 (App Router) |
| UI Library | React 19 |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 |
| State | Zustand (client), SWR (server) |
| Persistence | IndexedDB via `idb` |
| Markdown | react-markdown, react-syntax-highlighter, remark-gfm, rehype-highlight |
| Icons | lucide-react |
| Testing | Vitest, @testing-library/react, @playwright/test |

---

## 3. Project Structure

### Root Layout
```
Reasoner/
├── main.py                 # CLI entry-point shim → reasoner.main
├── api.py                  # Backward-compat API shim
├── pipeline.py             # Backward-compat pipeline shim
├── llm.py                  # Backward-compat LLM shim
├── models.py               # Backward-compat models shim
├── phases.py               # Backward-compat phases shim
├── presets.py              # Backward-compat presets shim
├── renderer.py             # Backward-compat renderer shim
├── parsing.py              # Backward-compat parsing shim
├── scraper.py              # Backward-compat scraper shim
├── gate_agent.py           # Legacy GateAgent + HyperGateAgent lazy import
├── asgi.py                 # ASGI entry point: uvicorn asgi:app --reload --port 8000
├── start_all.py            # Orchestrator shim
├── requirements.txt        # Python dependencies
├── pytest.ini              # Test configuration
├── .env / .env.example     # Environment variables (NEVER commit .env)
├── docker-compose.searxng.yml   # SearXNG container setup
├── tests/                  # 60+ pytest files
├── src/reasoner/           # Main Python package
├── ui-next/                # Next.js frontend
├── cache/                  # Run-related cache
├── docs/                   # Markdown documentation
├── healing/                # Self-healing codebase (introspection, test generation)
└── .github/workflows/      # CI/CD (self-healing-ci.yml)
```

### Backend Source (`src/reasoner/`)
```
src/reasoner/
├── __init__.py                    # Package init; __version__ = "2.1.0"
├── main.py                        # CLI entry point with argparse
├── pipeline.py                    # ARAPipeline orchestrator
├── models.py                      # Core dataclasses: PipelineState, enums, etc.
├── core/                          # Domain core abstractions
│   ├── protocol.py                # PhaseConfig, PhaseResult, Phase Protocol
│   ├── constants.py               # Token budgets, defaults, truncation rules
│   ├── settings.py                # Pydantic-settings from .env
│   ├── temperatures.py            # Per-phase temperature maps
│   ├── search.py                  # Discovery client for web search
│   ├── memory.py                  # Memory abstractions
│   ├── perspectives.py            # Perspective definitions
│   ├── events/                    # Domain events (event sourcing)
│   └── aggregates/                # Pipeline aggregate root
├── domain/                        # Domain logic
│   ├── preset_core.py             # Preset data structures
│   └── preset_registry.py         # Preset definitions and resolution
├── application/                   # Application layer
│   ├── event_bus/                 # In-memory event bus
│   ├── flows/                     # Pipeline flows
│   ├── handlers/                  # Event handlers
│   ├── mixins/                    # Method-specific mixins (debate, jury, research, etc.)
│   └── services/                  # Preset service, search service, renderers
├── phases/                        # 16+ reasoning method implementations
│   ├── multi_perspective.py
│   ├── debate.py
│   ├── jury.py
│   ├── research.py
│   ├── scientific.py
│   ├── socratic.py
│   ├── pre_mortem.py
│   ├── bayesian.py
│   ├── dialectical.py
│   ├── analogical.py
│   ├── delphi.py
│   ├── cove.py
│   ├── sot.py
│   ├── tot.py
│   ├── pot.py
│   ├── self_discover.py
│   └── writing.py
├── infrastructure/                # Infrastructure layer
│   ├── llm/                       # LLM abstraction
│   │   ├── base.py
│   │   ├── ports.py               # BaseLLMProvider, LLMResponse, LLMConfig, Message
│   │   ├── registry.py            # Model registry (_REGISTRY)
│   │   ├── router.py              # ProviderRouter
│   │   ├── providers/             # Provider adapters (OpenRouter compat)
│   │   └── extraction/            # JSON extraction utilities
│   ├── persistence/               # Event store, postgres, snapshots
│   ├── websocket/                 # WebSocket manager
│   └── widgets/                   # Widget registry (calculator, stocks, weather, etc.)
├── api/                           # FastAPI application
│   ├── __init__.py                # App factory, CORS, rate limiter, security middleware
│   ├── routes/                    # REST/SSE routes (pipelines, widgets, uploads, etc.)
│   ├── schemas.py
│   ├── serializers.py
│   ├── streaming.py
│   ├── middleware.py
│   ├── auth_deps.py
│   ├── cache.py
│   ├── history.py
│   └── run_state.py
├── hypergate/                     # HyperGate pre-router
│   ├── hyperagent.py
│   ├── base_sub_agent.py
│   ├── models.py
│   └── sub_agents/                # language, complexity, direct, web, method, tie-breaker
├── subagents/                     # Phase sub-agents
│   ├── enhancement/
│   ├── decomposition/
│   ├── critique/
│   ├── search/
│   └── synthesis/
├── neuro/                         # Long-term memory system
│   ├── server.py                  # Neuro API router (Recall, Learn endpoints)
│   ├── cache.py
│   ├── compression.py             # smart_compress, Aggressive/Minimal modes
│   ├── providers.py
│   ├── sessions.py
│   ├── config.py
│   └── cli.py
├── healing/                       # Self-healing (introspection, test generation)
│   ├── introspection_engine.py
│   ├── test_generation_engine.py
│   └── generated_tests/           # Auto-generated pytest files
└── [utility modules]
    ├── auth.py                    # Token-based auth with scopes
    ├── rate_limiter.py            # Token bucket rate limiter
    ├── circuit_breaker.py         # Circuit breaker pattern
    ├── exceptions.py              # Custom exceptions
    ├── sanitization.py            # Input sanitization / prompt-injection defense
    ├── token_cache.py             # Token-aware caching
    ├── pricing.py                 # Cost estimation
    ├── suggestions.py             # Smart search suggestions
    ├── logging_utils.py
    └── widgets.py                 # Legacy widget helpers
```

### Frontend Source (`ui-next/src/`)
```
ui-next/src/
├── app/                           # Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   ├── providers.tsx
│   └── api/                       # API route handlers (proxies to FastAPI)
│       ├── run/route.ts
│       ├── stop/route.ts
│       ├── presets/route.ts
│       ├── search/route.ts
│       ├── calculate/route.ts
│       ├── stocks/route.ts
│       ├── weather/route.ts
│       ├── upload/route.ts
│       ├── generate-image/route.ts
│       ├── cache/route.ts
│       └── csrf/route.ts
├── components/
│   ├── chat/                      # ChatFeed, ChatMessage, MarkdownRenderer, TypewriterMarkdown
│   ├── layout/                    # Composer, PhaseTimeline, Sidebar, ShortcutModal
│   ├── phases/                    # ClassificationCard, CritiqueCard, PhaseCard, PhaseRenderer, SynthesisCard
│   ├── ui/                        # Badge, Button, Spinner, ThemeToggle
│   └── widgets/                   # CalculationWidget, StockWidget, WeatherWidget
├── hooks/                         # useConversationHistory, useKeyboardShortcuts, usePipelineStream, etc.
├── lib/                           # api-client, config, db (IndexedDB), types, utils, security
├── stores/
│   └── app-store.ts               # Zustand store with persistence
└── proxy.ts
```


Read: ARCHITECTURE_MINDMAP.md
---

## 4. Build, Test, and Development Commands

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI
python main.py --list-presets
python main.py --list-models
python main.py --problem "..." --preset <id> [--top-k N] [--sequential] [--source-type <type>]
python main.py --resume state.json

# Start API server
uvicorn asgi:app --reload --port 8000

# Run tests
python -m pytest -v
python -m pytest test_parsing.py test_models.py test_perplexity_config.py
python -m pytest -m "not slow"          # Skip slow tests
python -m pytest --run-slow             # Include slow tests
```

### Frontend
```bash
cd ui-next
npm install
npm run dev          # Development server (http://localhost:3000)
npm run build        # Production build
npm run lint         # ESLint
```

### Full Stack (Local)
```bash
# One-command start (backend + frontend + SearXNG)
python start_all.py

# Or individually:
uvicorn asgi:app --reload --port 8001
docker compose -f docker-compose.searxng.yml up -d
cd ui-next && npm run dev
```

### SearXNG (Search)
```bash
docker compose -f docker-compose.searxng.yml up -d
# Available at http://localhost:8888
```

---

## 5. Code Style & Naming Conventions

### Python
- **Indentation:** 4 spaces
- **Functions/variables/modules:** `snake_case`
- **Dataclasses, enums, test classes:** `PascalCase`
- **Type hints:** Prefer type hints when intent is unclear
- **Docstrings:** Use triple-double-quote docstrings for modules and public functions
- **Imports:** `from __future__ import annotations` at the top of files when using modern typing

### TypeScript / Frontend
- **Components:** PascalCase files, default export for page components
- **Hooks:** `useCamelCase`
- **Styling:** Tailwind CSS v4 utility classes
- **Accent colors:** Preserve the `--method-accent-rgb` CSS custom property when adjusting gradients or glass panels
- **UI blocks:** Document new helper UI blocks in the same file rather than scattering markup elsewhere

---

## 6. Testing Strategy

- **Framework:** pytest with pytest-asyncio, pytest-timeout
- **Location:** `tests/` directory at repo root
- **Naming:** `test_*.py` files, `Test…` classes
- **Markers:**
  - `slow` — deselect with `-m "not slow"`
  - `integration` — integration tests
  - `timeout` — tests with timeout threshold
  - `searxng` — tests requiring a live SearXNG instance
- **Fixtures:** Defined in `tests/conftest.py` (sample_pipeline_state, mock_llm_response, searxng_container, temp_event_store, etc.)
- **Coverage target:** ~70%, minimum gate 60%
- **Guidelines:**
  - Add regression coverage when fixing parsing, routing, or UI rendering bugs
  - Assert on both happy and fallback paths
  - Use `pytest --run-slow` to include slow tests

---

## 7. Configuration & Environment

### Required Environment Variables (`.env`)
Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Primary LLM access (recommended single key) |
| `OPENAI_API_KEY` | Direct OpenAI access (optional) |
| `ANTHROPIC_API_KEY` | Direct Anthropic access (optional) |
| `GOOGLE_API_KEY` | Direct Google Gemini access (optional) |
| `DEEPSEEK_API_KEY` | Direct DeepSeek access (optional) |
| `MISTRAL_API_KEY` | Direct Mistral access (optional) |
| `XAI_API_KEY` | Direct xAI Grok access (optional) |
| `PERPLEXITY_API_KEY` | Perplexity Sonar access (optional) |
| `DASHSCOPE_API_KEY` | Alibaba Qwen access (optional) |
| `MOONSHOT_API_KEY` | Moonshot Kimi access (optional) |
| `ZHIPUAI_API_KEY` | ZhipuAI GLM access (optional) |
| `ADMIN_API_KEY` | Required for production admin endpoints |
| `SEARXNG_URL` | SearXNG instance URL (default: http://localhost:8888) |
| `DEBUG` | Must be `false` in production |
| `SERVER_HOST` / `SERVER_PORT` | FastAPI bind address |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_HOUR` / `RATE_LIMIT_BURST` | Rate limiter config |

**NEVER commit `.env` with real values.**

---

## 8. Security Considerations

- **Input Sanitization:** All user inputs pass through `reasoner.sanitization.sanitize_for_prompt()` before reaching LLM prompts
- **Prompt Injection Defense:** Layered filtering in sanitization module + adversarial persuasion defense (`ara_persuasion_defense.py`)
- **Rate Limiting:** Token-bucket rate limiter per client IP (`rate_limiter.py`)
- **Authentication:** Token-based auth with scoped permissions (`auth.py`)
- **Circuit Breaker:** Automatic fallback when providers fail (`circuit_breaker.py`)
- **CSRF Protection:** CSRF token endpoints for state-changing operations
- **Security Headers:** X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS (production)
- **CORS:** Restricted to known origins (`localhost:8000/8001`)

---

## 9. Architecture Patterns

1. **Event Sourcing** — Pipeline state derived from domain events stored in SQLite
2. **CQRS** — Separate command and query handlers
3. **Hexagonal Architecture** — Domain depends on protocols (Widget, Phase), not concrete implementations
4. **Mixin Pattern** — Method-specific behaviors composed via mixins (DebateMixin, JuryMixin, etc.)
5. **Provider Router with Fallbacks** — Cross-lab diversity with automatic fallback on failure
6. **HyperGate Pre-Routing** — 6 parallel sub-agents detect language, complexity, directness, web need, and optimal method
7. **Token Optimization** — Phase-specific budgets, context compression, caching
8. **Security in Depth** — Input sanitization, prompt injection filtering, rate limiting, scoped auth, CSRF protection

---

## 10. Working with Neuro & Compression

- **Recall (Bootstrap):** `neuro.server.create_neuro_router()` provides the `Recall` endpoint. Automatically called in `ARAPipeline.run` to fetch relevant context from long-term memory.
- **Learn (Ingest):** The `Learn` endpoint is called at the end of the pipeline to save the final synthesis. Tag entries with metadata (e.g., `preset`, `task_type`).
- **Compression:** Use `neuro.compression.smart_compress(text, ext, level)` to reduce token usage. Modes:
  - `Aggressive` — structural analysis, keeps only signatures
  - `Minimal` — general cleanup
- **Tenant Isolation:** Use `agent_id` in Neuro requests to ensure data is stored in separate directories (`~/.neuro/agents/<id>`).

---

## 11. Reasoning Methods (16+)

The pipeline supports 16+ reasoning methodologies. Each method has its own phase module and renderer:

1. **Multi-Perspective** — Parallel constructive/destructive/systemic/minimalist analysis
2. **Debate** — Adversarial reasoning with opening, rebuttal, judge phases
3. **Jury** — Expert panel with generator, critic, verifier roles
4. **Research** — Web-grounded iterative RAG with deep discovery
5. **Scientific** — Hypothesis generation and falsification
6. **Socratic** — Deep questioning through dialectic
7. **Pre-Mortem** — Risk analysis via future failure simulation
8. **Bayesian** — Belief updating with probabilistic reasoning
9. **Dialectical** — Thesis-antithesis-synthesis
10. **Analogical** — Cross-domain analogy mapping
11. **Delphi** — Expert panel consensus (structured)
12. **CoVE** — Chain-of-Verification
13. **SoT** — Skeleton-of-Thought
14. **ToT** — Tree-of-Thoughts
15. **PoT** — Program-of-Thoughts
16. **Self-Discover** — Dynamic reasoning module composition
17. **Writing** — Creative writing with hallucination guards

---

## 12. Presets & Model Routing

Presets define which models are used for each phase role. The UI orders methods (and their Budget → Balanced → Premium presets) from most cost-effective to least and defaults to the first method/preset.

- **Budget** — Cheapest models, fastest
- **Balanced** — Mid-tier quality/cost tradeoff
- **Premium** — Best available models

Key commands:
```bash
python main.py --list-presets      # Show all presets + key status
python main.py --list-models       # Show all model IDs grouped by ecosystem
```

---

## 13. CI/CD

- **File:** `.github/workflows/self-healing-ci.yml`
- **Triggers:** Push to `main`/`develop`, PRs to `main`, nightly cron (2 AM), manual dispatch
- **Jobs:**
  - `healing-profile` — baseline coverage, doc gaps, monitoring gaps
  - `loop1-static-healing` — introspection engine + test generation + coverage gating (60% fail, 80% warn)
  - `loop2-runtime-healing` — circuit breaker + health checks + smoke tests
  - `loop3-evolutionary-healing` — failure patterns, spec drift, optimization proposals
  - `searxng-integration` — SearXNG integration tests
  - `healing-verification` — artifact verification

---

## 14. Commit & Pull Request Guidelines

- Follow short, imperative subjects with Conventional prefixes (`feat:`, `fix:`, `docs:`, etc.)
- Describe UI changes (screenshots if layout shifts) and note commands you ran
- When the feature touches presets, methods, or docs, mention CRITICAL API keys or `.env` expectations in the PR
- Update `README.md`, `CLAUDE.md`, and `QWEN.md` whenever new stages, methods, or UI affordances ship

---

## 15. Workflow Orchestration (Agent Guidelines)

### Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- One task per subagent for focused execution

### Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Review lessons at session start for relevant project

### Verification Before Done
- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- Ask yourself: "Would a staff engineer approve this?"

### Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky, implement the elegant solution
- Skip this for simple, obvious fixes — don't over-engineer

### Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them

---

## 16. Task Management

1. **Plan First:** Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan:** Check in before starting implementation
3. **Track Progress:** Mark items complete as you go
4. **Explain Changes:** High-level summary at each step
5. **Document Results:** Add review section to `tasks/todo.md`
6. **Capture Lessons:** Update `tasks/lessons.md` after corrections

---

## 17. Core Principles

- **Simplicity First:** Make every change as simple as possible. Impact minimal code.
- **Root Causes:** Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact:** Changes should only touch what's necessary. Avoid introducing bugs.
