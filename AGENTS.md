<!-- From: E:\Documents\Vibe-Coding\Reasoner\AGENTS.md -->
# AGENTS.md — Reasoner (Reasoner Pipeline v2.2)

> This file is written for AI coding agents. It assumes you know nothing about this project.
> Read this first before making any changes.

---

## 1. Project Overview

**Reasoner** (also called Reasoner) is a production-grade AI reasoning orchestrator written in Python with a Next.js frontend. It decomposes complex problems into structured multi-phase pipelines, leverages multiple LLMs from diverse training ecosystems in parallel, applies independent critique, stress-tests solutions, and synthesizes actionable recommendations with epistemic labeling.

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
| LLM Routing | OpenRouter (primary, 346+ models); direct adapters for Anthropic, OpenAI, Google, Perplexity, DeepSeek, Mistral, xAI, Qwen, Kimi, GLM, MiniMax, Ollama |
| Search | SearXNG (self-hosted via Docker Compose), Perplexity Sonar |
| Database | PostgreSQL (asyncpg), SQLite (aiosqlite), SQLAlchemy 2 async ORM, Alembic migrations |
| Cache / Sessions | Redis (quota caching, rate limiting, session store) |
| Auth | Supabase JWT + local JWT fallback, token-based scoped auth |
| Billing | Stripe (checkout, webhooks, pro/enterprise tiers) |
| File Processing | pypdf, python-docx, pymupdf, python-magic |
| Web Scraping | lxml |
| Financial Data | yfinance, yahooquery |
| Math | simpleeval |
| Memory/Cache | Custom token cache, Neuro-based long-term memory with embedding search |
| Security | Custom auth manager, token-bucket rate limiter, circuit breaker, input sanitization, prompt-injection filtering, CSRF HMAC-SHA256 |
| Production WSGI | gunicorn |
| Monitoring | psutil (memory limits), Sentry tracing |

### Frontend (`ui-next/`)
| Layer | Technology |
|-------|------------|
| Framework | Next.js 16.2.3 (App Router) |
| UI Library | React 19.2.4 |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 |
| State | Zustand v5 (client), SWR v2 (server) |
| Persistence | IndexedDB via `idb` v8 |
| Markdown | react-markdown, react-syntax-highlighter, remark-gfm, rehype-highlight |
| Icons | lucide-react |
| Animation | framer-motion |
| Charts | recharts |
| Payments | `@stripe/react-stripe-js` |
| Auth | `@supabase/supabase-js` |
| Error Tracking | `@sentry/nextjs` |
| Testing | Vitest v4, @testing-library/react, @playwright/test |
| Linting | ESLint 9 flat config (`eslint.config.mjs`) |

