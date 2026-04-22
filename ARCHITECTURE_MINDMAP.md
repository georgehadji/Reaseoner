# Architecture Mindmap

## 1. System Overview
- Reasoner is a multi-method AI reasoning platform for complex analysis, research, and decision support.
- The backend has evolved into a modular monolith under `src/reasoner/`, with clear package boundaries for API, application services, domain logic, infrastructure, phases, and subagents.
- Primary interfaces:
  - CLI shim at `main.py`, which delegates to `src/reasoner/main.py`
  - ASGI/FastAPI backend at `asgi.py` and `src/reasoner/api/`
  - Next.js frontend at `ui-next/`
- Core runtime pattern:
  - Request enters through CLI or API
  - A method/preset is selected explicitly or inferred
  - The pipeline orchestrates phase execution, search/context gathering, critique, and synthesis
  - Results stream back through SSE/WebSocket-aware API surfaces and are rendered in the UI
- Key platform traits:
  - Multi-provider LLM routing
  - Multi-phase reasoning pipeline
  - Method-specific phase modules
  - Search and web-context integration
  - Neuro memory/compression integration
  - Event-driven and persistence-oriented architecture in newer subsystems

## 2. Top-Level Repository Structure
- `src/reasoner/`: Main Python package and canonical backend implementation
- `ui-next/`: Next.js 16 / React 19 frontend
- `tests/`: Primary automated test suite
- `cache/`: Token and response cache artifacts
- `history/`: Persisted run/conversation history artifacts at repo root
- `uploads/`: Uploaded file storage
- `docs/`: Documentation
- `scripts/`: Utility scripts and smoke tests
- `tasks/`: Task tracking and working notes
- `legacy/`: Older utility and maintenance scripts
- Root operational/config files:
  - `asgi.py`
  - `main.py`
  - `start_all.py`
  - `requirements.txt`
  - `pytest.ini`
  - `.env.example`
  - `.searxng-settings.yml`
  - `docker-compose.searxng.yml`
  - `mempalace.yaml`

## 3. Backend Entry Points
- CLI:
  - `main.py`: Thin shim that keeps `python main.py` working
  - `src/reasoner/main.py`: Real CLI implementation, argument parsing, preset/model listing, pipeline execution
- API:
  - `asgi.py`: Adds `src/` to `sys.path` and imports `reasoner.api.app`
  - `src/reasoner/api/__init__.py`: Main FastAPI app assembly
- Service orchestration:
  - `start_all.py` and `src/reasoner/start_all.py`: Multi-service startup helpers

## 4. Backend Package Map (`src/reasoner/`)

### 4.1 Interface Layer
- `api/`: FastAPI app, routing, streaming, serializers, middleware, schemas, run-state handling
  - `routes/`: Focused routers for uploads, images, history, widgets, pipelines, websocket, keys, context
  - `streaming.py`: Streaming pipeline/follow-up responses
  - `serializers.py`: SSE/event payload formatting by phase/event type
  - `middleware.py`: Security headers, memory limits, timeouts

### 4.2 Application Layer
- `application/`: Use cases, orchestration helpers, handlers, queries, flows, mixins, event bus, services
  - `handlers/`: Command/query style orchestration entry points
  - `queries/`: Query objects for state/status retrieval
  - `flows/`: Higher-level workflow coordination such as pipeline flow logic
  - `event_bus/`: Internal publish/subscribe infrastructure
  - `services/`: Search service, preset service, renderer helpers
  - `mixins/`: Shared pipeline/method behavior extracted from monolithic orchestration

### 4.3 Domain/Core Layer
- `domain/`: Domain-centered logic such as preset core/registry concepts
- `core/`: Shared protocols, settings, search primitives, constants, perspective definitions, memory utilities
- `shared/`: Common shared package namespace for cross-cutting helpers

### 4.4 Infrastructure Layer
- `infrastructure/`: External-facing adapters and lower-level implementations
  - `llm/`: Router, provider registry, base classes, provider adapters, image generation, extraction utilities
  - `persistence/`: Event store, snapshots, PostgreSQL storage
  - `websocket/`: Connection manager
  - `widgets/`: Discover, calculator, weather, stocks, image/video search widget backends

