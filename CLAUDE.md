# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Project Overview

**Reasoner** (Adaptive Reasoning Architecture) is a production-grade AI reasoning orchestrator that decomposes complex problems into structured multi-phase pipelines, leverages 90+ LLM models from diverse training ecosystems in parallel, applies independent critique, stress-tests solutions, and synthesizes actionable recommendations with epistemic labeling (`VERIFIED` / `HYPOTHESIS` / `UNKNOWN`).

- **Version:** 2.2 (Python package 2.1.0)
- **Python:** 3.12+ | **Frontend:** Next.js 16 / React 19 / TypeScript 5
- **License:** MIT

> This is not a chatbot. Reasoning is a first-class engineering problem: classify → decompose → vet context → generate (parallel, cross-lab) → critique → stress-test → synthesize → epistemic label → action blueprint.

### Architecture Style

Hexagonal DDD + CQRS + Event Sourcing + Mixin Composition. The `PipelineState` (~60 fields) is the primary state model. `PipelineAggregate` provides event-sourced state replay.

**Dependency Rule:** Dependencies point inward — Domain has no outer dependencies, Application depends on Domain/Core but not Infrastructure, Infrastructure implements ports defined in Core.

**Known violations:** `domain/preset_core.py` imports from `infrastructure.llm.registry`. `api/streaming.py` directly instantiates `ReasonerPipeline` rather than routing through CQRS handlers. `application/flows/__init__.py` imports from `api.serializers`.

---

## 2. Technology Stack

### Backend
| Layer | Technology |
|-------|------------|
| Runtime | Python 3.12+, FastAPI 0.109+, uvicorn, Pydantic v2 |
| HTTP | httpx |
| LLM Routing | OpenRouter (primary, 350+ models); 12 direct adapters (Anthropic, OpenAI, Google, Perplexity, DeepSeek, Mistral, xAI, Qwen, Kimi, GLM, MiniMax, Ollama) |
| Search | SearXNG (Docker), Perplexity Sonar |
| Database | SQLite (event store), PostgreSQL (asyncpg), aiosqlite |
| Memory | Custom token cache, Neuro L1/L2/L3 tiered cache with embedding search |
| Security | Auth, rate limiter, circuit breaker, input sanitization, prompt-injection defense |

### Frontend (`ui-next/`)
| Layer | Technology |
|-------|------------|
| Framework | Next.js 16 (App Router), React 19 |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 |
| State | Zustand v5 (client), SWR v2 (server) |
| Persistence | IndexedDB via `idb` v8 |
| Markdown | react-markdown, react-syntax-highlighter, remark-gfm, rehype-highlight |

**Critical:** Tailwind CSS v4 does **NOT** use `tailwind.config.ts`. Configuration is CSS-native via `@import "tailwindcss"` in `globals.css` and the `@tailwindcss/postcss` PostCSS plugin. Do not create `tailwind.config.ts`.

---

## 3. Project Structure