**Critical frontend note:** Tailwind CSS v4 does **NOT** use a `tailwind.config.ts` file. Configuration is CSS-native via `@import "tailwindcss" in `globals.css` and the `@tailwindcss/postcss` PostCSS plugin. Do **not** create a `tailwind.config.ts`.

---

## 3. Project Structure

### Root Layout
```
Reasoner/
├── main.py                 # CLI entry-point shim → reasoner.main
├── asgi.py                 # ASGI entry point: uvicorn asgi:app --reload --port 8003
├── start_all.py            # Orchestrator shim (starts backend + frontend + SearXNG)
├── start_all.bat           # Windows batch equivalent of start_all.py
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
├── requirements.txt        # Python dependencies (no pyproject.toml / setup.py / setup.cfg)
├── pytest.ini              # Test configuration
├── alembic.ini             # Alembic migration configuration
├── .env / .env.example     # Environment variables (NEVER commit .env)
├── docker-compose.yml      # Full production stack (Caddy, backend, frontend, Postgres, Redis, SearXNG)
├── docker-compose.searxng.yml   # SearXNG-only container setup
├── kill_servers.py         # Utility to kill running backend/frontend processes
├── kill_servers.bat        # Windows batch equivalent
├── push_to_github.py       # Git push helper
├── push_to_github.bat      # Windows batch equivalent
├── tests/                  # 140+ pytest files
├── src/reasoner/           # Main Python package
├── ui-next/                # Next.js frontend
├── cache/                  # Run-related cache
├── docs/                   # Markdown documentation (architecture plans, audits, research)
├── scripts/                # Utility scripts (smoke_test_search.py, scan-secrets.py)
├── skills/                 # Project-specific skill definitions for agents
├── legacy/                 # Legacy modules (health_check.py, alerts.py, audit.py, etc.)
├── .claude/skills/         # Claude-specific skills (ara-add-preset, ara-add-provider, ara-debug, etc.)
├── .github/workflows/      # CI/CD (self-healing-ci.yml)
├── uploads/                # File upload storage
├── history/                # Pipeline run history JSON files (runtime data)
├── logs/                   # Runtime logs (e.g., dead_letter_events.jsonl)
└── vs_vertical_configs/    # Vertical solution configs (aerospace, legal, radiology)
```

### Backend Source (`src/reasoner/`)
```
src/reasoner/
├── __init__.py                    # Package init; __version__ = "2.1.0"
├── main.py                        # CLI entry point with argparse
├── pipeline.py                    # ReasonerPipeline orchestrator
├── models.py                      # Core dataclasses: PipelineState, enums, etc.
├── core/                          # Domain core abstractions (zero I/O)
│   ├── protocol.py                # PhaseConfig, PhaseResult, Phase Protocol
│   ├── constants.py               # Token budgets, defaults, truncation rules, timeouts
│   ├── settings.py                # Pydantic-settings from .env (ONLY env reader)
│   ├── temperatures.py            # Per-phase temperature maps
│   ├── search.py                  # Discovery client for web search
│   ├── memory.py                  # Memory abstractions
│   ├── perspectives.py            # Perspective definitions
│   ├── health_validator.py        # Startup health checks
│   ├── events/                    # Domain events (event sourcing)
│   │   ├── domain_events.py
│   │   └── __init__.py
│   └── aggregates/                # Pipeline aggregate root
│       ├── pipeline.py
│       └── __init__.py
├── domain/                        # Domain logic
│   ├── preset_core.py             # Preset data structures
│   ├── preset_registry.py         # Preset definitions and resolution (24+ presets)
│   ├── saas.py                    # SaaS domain models (User, QuotaResult, tiers)
│   └── __init__.py
├── application/                   # Application layer (CQRS + Event Bus + Mixins)
│   ├── commands/                  # Command handlers
│   ├── event_bus/                 # In-memory event bus with backpressure handling
│   ├── flows/                     # Pipeline flows
│   ├── handlers/                  # Event handlers
│   ├── mixins/                    # Method-specific mixins (13 mixins)
│   │   ├── article_pipeline.py
│   │   ├── coding_pipeline.py
│   │   ├── cognitive_mixin.py
│   │   ├── debate_mixin.py
│   │   ├── delphi_mixin.py
│   │   ├── dialectical_mixin.py
│   │   ├── jury_mixin.py
│   │   ├── perspective_mixin.py
│   │   ├── recovery_mixin.py
│   │   ├── research_mixin.py
│   │   ├── search_mixin.py
│   │   ├── writing_mixin.py
│   │   └── _protocol.py
│   ├── queries/                   # Query handlers
│   └── services/                  # Application services
│       ├── audit_service.py
│       ├── auth_service.py
│       ├── billing_service.py
│       ├── preset_service.py
│       ├── quota_service.py
│       └── search_service.py
├── phases/                        # 17 reasoning method implementations
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
│   ├── writing.py
│   ├── _shared.py
│   └── _universal.py
├── infrastructure/                # Infrastructure layer
│   ├── llm/                       # LLM abstraction
│   │   ├── base.py
│   │   ├── ports.py               # BaseLLMProvider, LLMResponse, LLMConfig, Message
│   │   ├── registry.py            # Model registry (_REGISTRY with 70+ entries)
│   │   ├── router.py              # ProviderRouter
│   │   ├── providers/             # Provider adapters
│   │   │   └── openai_compat.py
│   │   └── extraction/            # JSON extraction utilities
│   ├── persistence/               # Event store, postgres, snapshots, feedback store, auth store
│   │   ├── event_store.py
│   │   ├── feedback_store.py
│   │   ├── postgres_store.py
│   │   ├── snapshots.py
│   │   ├── auth_store.py
│   │   └── __init__.py
│   ├── redis/                     # Redis client, RunStateManager
│   ├── auth/                      # Infrastructure auth implementations
│   ├── billing/                   # Stripe adapter and billing infrastructure
│   ├── websocket/                 # WebSocket manager
│   ├── translation/               # Translation utilities
│   └── widgets/                   # Widget registry (calculator, stocks, weather, etc.)
├── api/                           # FastAPI application
│   ├── __init__.py                # App factory, CORS, rate limiter, security middleware
│   ├── saas_router.py             # SaaS routes (auth, quota, history)
│   ├── billing_router.py          # Stripe billing routes
│   ├── metrics.py                 # Prometheus metrics endpoint
│   ├── cron.py                    # Scheduled task endpoints
│   ├── schemas.py                 # Pydantic v2 request/response models
│   ├── serializers.py
│   ├── streaming.py               # SSE streaming utilities
│   ├── middleware.py              # Custom middleware (security, audit, memory, timeout)
│   ├── auth_deps.py               # Auth dependency injection
│   ├── cache.py
│   ├── csrf.py
│   ├── history.py
│   ├── run_state.py
│   └── routes/                    # REST/SSE route modules
│       ├── context.py
│       ├── history.py
│       ├── images.py
│       ├── keys.py
│       ├── legacy_widgets.py
│       ├── pipelines.py
│       ├── uploads.py
│       ├── websocket.py
│       └── widgets.py
├── hypergate/                     # HyperGate pre-router
│   ├── hyperagent.py
│   ├── base_sub_agent.py
│   ├── models.py
│   └── sub_agents/                # 6 parallel sub-agents
│       ├── complexity_estimator.py
│       ├── direct_detector.py
│       ├── language_detector.py
│       ├── method_classifier.py
│       ├── tie_breaker.py
│       └── web_detector.py
├── subagents/                     # Phase sub-agents
│   ├── base.py
│   ├── models.py
│   ├── enhancement/
│   │   ├── ambiguity_detector.py
│   │   ├── context_enricher.py
│   │   ├── hyper_agent.py
│   │   └── scope_narrower.py
│   ├── decomposition/
│   │   ├── coverage_validator.py
│   │   ├── hyper_agent.py
│   │   ├── stakeholder_mapper.py
│   │   └── structural_decomposer.py
│   ├── critique/
│   │   ├── bias_critique.py
│   │   ├── counterfactual.py
│   │   ├── evidence_critique.py
│   │   ├── hyper_agent.py
│   │   └── logic_critique.py
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
│   ├── generated_tests/           # Auto-generated pytest files
│   └── README.md
├── security/                      # URL validation, security utilities
├── vs_vertical_configs/           # Vertical solution configs
├── utils/                         # json_safe.py and general utilities
├── logs/                          # Runtime log storage
├── documents/                     # Document vector store
├── history/                       # Pipeline run history storage
├── uploads/                       # Uploaded file storage
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
│   ├── page.tsx                   # Main application UI (large client component)
│   ├── globals.css                # Tailwind v4 import + CSS custom properties
│   ├── providers.tsx              # next-themes ThemeProvider
│   ├── error.tsx                  # Error boundary
│   └── api/                       # API route handlers (proxies to FastAPI)
│       ├── run/route.ts
│       ├── run-followup/route.ts
│       ├── stop/route.ts
│       ├── presets/route.ts
│       ├── search/route.ts
│       ├── calculate/route.ts
│       ├── stocks/route.ts
│       ├── weather/route.ts
│       ├── upload/route.ts
│       ├── generate-image/route.ts
│       ├── estimate/route.ts
│       ├── feedback/route.ts
│       ├── cache/route.ts
│       ├── csrf/route.ts
│       ├── billing/               # Stripe checkout session routes
│       └── neuro/                 # Neuro memory routes
│           ├── health/route.ts
│           ├── learn/route.ts
│           ├── recall/route.ts
│           └── sessions/route.ts
├── components/
│   ├── chat/                      # ChatFeed, ChatMessage, MarkdownRenderer, Composer, CodeBlock, ErrorMessage, ManifestationVisuals, TypewriterMarkdown
│   ├── layout/                    # Sidebar, PhaseTimeline, ShortcutModal, CommandPalette, NeuroPanel, Composer
│   ├── phases/                    # PhaseRenderer, PhaseCard, ClassificationCard, CritiqueCard, SynthesisCard
│   ├── ui/                        # Button, Badge, Spinner, ThemeToggle, Tooltip
│   │   └── index.ts
│   └── widgets/                   # WidgetRenderer, CalculationWidget, StockWidget, WeatherWidget
├── hooks/                         # usePipelineStream, useWebSocketPipeline, useKeyboardShortcuts, useConversationHistory, useServerStatus, useScrollAnchor, useFeatureFlags, usePresets
├── lib/                           # api-client, config, db (IndexedDB), types, utils, security-server, security-client, server-config, sse-reader, markdown, animation-cache, method-hints, conversation-history
├── stores/
│   └── app-store.ts               # Zustand store with persistence
└── proxy.ts
```

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
uvicorn asgi:app --reload --port 8003

# Run tests
python -m pytest -v
python -m pytest test_parsing.py test_models.py test_perplexity_config.py
python -m pytest -m "not slow"          # Skip slow tests
python -m pytest --run-slow             # Include slow tests
python -m pytest -m searxng             # SearXNG integration tests (requires live instance)

# With coverage
python -m pytest tests/ --cov=src/reasoner --cov-report=html

# Python linting (no formal config file — manual consistency)
ruff check src/reasoner/
ruff format src/reasoner/

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend
```bash
cd ui-next
npm install
npm run dev          # Development server (http://localhost:3000)
npm run build        # Production build
npm run lint         # ESLint (flat config)
```

### Full Stack (Local)
```bash
# One-command start (backend + frontend + SearXNG)
python start_all.py