### 4.5 Reasoning Runtime
- `pipeline.py`: Main orchestration spine for the reasoning process
- `phases.py`: Shared phase logic and prompt configuration
- `phases/`: Method-specific phase implementations
- `models.py`: Pydantic/data models for requests, state, and structured phase data
- `presets.py`: Method/preset definitions and routing metadata
- `llm.py`: Higher-level provider abstraction and legacy-compatible routing surface
- `parsing.py`: Extraction, repair, and structured parsing helpers
- `renderer.py`: CLI-oriented rendering/output formatting
- `scraper.py`: Web content extraction
- `sanitization.py`: Input/output sanitization
- `pricing.py`: Token/cost accounting logic
- `rate_limiter.py`: Request throttling

### 4.6 Specialized Subsystems
- `subagents/`: Focused agent families for decomposition, critique, enhancement, search, and synthesis
- `hypergate/`: Method selection, routing, complexity detection, and direct/agent decision logic
- `neuro/`: Memory server integration, compression, session handling, provider configuration
- `healing/`: Self-healing, introspection, instrumentation, and generated-test artifacts
- `history/`: Package-local persisted history artifacts and history logic
- `uploads/`: Package-local upload handling

### 4.7 Cross-Cutting Modules
- `auth.py`: Authentication support
- `circuit_breaker.py`: Provider/request resilience
- `exceptions.py`: Exception taxonomy and retry behavior
- `gate_agent.py`: Gate/selection agent logic
- `logging_utils.py`: Logging helpers
- `server_check.py`: Server and environment diagnostics
- `suggestions.py`: Suggestion generation
- `token_cache.py`: Token/cache utilities
- `uploader.py`: Upload helper logic
- `widgets.py`: Widget-related support on the backend side
- `ara_persuasion_defense.py`: Specialized persuasion/defense reasoning support

## 5. Reasoning Methods and Phase Modules
- The method list is broader than the original high-level summary. Current phase modules under `src/reasoner/phases/` include:
  - `multi_perspective`
  - `debate`
  - `jury`
  - `research`
  - `scientific`
  - `socratic`
  - `analogical`
  - `bayesian`
  - `cove`
  - `delphi`
  - `dialectical`
  - `pot`
  - `pre_mortem`
  - `self_discover`
  - `sot`
  - `tot`
  - `writing`
- Shared support files:
  - `_shared.py`
  - `_universal.py`
- Conceptual pipeline shape still centers on:
  - classification/routing
  - decomposition and perspective generation
  - context vetting and deep read
  - critique/scoring/challenge
  - synthesis/final answer construction
- Actual phase/event execution is method-dependent rather than a single rigid sequence for every run.

## 6. API Surface and Runtime Behavior
- `src/reasoner/api/__init__.py` assembles a richer backend than a simple single-router app:
  - FastAPI app creation
  - CORS and security middleware
  - auth and rate-limit dependencies
  - SSE endpoints for runs and follow-ups
  - search endpoint
  - cache clearing
  - cancellation/stop endpoint
  - health endpoint
  - Neuro router mounting
  - widget, history, upload, image, pipeline, websocket, and key-validation routers
- Response streaming is a first-class behavior, especially for pipeline execution and follow-up runs.
- The API layer also bridges older and newer architecture pieces:
  - legacy/compatibility flows through `reasoner.llm` and existing pipeline code
  - newer persistence and handler concepts through `application` and `infrastructure.persistence`

## 7. Diagram-Style Runtime Flow

### 7.1 High-Level Request Path
```text
User
  |
  v
ui-next (Next.js chat UI)
  |
  +--> local UI state / history helpers / stream hooks
  |
  v
FastAPI app (reasoner.api.app)
  |
  +--> middleware: CORS, security headers, memory limits, timeout
  +--> dependencies: auth, rate limiting
  |
  v
API route / streaming handler
  |
  +--> direct utility path
  |     - search
  |     - uploads
  |     - widgets
  |     - image generation
  |
  +--> reasoning path
        |
        v
      HyperGate / method selection / preset selection
        |
        v
      Pipeline orchestration
        |
        +--> phases
        +--> search and scraping
        +--> subagents
        +--> LLM routing
        +--> parsing / validation / repair
        |
        v
      synthesis + event serialization
        |
        +--> SSE stream back to UI
        +--> history / cache / persistence side effects
```

### 7.2 Backend Execution Graph
```text
CLI or API input
  |
  v
src/reasoner/main.py or src/reasoner/api/streaming.py
  |
  v
presets.py + llm.py + hypergate/
  |
  v
pipeline.py
  |
  +--> phases.py
  +--> phases/*.py
  +--> application/services/search_service.py
  +--> scraper.py
  +--> parsing.py
  +--> models.py
  +--> subagents/*
  +--> neuro/*
  +--> infrastructure/llm/*
  |
  v
serializers.py / renderer.py
  |
  +--> CLI rendering
  +--> API event stream
```