```
src/reasoner/
├── api/                      # FastAPI HTTP/SSE interface (~30 endpoints)
│   ├── __init__.py           # App factory, CORS, middleware, route mounting
│   ├── streaming.py          # Core SSE: run_stream(), run_followup_stream(), run_stream_cached()
│   ├── serializers.py        # SSE serialization by phase (_ser_0 through _ser_5)
│   ├── schemas.py            # Pydantic request/response models
│   ├── middleware.py         # Security headers, memory limits, timeouts
│   ├── auth_deps.py          # Auth dependencies with scoped permissions
│   └── routes/               # Modular route handlers (pipelines, uploads, websocket, etc.)
├── application/              # CQRS commands, queries, event bus, flows, mixins
│   ├── flows/                # build_default_flow_registry() — binds 17 methods to ReasonerPipeline
│   ├── handlers/             # RunPipelineCommandHandler, ResumePipelineCommandHandler, etc.
│   ├── mixins/               # 12 method-specific mixins (debate, jury, research, etc.)
│   └── services/             # PresetService, SearchService, RendererService
├── core/                     # Domain core: protocols, constants, settings, events, aggregates
│   ├── protocol.py           # PhaseConfig, PhaseResult, Phase Protocol
│   ├── constants.py          # Token budgets, defaults, truncation rules, HyperGate thresholds
│   ├── search.py             # DiscoveryClient (SearXNG + BM25), PerplexitySearchClient
│   ├── memory.py             # TaggedMemory (JSONL-based)
│   ├── events/               # DomainEvent hierarchy + make_event() factory
│   └── aggregates/           # PipelineAggregate (event-sourced), WidgetAggregate
├── domain/                   # PresetCore, PresetRegistry — declarative routing configs
│   ├── preset_core.py        # _KNOWN_ROUTING_ROLES, PipelinePreset, build_auto_preset()
│   └── preset_registry.py     # 42 preset configs with model routing and fallbacks
├── infrastructure/           # Adapters: LLM providers, persistence, websocket, widgets
│   ├── llm/
│   │   ├── ports.py          # Hexagonal ports: LLMProvider Protocol, Message, LLMResponse
│   │   ├── registry.py       # _MODEL_WHITELIST (90+ models), _REGISTRY, build_provider()
│   │   ├── router.py         # ProviderRouter: role-based routing, fallback chain
│   │   ├── providers/        # OpenAICompatibleProvider, OpenRouterProvider
│   │   └── extraction/       # Vision LLM image description/OCR
│   ├── persistence/          # EventStore (SQLite), snapshots, postgres_store
│   └── websocket/            # WebSocket connection manager
├── pipeline.py               # ReasonerPipeline orchestrator (902 lines + 11 mixins)
├── models.py                 # PipelineState (~60 fields), CostTrackingState, ConversationState
├── phases/                   # 19 prompt modules (_shared, _universal, 17 methods)
├── hypergate/                # HyperGate pre-router: 5 parallel sub-agents + TieBreaker
│   ├── hyperagent.py         # HyperGateAgent orchestrator
│   ├── base_sub_agent.py     # Abstract base
│   └── sub_agents/           # language, complexity, direct, web, method, tie-breaker
├── subagents/                # Phase sub-agents (enhancement, decomposition, critique, synthesis, search)
├── neuro/                    # Long-term memory: server.py, L1/L2/L3 cache, compression, sessions
├── healing/                  # Self-healing: introspection_engine, test_generation_engine, generated_tests/
└── [utility modules]
    ├── auth.py               # Token-based auth with scopes
    ├── rate_limiter.py       # Token-bucket rate limiter
    ├── circuit_breaker.py   # Circuit breaker pattern
    ├── sanitization.py       # Input sanitization / prompt-injection defense
    ├── parsing.py            # JSON extraction, repair, structured parsing
    ├── renderer.py           # CLI rendering
    ├── scraper.py            # Web content extraction
    └── reasoner_persuasion_defense.py  # Adversarial persuasion defense

ui-next/src/
├── app/                      # App Router (layout, page, providers, error, api routes)
├── components/
│   ├── chat/                 # ChatFeed, ChatMessage, MarkdownRenderer, TypewriterMarkdown
│   ├── layout/               # Composer, PhaseTimeline, Sidebar, ShortcutModal
│   ├── phases/              # PhaseCard, PhaseRenderer, ClassificationCard, CritiqueCard, SynthesisCard
│   ├── ui/                  # Button, Badge, Spinner, ThemeToggle
│   └── widgets/             # WidgetRenderer, CalculationWidget, StockWidget, WeatherWidget
├── hooks/                    # usePipelineStream (SSE), useConversationHistory, useKeyboardShortcuts, useServerStatus
├── lib/                      # api-client, db (IndexedDB), types, utils, security, markdown
└── stores/                   # app-store.ts (Zustand global state with persistence)

tests/                        # pytest suite (~60+ test files)
```