# Or individually:
uvicorn asgi:app --reload --port 8003
docker compose -f docker-compose.searxng.yml up -d
cd ui-next && npm run dev

# Full production stack (Caddy, backend, frontend, Postgres, Redis, SearXNG)
docker compose up -d
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
- **Type hints:** Prefer type hints when intent is unclear; use `from __future__ import annotations` at the top of files when using modern typing
- **Docstrings:** Use triple-double-quote docstrings for modules and public functions
- **Imports:** Group stdlib, third-party, and local imports separately
- **No formal linter config** (no `ruff.toml`, `mypy.ini`, or `.pre-commit-config.yaml`) exists at repo root. Rely on manual consistency.

### TypeScript / Frontend
- **Components:** PascalCase files, default export for page components
- **Hooks:** `useCamelCase`
- **Styling:** Tailwind CSS v4 utility classes
- **Accent colors:** Preserve the `--method-accent-rgb` CSS custom property when adjusting gradients or glass panels
- **UI blocks:** Document new helper UI blocks in the same file rather than scattering markup elsewhere
- **ESLint:** Uses ESLint 9 flat config (`eslint.config.mjs`) extending `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`

---

## 6. Testing Strategy

- **Framework:** pytest with pytest-asyncio, pytest-timeout
- **Location:** `tests/` directory at repo root
- **Count:** 140+ test files
- **Naming:** `test_*.py` files, `Test…` classes
- **Configuration:** `pytest.ini` sets `testpaths = tests` and `pythonpath = src`
- **Markers:**
  - `slow` — deselect with `-m "not slow"`; include with `--run-slow`
  - `integration` — integration tests
  - `timeout` — tests with timeout threshold (requires pytest-timeout)
  - `searxng` — tests requiring a live SearXNG instance
