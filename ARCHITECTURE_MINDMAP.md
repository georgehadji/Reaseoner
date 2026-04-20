# ARA v2.2 — Complete Architectural Mindmap

> **Repository:** `E:\Documents\Vibe-Coding\Reasoner`  
> **Generated:** 2026-04-19  
> **Methodology:** Static analysis + multi-agent codebase traversal + dependency graph reconstruction

---

## 1. PROJECT OVERVIEW

**ARA (Adaptive Reasoning Architecture)** is a multi-method LLM reasoning pipeline exposed through a FastAPI backend and a Next.js chat UI. It orchestrates 16+ reasoning methodologies (Debate, Jury, Scientific, Socratic, Bayesian, Delphi, CoVe, SoT, ToT, PoT, Self-Discover, etc.) across a 6-phase universal pipeline, with automatic method selection via the HyperGateAgent.

| Concern | Technology |
|---------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS v4 |
| State (FE) | Zustand 5 (persist → localStorage) |
| State (BE) | Module-level globals + PipelineState god object |
| LLM Routing | OpenRouter (primary) + Ollama (local) + 10 direct provider APIs |
| Search | SearXNG (Docker, port 8888) |
| Persistence | SQLite (default) / PostgreSQL (optional, lazy-loaded) |
| Cache | Disk JSON + `_MEMORY_CACHE` dict + Neuro L1/L2/L3 hierarchy |
| Testing | pytest + pytest-asyncio (~800 tests) |
| CI/CD | GitHub Actions — "Self-Healing CI" with 4 introspection loops |

---

## 2. PHASE 1 — CODEBASE SURVEY

### 2.1 Directory Map

```
Reasoner/
├── .env / .env.example           # Environment schema (11 LLM keys, rate limits, admin)
├── docker-compose.searxng.yml    # SearXNG container only
├── main.py                       # CLI shim (argparse, --list-models)
├── asgi.py                       # ASGI entry shim → FastAPI app
├── start_all.py / .bat           # Dev orchestrator: backend + frontend + docker
├── kill_servers.py / .bat        # Graceful process killer
├── requirements.txt              # Python deps (no Redis/Stripe yet)
├── pytest.ini                   # testpaths=tests, pythonpath=src
│
├── src/reasoner/                 # ← ALL BACKEND LOGIC
│   ├── api/                      # FastAPI interface layer
│   ├── application/              # CQRS commands, queries, event bus, handlers
│   ├── core/                     # Domain core: constants, settings, protocols, perspectives, memory, search
│   ├── hypergate/                # Auto-method selector (6 sub-agents)
│   ├── infrastructure/           # Adapters: LLM ports, persistence, WebSocket, widgets
│   ├── neuro/                    # Persistent memory engine (L1/L2/L3 cache, sessions, server)
│   ├── subagents/                # PhaseSubAgent v2.2 (critique, decomposition, enhancement, search, synthesis)
│   ├── healing/                  # Self-healing system (3 loops) + 19 auto-generated tests
│   ├── shared/                   # Shared kernel (empty placeholder)
│   ├── pipeline.py               # ARAPipeline orchestrator (~2,300 lines)
│   ├── llm.py                    # Multi-provider LLM abstraction + ProviderRouter
│   ├── models.py                 # PipelineState + 20+ dataclasses
│   ├── presets.py                # 24+ PipelinePreset configs
│   ├── auth.py                   # In-memory SHA-256 API key auth
│   ├── rate_limiter.py           # Token-bucket + sliding window
│   ├── exceptions.py             # ARAError hierarchy
│   ├── sanitization.py           # Prompt-injection defense
│   ├── phases.py                 # Prompt template library
│   └── ... (scraper, renderer, parsing, pricing, circuit_breaker, etc.)
│
├── ui-next/                      # ← ALL FRONTEND LOGIC
│   ├── src/app/                  # Next.js App Router pages + API proxies
│   ├── src/components/           # chat, layout, phases, widgets, ui
│   ├── src/hooks/                # usePipelineStream, useKeyboardShortcuts, etc.
│   ├── src/lib/                  # api-client, security-server/client, db (IndexedDB)
│   └── src/stores/               # Zustand app-store
│
├── tests/                        # pytest suite (~800 tests)
├── docs/                         # Documentation
├── legacy/                       # Deprecated code
└── uploads/                      # File upload storage
```

### 2.2 File Classification