### 7.3 Persistence and Side-Effect Paths
```text
Pipeline/API activity
  |
  +--> cache/
  |     - token and response caching
  |
  +--> history/ and src/reasoner/history/
  |     - persisted run artifacts
  |
  +--> infrastructure/persistence/
  |     - event store
  |     - snapshots
  |     - postgres store
  |
  +--> uploads/
  |     - file payload persistence
  |
  +--> neuro/
        - recall/bootstrap context
        - learn/ingest final synthesis
        - compression helpers
```

### 7.4 Frontend Interaction Flow
```text
Composer submit
  |
  +--> web search mode
  +--> image generation mode
  +--> reasoning run mode
          |
          v
      usePipelineStream
          |
          v
      SSE events from backend
          |
          +--> phase timeline updates
          +--> streaming text updates
          +--> rendered phase cards
          +--> final conversation persistence
```

## 8. Frontend Architecture (`ui-next/`)
- Stack:
  - Next.js `16.2.3`
  - React `19.2.4`
  - TypeScript `5`
  - Tailwind CSS `4`
  - Zustand for client state
  - SWR for data fetching where applicable
- Important frontend areas:
  - `src/app/`: App Router entry points, layout, global styles, top-level page
  - `src/components/`: Layout, chat, phases, widgets, UI components
  - `src/hooks/`: Pipeline stream hook, presets, server status, keyboard shortcuts, history
  - `src/stores/`: App state store
  - `src/lib/`: API client, config, markdown transformation, shared types/utilities
- `ui-next/src/app/page.tsx` is the main chat/reasoning surface and coordinates:
  - composer submission
  - web search mode
  - image generation mode
  - streaming pipeline events
  - follow-up flows
  - conversation history loading
  - phase timeline state

## 9. Persistence, History, and Caching
- Persistence is split across multiple concerns:
  - `cache/`: Response/token cache artifacts
  - `history/`: Root-level history JSON artifacts
  - `src/reasoner/history/`: Package-local history data/artifacts
  - `src/reasoner/infrastructure/persistence/`: Event store, snapshots, and PostgreSQL support
  - `src/reasoner/infrastructure/events.db`: Local event database artifact
- This is not just client-side IndexedDB storage; history exists in both frontend-facing and backend-persisted forms.

## 10. Testing Layout
- The repo now uses a dedicated `tests/` directory as the primary suite location.
- Coverage spans:
  - API behavior
  - auth and rate limiting
  - event bus and event store
  - gate/hypergate logic
  - parsing and model handling
  - pipeline regressions
  - presets and routing
  - search quality and searxng integration
  - websocket and widget behavior
  - subagent and synthesis logic
- Additional generated/self-healing tests also exist under `src/reasoner/healing/`.

## 11. Technical Stack
- Backend:
  - Python 3.10+
  - FastAPI
  - Uvicorn
  - Pydantic v2
  - `httpx`
  - Anthropic, OpenAI, and Google Generative AI SDKs
  - `asyncpg` and `aiosqlite`
  - `PyPDF2`, `python-docx`
  - `simpleeval`
  - `yfinance`, `yahooquery`
  - `newspaper3k`, `lxml`
  - `python-dotenv`
  - `psutil`
- Frontend:
  - Next.js
  - React
  - TypeScript
  - Tailwind CSS
  - Zustand
  - SWR
  - `react-markdown`
  - `lucide-react`
- Testing:
  - `pytest`
  - `pytest-asyncio`
  - `pytest-timeout`
  - Vitest
  - Playwright

## 12. Architectural Notes
- The repo shows signs of an active migration from a flatter, more centralized backend toward a more explicit layered architecture.
- There is some duality between:
  - older root-style orchestration modules such as `pipeline.py`, `phases.py`, `llm.py`
  - newer package-oriented application/infrastructure/domain boundaries
- The practical architecture is therefore:
  - a modular monolith
  - with streaming API interfaces
  - multiple reasoning methods
  - growing event-driven/persistence abstractions
  - frontend-first interactive UX around the reasoning pipeline
- `mempalace.yaml` exists but should be documented separately if it becomes operationally important; its role is not obvious from the file name alone.