---

## 4. Commands

### Development Environment

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd ui-next && npm install

# Start all (backend + frontend + SearXNG)
python start_all.py

# Backend only
uvicorn asgi:app --reload --host 0.0.0.0 --port 8003

# Frontend only
cd ui-next && npm run dev

# SearXNG search
docker-compose -f docker-compose.searxng.yml up -d
```

### Testing

```bash
# All tests
python -m pytest tests/ -v

# Skip slow/integration
python -m pytest tests/ -v -m "not slow and not integration"

# Single file
pytest tests/unit/test_activity_stream.py -v

# With coverage
pytest tests/ --cov=src/reasoner --cov-report=html

# Include slow tests
python -m pytest --run-slow

# SearXNG integration tests (requires live instance)
python -m pytest -m searxng

# Parallel execution
pytest -n auto
```

### CLI

```bash
# List presets and models
python main.py --list-presets
python main.py --list-models

# Run a reasoning pipeline
python main.py --problem "..." --preset debate-premium

# Load from file, export JSON
python main.py --problem-file problem.txt --output result.json --preset multi-perspective-premium

# Sequential mode (rate-limited environments)
python main.py --problem "..." --sequential

# Adjust top-k pruning (default: 2)
python main.py --problem "..." --top-k 3

# Save and resume state
python main.py --save-state state.json --problem "..."
python main.py --resume state.json
```

### Frontend

```bash
cd ui-next

# Dev / build
npm run dev
npm run build
npm run lint        # ESLint 9 flat config (eslint.config.mjs)

# Type check
npx tsc --noEmit

# E2E tests
npx playwright test
```

---

## 5. Key Architecture Details

### HyperGate Pre-Router

Every request passes through `HyperGateAgent` before any reasoning pipeline. Six specialized sub-agents run **in parallel** with fail-safe fallback — any sub-agent error becomes a graceful fallback, never a crash. Real method names are never exposed to LLMs; only opaque letters (B–Q) appear in sub-agent prompts.

```
Problem → [LanguageDetector, ComplexityEstimator, DirectDetector, WebSearchDetector, MethodClassifier] → TieBreaker
                                                                                                          ↓
                              DIRECT (instant answer) | WEB_SEARCH | PIPELINE (method auto-selected)
```

### Core Pipeline Flow

```
Problem → HyperGate → Phase 0: Classification (task type, language) → Phase 1: Decomposition (≤5 sub-problems, failure modes)
       → Phase 2: Multi-Perspective Generation (parallel, cross-lab: constructive/destructive/systemic/minimalist)
       → Phase 3: Critique & Pruning (independent scoring 0-10, retains top-k)
       → Phase 4: Stress Testing (optimal/constraint-violation/adversarial)
       → Phase 5: Synthesis (VERIFIED/HYPOTHESIS/UNKNOWN + Action Blueprint)