- **Async config:** `asyncio_mode = auto` and `asyncio_default_fixture_loop_scope = session` in `pytest.ini`. All async fixtures share a single event loop for the entire test session because the project uses in-memory singletons (rate limiter, circuit breaker, auth store) that persist across tests.
- **Fixtures:** Defined in `tests/conftest.py`:
  - `sample_pipeline_state`, `sample_llm_messages`, `sample_llm_config`, `mock_llm_response`
  - `sample_widget_params`, `sample_domain_events`
  - `searxng_container` (session-scoped Docker compose fixture), `searxng_client`
  - `run_state_store`, `temp_event_store`
  - `event_loop_policy` (Windows-compatible selector event loop)
  - `writable_temp_dirs` (session-scoped autouse)
  - `clear_token_cache` (async autouse to prevent stale cache hits)
- **Test environment:** `CSRF_ENFORCE_BACKEND` is set to `"false"` in `conftest.py` so tests do not need CSRF tokens.
- **Coverage target:** ~70%, minimum gate 60% (enforced in CI)
- **Guidelines:**
  - Add regression coverage when fixing parsing, routing, or UI rendering bugs
  - Assert on both happy and fallback paths
  - Use `pytest --run-slow` to include slow tests
  - `--durations=10` is enabled by default to show the 10 slowest tests per run