| Layer | Files |
|-------|-------|
| **Core Logic** | `pipeline.py`, `llm.py`, `models.py`, `phases.py`, `parsing.py`, `presets.py`, `gate_agent.py`, `hypergate/` |
| **Domain** | `core/constants.py`, `core/settings.py`, `core/protocol.py`, `core/perspectives.py`, `core/memory.py`, `core/search.py`, `core/temperatures.py` |
| **Application (CQRS)** | `application/commands/__init__.py`, `application/queries/__init__.py`, `application/event_bus/bus.py`, `application/handlers/handlers.py` |
| **Interface (API)** | `api/__init__.py`, `api/cache.py`, `api/history.py`, `api/serializers.py` |
| **Infrastructure** | `infrastructure/llm/ports.py`, `infrastructure/persistence/`, `infrastructure/websocket/manager.py`, `infrastructure/widgets/` |
| **Interfaces (UI)** | `ui-next/src/app/page.tsx`, `ui-next/src/app/api/*/route.ts`, `ui-next/src/components/`, `ui-next/src/hooks/usePipelineStream.ts` |
| **Utilities** | `sanitization.py`, `scraper.py`, `logging_utils.py`, `server_check.py`, `circuit_breaker.py`, `pricing.py`, `suggestions.py`, `uploader.py` |
| **Data Layer** | `neuro/cache.py`, `neuro/sessions.py`, `neuro/config.py`, `token_cache.py`, `infrastructure/persistence/event_store.py`, `infrastructure/persistence/postgres_store.py`, `infrastructure/persistence/snapshots.py` |

---

## 3. PHASE 2 — ARCHITECTURE RECONSTRUCTION

### 3A. STRUCTURAL VIEW

#### Layered Architecture (Clean Architecture aspirational; pragmatic hybrid in practice)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  Next.js 16 (App Router)│  │  FastAPI HTTP/SSE Interface              │   │
│  │  - page.tsx             │  │  - api/__init__.py (~1,760 lines)        │   │
│  │  - API proxy routes     │  │  - ~30 endpoints, middleware stack       │   │
│  │  - Zustand state        │  │  - StreamingResponse (SSE)               │   │
│  └─────────────────────────┘  └─────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER (CQRS)                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Commands: RunPipelineCommand, ExecuteWidgetCommand                    ││
│  │  Queries:  GetPipelineStatusQuery, GetHistoryQuery                     ││
│  │  EventBus: track_pipeline_metrics, handle_event                        ││
│  │  Handlers: HandlerRegistry                                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  DOMAIN LAYER                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  PipelineState (god object), Phase Protocol, PerspectiveDefinition     ││
│  │  ARAPipeline.run(problem) → universal start → method branch → end      ││
│  │  HyperGateAgent.decide(problem) → action + method                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER (Adapters)                                            │
│  ┌──────────────────┬──────────────────┬──────────────────┬───────────────┐│
│  │  LLM Providers   │  Persistence     │  Transport       │  Widgets      ││
│  │  - OpenRouter    │  - SQLite Event  │  - WebSocketMgr  │  - Weather    ││
│  │  - Ollama        │  - PostgreSQL    │  - SSE streams   │  - Stocks     ││
│  │  - Anthropic     │  - Snapshots     │                  │  - Calculator ││
│  │  - Google        │  - TaggedMemory  │                  │  - Discover   ││
│  │  - DeepSeek...   │  - Neuro L1/L2/L3│                  │  - Image/Video││
│  └──────────────────┴──────────────────┴──────────────────┴───────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Module Dependency Graph (Simplified)

```
[Entry: asgi.py] ──► [api/__init__.py]
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
 [pipeline.py]      [rate_limiter.py]   [auth.py]
       │
       ├────► [llm.py] ◄────┬────► [infrastructure/llm/ports.py]
       │                    │
       ├────► [models.py] ◄─┴────► [core/constants.py]
       │                    │
       ├────► [phases.py]           [core/settings.py]
       │
       ├────► [core/search.py]
       │
       ├────► [hypergate/] ◄──── [hypergate/sub_agents/]
       │
       ├────► [subagents/] (optional, env-flagged)
       │
       ├────► [token_cache.py]
       │
       └────► [neuro/] ◄──── [api/cache.py] ◄──── [api/history.py]
```

#### Key Structural Patterns

1. **CQRS/Event Sourcing** — `application/commands`, `application/queries`, `infrastructure/persistence/event_store.py`, `snapshots.py`. Commands mutate state via events; queries read from read-model projections.
2. **Plugin Widget System** — `infrastructure/widgets/` with `Widget` protocol and `WidgetRegistry`. Widgets are auto-detected and executed via `/api/widget/execute`.
3. **Sub-Agent Orchestration** — `subagents/<phase>/hyper_agent.py` coordinates parallel sub-agents per phase; toggled via `USE_PHASE_SUBAGENTS` env flags.
4. **Auto-Method Selection** — `HyperGateAgent` uses 6 sub-agents (complexity, direct detector, language detector, method classifier, tie-breaker, web detector) to choose pipeline method or bypass.
5. **Multi-Provider Routing** — All external LLMs route through OpenRouter (single API key) except Ollama local models; explicit fallback chains per preset.
6. **Token & Cost Optimization** — `token_cache.py`, dynamic `PHASE_TOKEN_BUDGETS`, `detailed_token_usage`, `phase_costs` tracked in `PipelineState`.
7. **Defense-in-Depth Prompt Engineering** — Dual-layer language enforcement (system prompt + user prompt), strict JSON schema contracts with `no additional keys` directives, and defensive serialization fallback when LLMs deviate from expected schemas.