```

### Reasoning Methods (17)

| Method | Description |
|--------|-------------|
| **Orchestrated** | Default 6-phase multi-perspective |
| **Debate** | Adversarial with opening, rebuttal, judge |
| **Jury** | Expert panel (generator, critic, verifier) |
| **Research** | Web-grounded iterative RAG with SearXNG |
| **Scientific** | Hypothesis generation + falsification |
| **Socratic** | Elenchus questioning to expose assumptions |
| **Pre-Mortem** | Prospective failure analysis |
| **Bayesian** | Prior → likelihood → posterior belief updating |
| **Dialectical** | Hegelian thesis-antithesis-synthesis |
| **Analogical** | Cross-domain structure-mapping |
| **Delphi** | Structured expert consensus |
| **CoVE** | Chain-of-Verification (draft → verify → answer → revise) |
| **SoT** | Skeleton-of-Thought (skeleton → parallel solve → assemble) |
| **ToT** | Tree-of-Thoughts (search + evaluate + backtrack) |
| **PoT** | Program-of-Thoughts (executable code as reasoning) |
| **Self-Discover** | Dynamic reasoning module composition |
| **Writing** | Creative writing with hallucination guards |

### Presets (42)

Every method has **Budget** (~$0.02/run) and **Premium** (~$0.15–$0.30/run) tiers, plus 1 Balanced and 1 Experimental. The UI orders methods Budget → Balanced → Premium from most to least cost-effective, defaulting to the first method/preset.

### Model Routing Philosophy

Cross-lab diversity prevents echo chambers:
- **Phase 2 (Perspectives):** ≥3 different labs in Budget, ≥4 in Premium
- **Scoring:** Scorer must be from a different ecosystem than the dominant generator
- **Fallbacks:** Fail to cross-lab equivalent, never blindly to preset primary

### State Field Pattern

Method-specific state uses `dict[str, Any]` fields initialized with `field(default_factory=dict)` in `PipelineState`. Accessed via `.get()`, never direct subscript. Enables `--resume` with partial/older state files.

### JSON Extraction

All LLM responses parsed via `parsing.extract_json()`, never direct JSON parsing.

---

## 6. Working with Neuro & Compression

- **Recall:** `neuro.server.create_neuro_router()` provides the `/neuro/recall` endpoint. Automatically called in `ReasonerPipeline.run` to fetch relevant context from long-term memory.
- **Learn:** `/neuro/learn` saves the final synthesis at pipeline end. Tag entries with metadata (preset, task_type).
- **Compression:** `neuro.compression.smart_compress(text, ext, level)` reduces token usage.
  - `Aggressive` — structural analysis, keeps only signatures
  - `Minimal` — general cleanup
- **L1/L2/L3 tiers:** L1=memory, L2=disk JSON, L3=Neuro LTM with embedding search
- **Tenant isolation:** Use `agent_id` in Neuro requests → stored in `~/.neuro/agents/<id>`

---

## 7. Cross-Cutting Concerns

### Security (Defense in Depth)
- **Input:** `reasoner.sanitization.sanitize_for_prompt()` — XSS stripping, null-byte removal, prompt-injection regex guards, unicode NFKC normalization
- **Auth:** Token-based with scoped permissions (`auth.py`)
- **Rate limiting:** Token-bucket per client IP (`rate_limiter.py`)
- **CSRF:** HMAC-SHA256 signed tokens verified in Next.js API routes **and** FastAPI via `require_csrf`
- **Circuit breaker:** Automatic provider fallback (`circuit_breaker.py`)
- **Headers:** X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS, CSP

### Self-Healing CI/CD
`.github/workflows/self-healing-ci.yml` runs 5 loops: healing-profile → loop1-static → loop2-runtime → loop3-evolutionary → searxng-integration → healing-verification. Coverage gates: 60% fail, 80% warn.

---

## 8. Workflow Orchestration

1. **Plan First** — Enter plan mode for any non-trivial task (3+ steps or architectural decisions). Write specs to `tasks/todo.md`.
2. **Subagent Strategy** — Use subagents liberally to keep main context clean. Offload research, exploration, and parallel analysis.
3. **Self-Improvement Loop** — After any correction from the user, update `tasks/lessons.md` with the pattern.
4. **Verification Before Done** — Never mark a task complete without proving it works (tests, logs, diffs).
5. **Demand Elegance** — For non-trivial changes, pause and ask "is there a more elegant way?"
6. **Autonomous Bug Fixing** — When given a bug report, just fix it. Point at logs, errors, failing tests — then resolve them.

---

## 9. Core Principles

- **Simplicity First** — Make every change as simple as possible. Impact minimal code.
- **Root Causes** — Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact** — Changes should only touch what's necessary. Avoid introducing bugs.

---

*For detailed product snapshot, reasoning methods, and preset tiers, see `AGENTS.md`. For complete architectural analysis (structural, behavioral, domain, infrastructure views), see `ARCHITECTURE_MINDMAP.md`.*
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