---

## 7. Configuration & Environment

### Required Environment Variables (`.env`)
Copy `.env.example` to `.env` and fill in:

**LLM API Keys**
| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Primary LLM access (recommended single key for 346+ models) |
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

**Security & Admin**
| Variable | Purpose |
|----------|---------|
| `ADMIN_API_KEY` | Required for production admin endpoints; generate with `secrets.token_urlsafe(32)` |
| `CSRF_SECRET` | HMAC-SHA256 signing secret; generate with `secrets.token_urlsafe(32)` |
| `ENVIRONMENT` | `development` or `production`; omitting defaults CORS to dev mode (insecure) |

**Server & Networking**
| Variable | Purpose |
|----------|---------|
| `DEBUG` | Must be `false` in production |
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `SERVER_HOST` / `SERVER_PORT` | FastAPI bind address (default 127.0.0.1:8003) |
| `UVICORN_HOST` | Uvicorn bind host (default 127.0.0.1; use 0.0.0.0 in containers) |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `REASONER_API_URL` | Frontend proxy target (default http://localhost:8003) |
| `TRUSTED_PROXIES` | Comma-separated IPs for X-Forwarded-For parsing (optional) |

**Rate Limiting & Resilience**
| Variable | Purpose |
|----------|---------|
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_HOUR` / `RATE_LIMIT_BURST` | Token-bucket config |
| `RATE_LIMITER_MODE` | `memory` (default, unsafe for multi-worker) or `redis` |
| `CIRCUIT_BREAKER_MODE` | `memory` (default, unsafe for multi-worker) or `redis` |
| `MEMORY_LIMIT_MB` / `MEMORY_WARNING_MB` | Process memory limits |
| `REQUEST_TIMEOUT_SECONDS` | Request timeout (default 300) |

**Search & Documents**
| Variable | Purpose |
|----------|---------|
| `SEARXNG_URL` | SearXNG instance URL (default: http://localhost:8888) |
| `COHERE_RERANK_ENABLED` | Enable Cohere reranking via OpenRouter |
| `DOCUMENT_SEMANTIC_RETRIEVAL_ENABLED` | Opt-in semantic chunking for uploaded files |
| `DOCUMENT_CHUNK_SIZE` / `DOCUMENT_CHUNK_OVERLAP` / `DOCUMENT_MAX_CHUNKS_PER_FILE` | Chunking params |

**SaaS Auth**
| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase project credentials |
| `JWT_SECRET_KEY` | Local dev JWT fallback when Supabase is unavailable |
| `ENABLE_LEGACY_API_KEY` | Set `true` for v1 API backward compatibility |

**Database & Cache**
| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (default with asyncpg driver) |
| `POSTGRES_PASSWORD` | Standalone Postgres password |
| `DB_POOL_SIZE` | Asyncpg connection pool size (default 10) |
| `REDIS_URL` | Redis connection string (default redis://localhost:6379/0) |

**Stripe Billing**
| Variable | Purpose |
|----------|---------|
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe API and webhook secrets |
| `STRIPE_PRO_PRICE_ID` / `STRIPE_ENTERPRISE_PRICE_ID` | Product price IDs |
| `APP_URL` | Frontend URL for checkout redirects (default http://localhost:3000) |

**Git Integration (Optional)**
| Variable | Purpose |
|----------|---------|
| `ORCHESTRATOR_GIT_ENABLED` | Enable Git integration |
| `ORCHESTRATOR_GIT_STRATEGY` | `manual`, `after_each_task`, `after_phase`, or `after_project` |
| `ORCHESTRATOR_GIT_AUTO_PUSH` | Auto-push to remote (use with caution) |

**NEVER commit `.env` with real values.**

---

## 8. Security Considerations

- **Input Sanitization:** All user inputs pass through `reasoner.sanitization.sanitize_for_prompt()` before reaching LLM prompts
- **Prompt Injection Defense:** Layered filtering in sanitization module + adversarial persuasion defense (`reasoner_persuasion_defense.py`)
- **XSS Prevention:** Regex-based `<script>` stripping, HTML tag removal, NFKC normalization in `RunRequest.validate_problem()`
- **Rate Limiting:** Token-bucket rate limiter per client IP (`rate_limiter.py`); Redis backend available for multi-worker deployments
- **Authentication:** Token-based auth with scoped permissions (`auth.py`); Supabase JWT primary, local JWT fallback
- **Circuit Breaker:** Automatic fallback when providers fail (`circuit_breaker.py`)
- **CSRF Protection:** CSRF token endpoints for state-changing operations (HMAC-SHA256 signed, verified in Next.js API routes **and** FastAPI backend via `require_csrf`)
- **Security Headers:** X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS (production), dynamic CSP with WebSocket origin allowlist
- **CORS:** Restricted to known origins (configurable via `CORS_ORIGINS` env var) with an explicit header whitelist
- **Frontend proxy validation:** Next.js API routes validate upstream URLs against port allowlists and block private IPs in production
- **Admin endpoint hardening:** Admin endpoints require BOTH a valid JWT with `admin` scope AND a correct `X-Admin-Key` header; uses `secrets.compare_digest()` for constant-time comparison
- **Environment guard:** `ENVIRONMENT=development` explicitly logs an insecure-CORS warning on startup
- **Horizontal Scaling Limitations:** Rate limiter, circuit breaker, and auth store are in-memory by default. For multi-worker deployments, enable `AUTH_PERSISTENCE_ENABLED=true`, set `RATE_LIMITER_MODE=redis` / `CIRCUIT_BREAKER_MODE=redis`, and place a shared rate limiter (e.g., Redis or reverse-proxy) in front of the app.

---

## 9. Architecture Patterns

1. **Event Sourcing** — Pipeline state derived from domain events stored in SQLite/PostgreSQL
2. **CQRS** — Separate command and query handlers in `application/`
3. **Hexagonal Architecture** — Domain depends on protocols (Widget, Phase), not concrete implementations
4. **Mixin Pattern** — Method-specific behaviors composed via 13 mixins; explicit `PipelineMixinProtocol` contract
5. **Provider Router with Fallbacks** — Cross-lab diversity with automatic fallback on failure; `_REGISTRY` maps 70+ model IDs
6. **HyperGate Pre-Routing** — 6 parallel sub-agents detect language, complexity, directness, web need, and optimal method
7. **Token Optimization** — Phase-specific budgets (`PHASE_TOKEN_BUDGETS`), context compression (`ContextCompressor`), token-aware caching
8. **Security in Depth** — Input sanitization, prompt injection filtering, rate limiting, scoped auth, CSRF protection, XSS prevention
9. **Dual-Stream Frontend** — SSE carries all phase data/events; WebSocket is used ONLY for control signals (stop, status) to avoid double-processing
10. **SaaS-Ready** — Supabase auth, Stripe billing, Redis caching, PostgreSQL persistence, quota enforcement, tiered presets

---

## 10. Working with Neuro & Compression

- **Recall (Bootstrap):** `neuro.server.create_neuro_router()` provides the `Recall` endpoint. Automatically called in `ReasonerPipeline.run` to fetch relevant context from long-term memory.
- **Learn (Ingest):** The `Learn` endpoint is called at the end of the pipeline to save the final synthesis. Tag entries with metadata (e.g., `preset`, `task_type`).
- **Compression:** Use `neuro.compression.smart_compress(text, ext, level)` to reduce token usage. Modes:
  - `Aggressive` — structural analysis, keeps only signatures
  - `Minimal` — general cleanup
- **Tenant Isolation:** Use `agent_id` in Neuro requests to ensure data is stored in separate directories (`~/.neuro/agents/<id>`).

---

## 11. Reasoning Methods (17)

The pipeline supports 17 reasoning methodologies. Each method has its own phase module and renderer:

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