---

### 3B. BEHAVIORAL VIEW

#### Request/Response Lifecycle (Pipeline Run)

```
1. Client POST /api/run
   └─► RunRequest validated (XSS strip, null-byte removal,
       regex injection guards, unicode NFKC normalization)

2. RateLimiter.is_allowed(client_id) + optional_auth

3. run_stream_cached(req)
   └─► Cache lookup (_cache_key → disk + _MEMORY_CACHE)
       └─► Cache miss → run_stream(req)

4. run_stream(req) — SSE AsyncGenerator
   a. Resolve preset:
      • "auto-budget" / "auto-premium" → HyperGateAgent.decide(problem)
        → action: "direct" | "web_search" | "pipeline" + method
      • Custom routing → _filter_routing → ProviderRouter.from_model_ids
   b. Build ARAPipeline(router, preset_name, ...)
   c. yield {"type": "start", auto_selected_method, ...}
   d. Phase loop (method-dependent ordering):
      ┌─────────────────────────────────────────────────────────────┐
      │  Phase 0: Classification      → _phase_0_classify           │
      │  Phase 1: Decomposition       → _phase_1_decompose          │
      │  Phase 1.5: Deep Read         → _phase_deep_read (cond.)    │
      │  Phase 2..N: Method-specific  → debate / jury / research /  │
      │              scientific / socratic / pre-mortem / bayesian /│
      │              dialectical / analogical / delphi / cove / sot/│
      │              tot / pot / self-discover                      │
      │  Final: Synthesis             → _phase_synthesis            │
      │  Optional: Post-Synthesis Verify                            │
      └─────────────────────────────────────────────────────────────┘
      • Before each phase: check _cancelled_runs[run_id]
      • On exception: yield phase_error; break if CRITICAL_PHASES
      • After each phase: drain state.pending_events; serialize state
      • Synthesis: typewriter text_chunk streaming (asyncio.sleep 0.1s)
   e. yield {"type": "done", errors, total_tokens, duration, cost}
   f. Persist history entry + TaggedMemory (method:preset tags)
   g. Save collected events to cache (unless no_cache or errors)

5. StreamingResponse(media_type="text/event-stream") → Client
```

#### Follow-up Request Lifecycle

```
POST /api/run-followup
  └─► Seeds state.previous_synthesis from conversation history
  └─► Calls run_stream() with conversation_id
  └─► After pipeline completes:
      POST to http://127.0.0.1:50001/neuro/learn
      with {prompt, response: state.final_solution.core_solution,
            agent_id: conversation_id, metadata: {...}}
```

#### Data Flow (High-Level)

```
User Input
    │
    ▼
[Sanitization] ──► [Rate Limit] ──► [Auth]
    │
    ▼
[HyperGateAgent] ──► method selection ──► preset resolution
    │
    ▼
[ARAPipeline.run(problem)]
    │
    ├──► Phase 0: classify ──► LLM call ──► state.task_type
    ├──► Phase 1: decompose ──► LLM call ──► state.sub_problems
    ├──► Phase 1.5: context vetting ──► SearXNG search ──► state.vetted_context
    │
    ├──► [METHOD BRANCH]
    │     ├──► multi_perspective ──► perspectives (parallel gather)
    │     │                          └──► critique ──► stress_test
    │     ├──► debate ──► opening ──► rebuttal ──► cross_examine ──► judge
    │     ├──► jury ──► generate ──► critique ──► verify ──► weighted_ranking
    │     ├──► research ──► web_search ──► perspectives ──► critique
    │     ├──► scientific ──► hypothesize ──► test ──► stress_test
    │     ├──► socratic ──► question ──► answer
    │     ├──► pre_mortem ──► failure ──► backtrack ──► signals ──► redesign
    │     ├──► bayesian ──► priors ──► likelihood ──► posterior ──► sensitivity
    │     ├──► dialectical ──► thesis ──► antithesis ──► contradictions ──► aufhebung
    │     ├──► analogical ──► abstraction ──► domain_search ──► mapping ──► transfer
    │     ├──► delphi ──► round1 ──► aggregation ──► round2 ──► convergence ──► dissent
    │     ├──► cove ──► draft ──► verify ──► answer ──► revise
    │     ├──► sot ──► skeleton ──► solve (parallel, max 4) ──► assemble
    │     ├──► tot ──► decompose ──► generate ──► evaluate ──► backtrack
    │     ├──► pot ──► generate ──► execute ──► interpret
    │     └──► self_discover ──► select ──► adapt ──► implement
    │
    ├──► Phase N: synthesis ──► LLM call ──► FinalSolution
    └──► Optional: post-synthesis verify ──► cross-model validation
    │
    ▼
[Cache write] + [History persist] + [Neuro learn]
    │
    ▼
SSE stream to client
```

#### State Management

| Scope | Mechanism | Location |
|-------|-----------|----------|
| **Per-request** | `PipelineState` dataclass | Passed through all phases |
| **Per-run cancellation** | `_cancelled_runs: dict[str, bool]` | `api/__init__.py` module global |
| **Per-run tracking** | `_active_runs: set[str]` | `api/__init__.py` module global |
| **API cache** | `_MEMORY_CACHE: dict` + disk JSON | `api/cache.py` module global |
| **Token cache** | Singleton `TokenCache` (1M budget, 1h TTL) | `token_cache.py` module global |
| **Auth keys** | `AuthManager._keys: dict` (in-memory) | `auth.py` — resets on restart |
| **Rate limit buckets** | `RateLimiter._buckets: dict` (in-memory) | `rate_limiter.py` — 10K cap |
| **Neuro L2 index** | `L2Index.entries: list[dict]` | `neuro/cache.py` — bounded FIFO |
| **Frontend global** | Zustand store (persist → localStorage) | `ui-next/src/stores/app-store.ts` |
| **Frontend conversations** | IndexedDB (`ARA_Pipeline_v2`) | `ui-next/src/lib/db.ts` |

---

### 3C. DOMAIN VIEW

#### Core Business Entities

```
PipelineState
├── problem: str
├── task_type: TaskType
├── language: str
├── sub_problems: list[str]
├── assumptions: list[str]
├── candidates: list[SolutionCandidate]
├── scores: list[float]
├── stress_results: list[StressTestResult]
├── generation_candidates: list[SolutionCandidate]
├── critic_scores: list[CritiqueScore]
├── verification_results: list[VerificationResult]
├── meta_evaluation: MetaEvaluation
├── final_solution: FinalSolution
├── previous_synthesis: str
├── vetted_context: list[ContextItem]
├── context_quality: str  # good | partial | contaminated | missing
├── web_discovery_results: list[WebResult]
├── debate_rounds: list[DebateRound]
├── scientific_state: ScientificState
├── socratic_state: SocraticState
├── pre_mortem_state: PreMortemState
├── bayesian_state: BayesianState
├── dialectical_state: DialecticalState
├── analogical_state: AnalogicalState
├── delphi_state: DelphiState
├── cove_state: CoVeState
├── sot_state: SoTState
├── tot_state: ToTState
├── pot_state: PoTState
├── self_discover_state: SelfDiscoverState
├── phase_tokens: dict[str, int]
├── detailed_token_usage: list[dict]
├── phase_costs: dict[str, float]
├── total_cost_usd: float
├── phase_models: dict[str, str]
├── errors: list[str]
├── pending_events: list[DomainEvent]
└── turn_number: int
```

#### Domain Boundaries

| Boundary | Responsibility | Key Classes |
|----------|---------------|-------------|
| **Reasoning Core** | Universal pipeline + method branching | `ARAPipeline`, `PhaseConfig`, `PhaseResult` |
| **Method Catalog** | 16 specific reasoning methodologies | `_phase_debate_*`, `_phase_jury_*`, `_phase_scientific_*`, etc. |
| **Perspectives** | Multi-perspective generation & critique | `PerspectiveDefinition`, `DEFAULT_PERSPECTIVES` |
| **Context Vetting** | Iterative RAG with search, dedup, CoT | `_phase_context_vetting` |
| **Synthesis** | Final answer assembly with citations | `_phase_synthesis` |
| **HyperGate** | Auto-method selection & bypass | `HyperGateAgent`, `GateDecision` |
| **Neuro Memory** | Persistent learning from conversations | `L1Cache`, `L2Index`, `L3Scan`, `TaggedMemory` |
| **Security** | Input sanitization, auth, rate limiting | `InputSanitizer`, `AuthManager`, `RateLimiter` |

#### Key Abstractions

1. **Phase Protocol** — `core/protocol.py` defines `Phase` as a callable contract: `(PipelineState, **kwargs) → PhaseResult`. Enables the universal pipeline to treat all phases uniformly.
2. **PipelinePreset** — Declarative routing table mapping phase roles → model IDs + fallbacks. 24+ presets in `presets.py`.
3. **ProviderRouter** — Abstracts LLM provider diversity. Each phase role gets a provider instance; failures cascade through explicit fallback → primary → re-raise.
4. **PerspectiveDefinition** — Encapsulates a reasoning stance (constructive, destructive, systemic, minimalist). Used in Phase 2 to generate parallel analyses.
5. **DomainEvent / Aggregate** — CQRS primitives. `PipelineState` is NOT an aggregate but a DTO; `core/aggregates/pipeline.py` defines the true aggregate with `apply(event)` logic.
6. **EpistemicLabel Contract** — `[VERIFIED]`, `[HYPOTHESIS]`, `[UNKNOWN]` labels are requested inline within `core_analysis` strings across Decomposition, Perspectives, and Synthesis phases. Not enforced by type system — heuristic convention carried by prompt instructions.

---

### 3D. INFRASTRUCTURE VIEW

#### External Services & APIs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL SERVICES                                                          │
├─────────────────────────────┬───────────────────────────────────────────────┤
│  LLM Providers              │  Search                                       │
│  ├── OpenRouter (primary)   │  └── SearXNG (localhost:8888)                │
│  ├── OpenAI                 │      ├── Bing, DuckDuckGo, Google, Brave     │
│  ├── Anthropic              │      ├── Wikipedia, arXiv                    │
│  ├── Google (Gemini)        │      ├── GitHub, StackOverflow               │
│  ├── DeepSeek               │                                               │
│  ├── Mistral                │  Widgets                                      │
│  ├── xAI (Grok)             │  ├── OpenWeatherMap API                      │
│  ├── Perplexity             │  ├── Yahoo Finance API                       │
│  ├── Qwen (Alibaba)         │  ├── Calculator (simpleeval)                 │
│  ├── Moonshot               │  ├── Image Search                            │
│  ├── ZhipuAI                │  └── Video Search                            │
│  └── Ollama (local)         │                                               │
├─────────────────────────────┴───────────────────────────────────────────────┤
│  Databases                                                                  │
│  ├── SQLite (default event store) — aiosqlite                               │
│  ├── PostgreSQL (optional event store) — asyncpg, lazy-loaded               │
│  └── IndexedDB (frontend conversations) — idb wrapper                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Docker                                                                     │
│  └── SearXNG container (searxng/searxng:latest)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Planned (SaaS roadmap)                                                     │
│  ├── Redis (sessions, distributed rate limit, run state)                    │
│  ├── Supabase Auth (JWT, OAuth, email/password)                             │
│  ├── Stripe (billing, subscriptions, checkout)                              │
│  ├── Prometheus + Grafana (metrics, dashboards)                             │
│  └── Sentry (error tracking)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Network Topology (Development)

```
┌─────────────┐     ┌─────────────────────────────┐     ┌─────────────────┐
│   Browser   │────►│  Next.js Dev Server (:3000) │────►│  FastAPI (:8001)│
│  (port 3000)│◄────│  - API proxy routes         │◄────│  - /api/run     │
└─────────────┘     │  - CSRF + rate limit        │     │  - /api/search  │
                    │  - Header sanitization      │     │  - SSE streams  │
                    └─────────────────────────────┘     └────────┬────────┘
                                                                 │
                    ┌─────────────────────────────┐              │
                    │  SearXNG (:8888)            │◄─────────────┘
                    │  - Docker Compose           │     (search queries)
                    └─────────────────────────────┘

                    ┌─────────────────────────────┐
                    │  Neuro Server (:50001)      │◄──── (neuro/learn)
                    │  - Persistent memory        │
                    └─────────────────────────────┘
```

#### Middleware Stack (FastAPI)

```
Request
  │
  ▼
[SecurityHeadersMiddleware]  → HSTS, X-Frame-Options, CSP-style, nosniff
  │
  ▼
[CORSMiddleware]             → Restricted origins
  │
  ▼
[MemoryLimitMiddleware]      → psutil RSS guard; 503 if MEMORY_LIMIT_MB exceeded
  │
  ▼
[RequestTimeoutMiddleware]   → 300s timeout (skipped for /api/run SSE)
  │
  ▼
[Route Handler]
```

---

## 4. PHASE 3 — RELATIONSHIP MAPPING

### 4.1 Module → Module Dependencies

```
api/__init__.py
├── pipeline.py           (ARAPipeline, run_stream orchestration)
├── llm.py                (ProviderRouter, build_provider)
├── presets.py            (PRESETS, PipelinePreset)
├── auth.py               (AuthManager, optional_auth, require_auth)
├── rate_limiter.py       (RateLimiter, check_rate_limit)
├── hypergate/            (HyperGateAgent)
├── api/cache.py          (_MEMORY_CACHE, _cache_key)
├── api/serializers.py    (per-phase SSE serializers)
├── api/history.py        (history persistence)
├── models.py             (RunRequest/FollowupRequest Pydantic models)
├── core/search.py        (get_discovery_client)
├── neuro/server.py       (create_neuro_router)
├── infrastructure/websocket/  (WebSocketManager)
└── application/          (get_architecture_components — lazy CQRS)

pipeline.py
├── llm.py                (ProviderRouter)
├── models.py             (PipelineState, dataclasses)
├── phases.py             (prompt templates)
├── parsing.py            (extract_json, safe_list, safe_float)
├── core/search.py        (discovery client, result filtering)
├── token_cache.py        (get_token_cache)
├── sanitization.py       (sanitize_for_prompt)
├── core/constants.py     (TIMEOUTS, TRUNCATION, budgets)
├── subagents/            (optional hyperagents per phase)
└── hypergate/            (indirect — method selection happens in api layer)

llm.py
├── infrastructure/llm/ports.py   (BaseLLMProvider)
├── core/constants.py             (model aliases, timeouts)
├── exceptions.py                 (ARAError hierarchy)
└── openai / httpx               (external SDKs)

infrastructure/persistence/
├── event_store.py        (SQLite — aiosqlite)
├── postgres_store.py     (PostgreSQL — asyncpg, lazy)
└── snapshots.py          (read-model projections)

neuro/
├── cache.py              (L1/L2/L3 memory hierarchy)
├── sessions.py           (conversation ingestion)
├── server.py             (FastAPI sub-router on :50001)
├── config.py             (NeuroConfig, CacheConfig)
└── providers.py          (embedding providers)
```

### 4.2 Function → Function Call Chains (Critical Paths)

#### Path A: Main Pipeline Run
```
asgi:app
└── api/__init__.py:run_pipeline()
    └── run_stream_cached(req)
        └── run_stream(req, initial_state=None)
            ├── HyperGateAgent.decide(problem)  [if auto preset]
            │   └── subagent orchestration (6 parallel detectors)
            ├── ProviderRouter.from_model_ids(...)
            │   └── build_provider(model_id)
            │       └── OpenRouterProvider() or OpenAICompatibleProvider()
            ├── ARAPipeline(router, preset_name, ...)
            │   └── .run(problem)
            │       ├── _phase_0_classify()
            │       │   └── _call_llm_cached("classification", ...)
            │       ├── _phase_1_decompose()
            │       │   └── _call_llm_cached("decomposition", ...)
            │       ├── _phase_context_vetting()
            │       │   ├── get_discovery_client().search()
            │       │   └── asyncio.gather(vet_tasks, return_exceptions=True)
            │       ├── [METHOD BRANCH]
            │       │   └── _phase_*_*
            │       │       └── _call_llm_cached(role, ...)
            │       │           ├── token_cache.get() [cache hit?]
            │       │           └── router.call(role, ...)
            │       │               └── provider.complete_with_retry()
            │       │                   └── httpx.AsyncClient.post()
            │       └── _phase_synthesis()
            │           └── _call_llm_cached("synthesis", ...)
            └── yield SSE events (start, phase_*, text_chunk, done)
```

#### Path B: Cache Write-Back
```
run_stream() completes
└── _save_cache(run_id, state, events)
    ├── _cache_key(req) → hash of normalized request fields
    ├── atomic write to temp file → os.replace()
    └── _MEMORY_CACHE[key] = events
```

#### Path C: Neuro Learning (Follow-up)
```
run_followup_stream() completes
└── httpx.post("http://127.0.0.1:50001/neuro/learn", json={...})
    └── neuro/server.py: neuro_learn_endpoint()
        └── sessions.ingest(prompt, response, agent_id, metadata)
            └── sessions.add(agent_id, embedding, content)
                └── L2Index.add() + L1Cache.add()
```

### 4.3 Data Transformations

```
User Input (raw str)
    │
    ▼  [InputSanitizer.sanitize]
Sanitized str (truncated, injection-checked, HTML-escaped)
    │
    ▼  [RunRequest Pydantic validation]
Validated request model
    │
    ▼  [HyperGateAgent.decide]
GateDecision(action, method, confidence)
    │
    ▼  [ARAPipeline.run]
PipelineState (accumulates across phases)
    │
    ▼  [Per-phase LLM calls]
Raw LLM response (JSON or prose)
    │
    ▼  [parsing.extract_json]
Structured dict / list
    │
    ▼  [Defensive schema validation + fallback serialization]
Validated / recovered content (empty `core_analysis` triggers full-dict serialization)
    │
    ▼  [Phase business logic]
Updated PipelineState fields
    │
    ▼  [_phase_synthesis]
FinalSolution(core_solution, citations, epistemic_labels)
    │
    ▼  [SSE serialization]
JSON event strings
    │
    ▼  [Frontend parsing]
PhaseEvent objects → React state → DOM
```

### 4.4 Events → Triggers

| Event | Source | Handler | Consumer |
|-------|--------|---------|----------|
| `pipeline_started` | `api/__init__.py:run_stream` | — | SSE client |
| `phase_complete` | `ARAPipeline.run` | `api/serializers.py:_ser_N` | SSE client |
| `phase_error` | `ARAPipeline.run` | logged + streamed | SSE client |
| `text_chunk` | `_phase_synthesis` | streamed directly | SSE client (typewriter effect) |
| `cancelled` | `api/__init__.py:stop_pipeline` | `_cancelled_runs[run_id]=True` | Checked before each phase |
| `DomainEvent` | Any phase | `state.pending_events.append()` | Drained after each phase → EventStore |
| `neuro/learn` | `run_followup_stream` | `neuro/server.py` | L1/L2 cache update |
| `cache_invalidate` | `api/__init__.py:clear_cache` | `_MEMORY_CACHE.clear()` + disk rm | Next request |

### 4.5 Cyclic Dependencies

**None detected at the package level.** The dependency graph is DAG-shaped:

- `api/` → `pipeline/` → `llm/`, `models/`, `phases/`, `core/`
- `core/` has no outgoing dependencies to `api/`, `pipeline/`, or `application/`
- `application/` depends on `core/` and `infrastructure/`
- `infrastructure/` depends on `core/` (for settings, constants) but NOT on `api/` or `pipeline/`

**However, intra-module tight coupling exists:**
- `pipeline.py` imports `phases.py` as a monolithic prompt library. `phases.py` is ~2,000+ lines of string constants with no clear interface boundaries.
- `models.py` is imported by nearly every module, creating a hub-and-spoke pattern around `PipelineState`.

### 4.6 Hidden Coupling

1. **Module-Level Global State** — `_cancelled_runs`, `_active_runs`, `_MEMORY_CACHE`, `rate_limiter`, `auth_manager` are all module-level singletons. They appear to be "utilities" but are actually **shared mutable state** across all requests. This prevents horizontal scaling (multi-worker/multi-process).

2. **PipelineState as God Object** — `PipelineState` has ~100 fields. Phases mutate overlapping subsets. A change to `state.candidates` in Phase 2 affects Phase 3's critique logic, Phase 4's stress test, and Phase N's synthesis — but these relationships are implicit, not typed.

3. **Neuro Server Hardcoded URL** — `http://127.0.0.1:50001/neuro/learn` is hardcoded in `api/__init__.py`. The Neuro server is a separate process; if it crashes, follow-up persistence fails silently (exception is caught and logged but not retried).

4. **Token Cache Singleton** — `token_cache.py` maintains a global `TokenCache` instance. It is lazily initialized but shared across all pipelines. Cache key collisions are possible if two different presets use the same model for the same role with the same prompt.

5. **Frontend Method Phases Mapping** — `ui-next/src/lib/config.ts` hardcodes `METHOD_PHASES` to map `auto_selected_method` to human-readable timeline labels. If the backend adds a new method without updating this map, the UI timeline shows generic fallback labels.

6. **Environment Variable Sprawl** — `core/settings.py` reads `.env` once at import time. Any code that imports `settings` before `load_dotenv` completes may see empty values. This is an implicit ordering contract.

### 4.7 Scaling Boundaries

The following components use **in-process mutable state** and therefore cannot span multiple workers or processes without data splitting:

| Component | State Location | Lock Protection | Scaling Path |
|-----------|---------------|-----------------|--------------|
| `RunStateStore` | `api/run_state.py:_run_store` | `asyncio.Lock` ✅ | Redis pub/sub or external task queue |
| `_MEMORY_CACHE` | `api/cache.py:_MEMORY_CACHE` | `threading.Lock` ✅ | Redis / memcached |
| `AuthManager` | `auth.py:_auth_manager` | `asyncio.Lock` ✅ | PostgreSQL + local TTL cache |
| `RateLimiter` | `rate_limiter.py:_rate_limiter` | `asyncio.Lock` ✅ | Redis sliding window |
| `CircuitBreaker` registry | `circuit_breaker.py:_circuit_breakers` | `threading.Lock` ✅ | Per-worker degradation acceptable |

**Fixes applied (2026-04-19):**
- `_run_store` unified to a single module-level singleton (was duplicated in `api/__init__.py` and `api/streaming.py`).
- `_MEMORY_CACHE` wrapped in `threading.Lock` for read/write safety.
- `_circuit_breakers` registry wrapped in `threading.Lock`.
- Scaling-limitation docstrings added to `RunStateStore`, `AuthManager`, `RateLimiter`, `CircuitBreaker`.

### 4.8 Implicit Contracts

| Contract | Parties | Enforcement | Risk if Broken |
|----------|---------|-------------|----------------|
| `PipelineState` field initialization | All phase methods | None (runtime `AttributeError`) | Phase crash, SSE error event |
| `state.pending_events` drain | Phase methods + `run_stream` | Manual `while` loop after each phase | Memory leak, event loss |
| `CRITICAL_PHASES` list | `pipeline.py` + `api/__init__.py` | Hardcoded set in both files | Desync → critical phase errors don't break pipeline |
| Cache key schema | `api/cache.py` + `run_stream_cached` | String concatenation with version prefix | Cache misses or collisions on schema change |
| `auto_selected_method` string values | `hypergate/hyperagent.py` + `ui-next/lib/config.ts` | None | UI timeline labels break |
| Neuro server availability | `api/__init__.py` + `neuro/server.py` | None (fire-and-forget POST) | Follow-up learning data lost |
| `_REGISTRY` model ID consistency | `llm.py` + `presets.py` | Preset constructor validates against registry | `PipelinePreset` raises `ValueError` at import time |
| `PhaseConfig` role mapping | `pipeline.py` + `presets.py` | `_KNOWN_ROUTING_ROLES` set | `ProviderRouter.get(role)` falls back to primary model |
| Request ID lifecycle | Client + `run_stream` + `stop_pipeline` | `_cancelled_runs` dict | Stop request may target wrong run or fail silently |
| SSE event type schema | `api/serializers.py` + `usePipelineStream.ts` | None (loose JSON parsing) | Frontend crashes on unhandled event types |
| Language consistency (system + user prompt) | `phases.py` + `pipeline.py` + LLM providers | Dual-layer: `PERSPECTIVE_SYSTEMS` strings + dynamic `get_language_instruction()` injection | One provider outputs wrong language; user sees mixed-language perspectives |
| Perspective JSON schema | `phases.py` prompt template + `pipeline.py` parsing | Prompt says "EXACTLY this JSON structure"; `extract_json()` + defensive fallback serialize non-standard dicts | `core_analysis` empty; perspective content lost or rendered as raw JSON |
| Deep Read trigger keywords | `pipeline.py` + user problem text | `_edu_keywords` ∪ `_historical_religious_keywords` set intersection with `problem.lower()` | Knowledge-dense topics (religion, history, philosophy) skip deep read; context quality degraded |

---

## 5. CRITICAL ARCHITECTURAL DECISIONS

### 5.1 Universal Pipeline + Method Branching
All methods share the same prefix (classify → decompose → context vetting) and suffix (synthesis). Only the middle section branches. This minimizes code duplication but forces every method to fit the same structural mold.

### 5.2 HyperGateAgent as Pre-Router
Rather than exposing a method dropdown, the backend automatically selects the reasoning method via 6 parallel sub-agents. This simplifies the UI but adds opacity — users cannot force a specific method.

### 5.3 Next.js as Secure API Gateway
The frontend never talks directly to the Python backend. All requests proxy through Next.js API routes, which apply CSRF signing, rate limiting, request validation, and header sanitization. This adds latency but centralizes security policy.

### 5.4 In-Memory Auth & Rate Limiting
Both auth and rate limiting are pure in-memory Python objects. This is simple and fast but makes the system strictly single-process. Multi-worker deployments would require Redis or external state.

### 5.5 Lazy-Loaded PostgreSQL
The PostgreSQL event store is lazy-imported so that missing `asyncpg` does not crash startup. This improves developer experience but hides configuration errors until the first CQRS operation.

### 5.6 Self-Healing CI/CD
The GitHub Actions workflow runs a "Self-Healing CI" with 4 loops: static introspection, auto-generated tests, runtime verification, and evolutionary optimization proposals. This is unique but adds significant CI complexity.

---

## 6. ARCHITECTURAL RISKS & TECHNICAL DEBT

| Risk | Severity | Description |
|------|----------|-------------|
| **Horizontal Scaling Blocker** | High | `_cancelled_runs`, `_active_runs`, `_MEMORY_CACHE`, `AuthManager`, `RateLimiter` are all module-level globals. Multi-process deployments (uvicorn workers) would create split-brain state. |
| **PipelineState God Object** | High | ~100 fields with implicit mutation contracts. Refactoring is risky because any phase may depend on any field. |
| **Neuro Server Coupling** | Medium | Hardcoded `127.0.0.1:50001` URL. No health check before POST. No retry logic. |
| **CQRS Underutilization** | Medium | Event bus, commands, queries, and aggregates exist but are lazily initialized and lightly used. The primary data flow bypasses CQRS and uses direct function calls. |
| **Frontend/Backend Method Sync** | Medium | `METHOD_PHASES` in frontend must match backend method strings. No shared schema contract. |
| **Port Inconsistency** | Low | README says 8000, `.env.example` says 8000, `core/constants.py` says 8001. Already flagged in TODO.md. |
| **SaaS Architecture Drift** | Medium | The codebase is a single-tenant tool. `SAAS.md` and `TODO.md` plan a massive Clean Architecture / Ports & Adapters transformation that does not yet exist in code. |
| **Memory Leak Potential** | Low | `_MEMORY_CACHE` has bounded keys but `_cancelled_runs` and `_active_runs` may leak if `stop_pipeline` or exceptions don't clean up. Rate limiter has FIFO cap. |

---

## 7. TEST INFRASTRUCTURE

| Aspect | Detail |
|--------|--------|
| Framework | pytest 8.4.2 + pytest-asyncio 0.24.0 |
| Collection | ~800 tests |
| Baseline | 483 passed, 303 skipped, 0 failed |
| Markers | `slow`, `integration`, `timeout` |
| Coverage | ~70% estimated; 60% CI gate |
| CI/CD | `.github/workflows/self-healing-ci.yml` |
| Auto-Generated | `healing/generated_tests/` — 19 pytest files from introspection engine |
| Frontend Tests | Vitest 4.1, Playwright 1.59, Testing Library |

---

## 8. DEPLOYMENT MODEL (Current vs Planned)

### Current (Single-Tenant Developer Tool)
```
Developer Machine
├── uvicorn asgi:app --port 8001
├── npm run dev (Next.js port 3000)
├── docker-compose -f docker-compose.searxng.yml up
└── All state in-memory or local filesystem
```

### Planned (SaaS — per SAAS.md)
```
Internet → Nginx/Caddy (TLS termination)
              ├── Next.js Frontend (static + SSR)
              ├── FastAPI Backend (async workers)
              └── SearXNG (search)
              │
              ├── PostgreSQL (primary + read replica)
              ├── Redis (sessions, distributed rate limit, run state)
              └── Stripe (billing webhooks)
```

---

*End of Architecture Mindmap*
