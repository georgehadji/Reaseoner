# TODO - Implementation Status

## ✅ Completed Features

### 1. Iterative RAG + Specialized Sources
- **Status**: ✅ Implemented
- **Changes**:
  - `_phase_context_vetting` now uses iterative loop (max 3 iterations)
  - LLM decides if more searches are needed based on current results
  - Added `source_type` parameter: general, academic, social, news, code
  - Added `SOURCE_TYPE_ENGINES` mapping for SearXNG engine filtering
  - New prompts: `ITERATIVE_CONTEXT_SYSTEM`, `iterative_context_prompt`

### 2. External Context API Integration
- **Status**: ✅ Implemented
- **Changes**:
  - New API endpoint: `POST /api/run-with-context`
  - Accepts external context (facts, URLs, summaries)
  - Runs Jury or Multi-Perspective method on provided data
  - Returns structured, validated answer
  - New status endpoint: `GET /api/ui/status`

### 3. Deep Read Phase (ScrapeURL)
- **Status**: ✅ Implemented
- **Changes**:
  - New module: `scraper.py` with `scrape_url()` and `scrape_urls()`
  - Simple HTML to Markdown conversion (lightweight turndown alternative)
  - New phase: `_phase_deep_read()` in pipeline
  - Fetches full content from critical sources
  - Added to API phase sequence

### 4. Ollama Support (Local LLMs)
- **Status**: ✅ Implemented
- **Changes**:
  - Added 8 Ollama models to registry: llama3, llama3.1, llama3.2, mistral, codellama, qwen2, gemma2, phi3
  - Supports custom base URL via `OLLAMA_BASE_URL` env var
  - Works with any dummy API key
  - Added "ollama" to model groups

### 5. Domain-specific Search
- **Status**: ✅ Implemented
- **Changes**:
  - Added `domain` parameter to `DiscoveryClient.search()`
  - Uses `site:` operator for domain filtering
  - Added `--domain` CLI argument
  - Added `domain` field to `RunRequest` and pipeline

### 6. Search History
- **Status**: ✅ Implemented
- **Changes**:
  - New `history/` directory for storage
  - New API endpoints: `/api/history`, `/api/history/{id}`, DELETE variants
  - Auto-saves completed runs to history
  - History entries include problem, preset, method, timestamp, tokens, status

### 7. File Uploads
- **Status**: ✅ Implemented
- **Changes**:
  - New module: `uploader.py` with text extraction
  - Supports PDF (PyPDF2), TXT, DOCX (python-docx)
  - New API endpoints: `/api/upload`, `/api/uploads`, `/api/upload/{file_id}`
  - Max file size: 10MB

### 8. Citation System
- **Status**: ✅ Implemented
- **Changes**:
  - Updated `SYNTHESIS_SYSTEM` prompt with citation requirements
  - Added `sources` field to `FinalSolution` model
  - Promotes citation format: [title](url)
  - Includes web sources in synthesis prompt

### 9. Smart Widgets (NEW - 2026-03-14)
- **Status**: ✅ Implemented
- **Changes**:
  - **Smart Suggestions**: Template-based query suggestions with topic detection
  - **Weather Widget**: Open-Meteo integration with 3-day forecast
  - **Stock Widget**: Yahoo Finance integration (yahooquery/yfinance)
  - **Calculator Widget**: mathjs expression evaluation
  - **Discover Mode**: Trending content aggregation by topic (tech, finance, science, sports, entertainment)
  - **Image Search**: SearXNG image search integration
  - **Video Search**: SearXNG video search integration
  - **Auto-detection**: Widgets automatically shown based on query patterns
  - New modules: `suggestions.py`, `widgets.py`
  - New API endpoints: `/api/suggestions`, `/api/weather`, `/api/stocks`, `/api/calculate`, `/api/discover`, `/api/images`, `/api/videos`
  - UI integration: Suggestions box, widget renderer, auto-detection logic

### 10. Hexagonal Architecture (NEW - 2026-03-14 Phase 2)
- **Status**: ✅ Implemented
- **Changes**:
  - **Domain Layer**: `core/events/`, `core/aggregates/`
  - **Application Layer**: `application/commands/`, `application/queries/`, `application/handlers/`, `application/event_bus/`
  - **Infrastructure Layer**: `infrastructure/llm/` (ports + adapters), `infrastructure/widgets/`, `infrastructure/persistence/`, `infrastructure/websocket/`
  - **LLM Provider Ports**: Protocol-based abstraction for 11 providers
  - **Event Sourcing**: 28 domain event types, aggregate state reconstruction
  - **CQRS**: Command/Query separation, read model projections

### 11. Full Pipeline Migration (NEW - 2026-03-14 Phase 2)
- **Status**: ✅ Implemented
- **Changes**:
  - **Debate Method**: Opening → Rebuttals (2) → Closing → Judge
  - **Research Method**: Iterative search (3 iterations) → Analysis → Synthesis
  - **Socratic Method**: Position → Elenchus → Aporia → Maieutics → Understanding
  - **Event Recording**: All phases record domain events
  - **Aggregate Integration**: Pipeline uses `PipelineAggregate` for state

### 12. PostgreSQL Support (NEW - 2026-03-14 Phase 2)
- **Status**: ✅ Implemented
- **Changes**:
  - `PostgreSQLEventStore` with asyncpg
  - Table partitioning by aggregate type
  - Full-text search on event payloads
  - Read replica support
  - Connection pooling
  - CQRS read model tables

### 13. WebSocket Integration (NEW - 2026-03-14 Phase 2)
- **Status**: ✅ Implemented
- **Changes**:
  - `WebSocketManager` for connection management
  - Real-time event broadcasting
  - Pipeline-specific subscriptions
  - Heartbeat/ping-pong for connection health
  - Event bus integration for auto-broadcast
  - API endpoints: `/ws`, `/ws/pipeline/{id}`, `/api/websocket/stats`

### 14. Snapshot Strategy (NEW - 2026-03-14 Phase 2)
- **Status**: ✅ Implemented
- **Changes**:
  - `SnapshotStrategy` with multiple strategies:
    - Version-based (every N events)
    - Time-based (every N seconds)
    - Phase-based (after each phase)
  - `SnapshotManager` for coordination
  - Fast aggregate reconstruction from snapshots
  - Performance optimization: O(n) → O(k) where k << n

### 15. CQRS Read Models (NEW - 2026-03-14 Phase 2)
- **Status**: ✅ Implemented
- **Changes**:
  - `ReadModelProjection` for denormalized views
  - `project_pipeline_list()` - Optimized listing
  - `project_pipeline_stats()` - Aggregated statistics
  - Event-driven updates via event bus
  - PostgreSQL-specific read model tables

### 16. SRE Reliability Pass — Pipeline Hardening (2026-03-15)
- **Status**: ✅ Fixed
- **Branch**: `security-fixes-implementation`
- **Files changed**: `pipeline.py`, `models.py`, `phases.py`, `main.py`, `api.py`, `renderer.py`
- **Bugs fixed**:
  1. **`asyncio.gather` silent drops** — 5 parallel gather calls missing `return_exceptions=True`; a single LLM failure silently emptied the entire phase result. Fixed with per-task exception handling that logs to `state.errors` and continues with partial results.
  2. **`CritiqueScore` missing field** — `confidence_vs_accuracy_penalty` was in the LLM prompt but absent from the dataclass; `CritiqueScore(**data)` raised `TypeError` on every phase-3 execution, crashing Multi-Perspective, Iterative, Scientific. Added field with `default=0.0` for backward compat.
  3. **`SolutionCandidate.content` None propagation** — `data.get("core_analysis")` returns `None` when key absent; downstream `c.content[:400]` raised `TypeError`. Guarded with `or ""` / `or []`.
  4. **Debate rebuttal `IndexError`** — `_phase_debate_rebuttal` indexed `statements[0]` and `[1]` without length guard; now possible to have <2 statements after `return_exceptions` fix. Added early-return guard.
  5. **Dead recovery path** — `_run_recovery_path` called `phases.CROSS_VERIFICATION_SYSTEM` and `phases.cross_verification_prompt` which did not exist. Added both to `phases.py`.
  6. **Missing imports in pipeline.py** — `import json` and `from dataclasses import asdict` absent; `json.dumps()` and `.to_dict()` in recovery path raised `NameError`/`AttributeError`. Added imports; replaced `.to_dict()` with `asdict()`.
  7. **`main.py` CLI broken** — 7 unterminated string/f-string literals (literal newlines inside quotes instead of `\n`); plus smart-quote corruption in argparse help. Fixed all, restoring CLI entry point.
  8. **Global cancel-flag race condition** — `_cancel_flag: bool` shared across all concurrent SSE requests; stopping one run could cancel another. Replaced with per-run `_cancelled_runs: dict[str, bool]` keyed by `uuid4()`; stop endpoint targets `_active_run_id`.
  9. **Renderer TOCTOU `KeyError`** — `state.scientific_state["hypotheses"]` subscript used after `state.scientific_state.get("hypotheses")` truthiness check; not atomic. Stored `.get()` result in local variable for all 4 locations in Scientific/Socratic renderers.
  10. **Cache file corruption** — `_load_cache()` uncaught `JSONDecodeError` on corrupt files; `_save_cache()` non-atomic `write_text()` could leave truncated files on crash. Added try/except + deletion for reads; `.tmp` write + `Path.replace()` atomic rename for writes.
  11. **DiscoveryClient resource leak** — `reset_discovery_client()` nulled global reference without calling `aclose()`, leaking httpx connection pool. Save old client, schedule `aclose()` on event loop (or `asyncio.run()` fallback).
  12. **Empty API key accepted** — `build_provider()` accepted empty string from `os.environ.get(key, "")` as valid API key; error only surfaced at first SDK call with opaque auth. Added early `ValueError` if key is empty and provider is not `is_local`.

### 17. SRE Reliability Pass — Resume & Deserialization (2026-03-15, Pass 4)
- **Status**: ✅ Fixed
- **Branch**: `security-fixes-implementation`
- **Files changed**: `models.py`, `pipeline.py`
- **Bugs fixed**:
  13. **`--resume` crashes on Decomposition** — `Decomposition(**dec)` in `_from_dict` fails with `TypeError`: LLM returns extra keys (causal_chain, critical_sources, systemic_connections, etc.) not in the dataclass, and `raw_response` had no default. Added `raw_response: str = ""` default; filter unknown keys via `dc_fields()` before unpacking in `_from_dict`.
  14. **Phase-3 critique TypeError** — `CritiqueScore(**s)` from raw LLM dict has 6 required fields with no defaults; any omitted field crashes with `TypeError`, leaving `state.scores` empty and synthesis without input. Replaced both call sites with `_parse_critique_scores()` helper using `.get()` with defaults for all fields and enum coercion for `perspective`.
  15. **Stress test scenario type mismatch** — `StressTestResult(**st)` bypasses `ScenarioType.coerce()` (used in `_from_dict`), so live run stores raw string if LLM uses variant spelling (e.g., "constraint-violation"). Replaced with explicit construction calling `coerce()` for consistency between live run and `--resume`.

### 18. SRE Reliability Pass — Input Validation & Resume Robustness (2026-03-15, Pass 5)
- **Status**: ✅ Fixed
- **Branch**: `security-fixes-implementation`
- **Files changed**: `models.py`, `pipeline.py`
- **Bugs fixed**:
  16. **Search queries silent type corruption** — `data.get("queries", [])[:3]` slices a string if the LLM returns `"queries": "search term"` instead of a list, producing single characters ("s", "e", "a") that are silently sent as search queries. Added `isinstance(list)` guard at both call sites (context-vetting phase and research phase).
  17. **Assumption deserialization KeyError** — `a['text']`, `a['label']`, `a['rationale']` in `_from_dict` used direct subscripts; any assumption missing `rationale` (common in partial state files) crashed `--resume` with `KeyError`. Replaced with `.get()` + fallback defaults and a per-entry try/except.
  18. **CriticDimensionScore / CriticScore TypeError on Jury resume** — `CriticDimensionScore(**v)` and `CriticScore(**cs)` have required fields with no defaults; a truncated state file caused `TypeError` crashing the entire resume. Replaced with explicit field-by-field `.get()` construction and nested try/except to skip malformed entries.

### 19. SRE Reliability Pass — Widget Bugs & Resume Consistency (2026-03-15, Pass 6)
- **Status**: ✅ Fixed
- **Branch**: `security-fixes-implementation`
- **Files changed**: `widgets.py`, `api.py`, `models.py`
- **Bugs fixed**:
  19. **Weather widget function shadowing** — Sync `get_weather_data()` (line 194) overwrote the async version (line 117). `/api/weather` called the sync version from FastAPI's event loop → `RuntimeError: This event loop is already running`. The sync wrapper called `get_weather_data_async()` which called `await get_weather_data()` (sync version) → infinite recursion / RuntimeError. Removed both the sync wrapper and `get_weather_data_async()`; api.py now `await`s the async function directly.
  20. **Stock widget None arithmetic** — `info.get("currentPrice", 0)` returns `None` when Yahoo Finance returns the key with a null value. `None - 0` raised `TypeError`. Replaced with `or 0` guard; division guarded with `if _prev else 0.0`.
  21. **Stress results `_from_dict` direct subscripts** — `sr['scenario']`, `sr['survival_rate']`, etc. in `_from_dict` raised `KeyError` on `--resume` with partial/older state files. Replaced with `.get()` + `ScenarioType.coerce()` + per-entry try/except, matching the BUG-015 fix applied to the live pipeline.

---

## 📊 Implementation Summary

| Category | Features | Status |
|----------|----------|--------|
| **Reasoning Methods** | 7 (Multi-Perspective, Debate, Jury, Research, Scientific, Socratic, Iterative) | ✅ Complete |
| **Smart Widgets** | 6 (Weather, Stocks, Calculator, Discover, Image, Video) | ✅ Complete |
| **LLM Providers** | 11 (Anthropic, OpenAI, Google, xAI, Perplexity, +6 OSS) | ✅ Complete |
| **Event Sourcing** | 28 event types, aggregate reconstruction | ✅ Complete |
| **Persistence** | SQLite (default), PostgreSQL (production) | ✅ Complete |
| **Real-time** | SSE streaming, WebSocket, Event Bus | ✅ Complete |
| **Performance** | Snapshots, Read Models, Connection Pooling | ✅ Complete |
| **Tests** | 4 test modules (events, aggregates, bus, widgets) | ✅ Complete |

**Total New Code (Phase 2):** ~3,000+ lines

---

## CLI Usage

```bash
# With source type
python main.py --problem "Your question" --preset max-quality --source-type academic

# With domain-specific search
python main.py --problem "Your question" --preset max-quality --domain github.com

# With local Ollama model
python main.py --problem "Your question" --preset ollama-llama3

# Available source types: general, academic, social, news, code
```

## API Usage

```bash
# Run with external context
curl -X POST http://localhost:8000/api/run-with-context \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "What are the latest advances in AI?",
    "context": [
      {"url": "https://example.com", "title": "AI Advances", "content": "..."}
    ],
    "method": "jury",
    "preset": "jury-premium"
  }'

# Check UI integration status
curl http://localhost:8000/api/ui/status

# History endpoints
curl http://localhost:8000/api/history
curl -X DELETE http://localhost:8000/api/history/{id}

# WebSocket (real-time updates)
ws://localhost:8000/ws?pipeline_id=xxx
```

## Environment Variables

```bash
# For Ollama (local models)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=any  # dummy value

# For file extraction (optional)
pip install PyPDF2 python-docx

# For PostgreSQL (production)
DATABASE_URL=postgresql://user:pass@localhost:5432/reasoner
USE_POSTGRES=true
POSTGRES_POOL_SIZE=20
```

---

## CLI Usage

```bash
# With source type
python main.py --problem "Your question" --preset max-quality --source-type academic

# With domain-specific search
python main.py --problem "Your question" --preset max-quality --domain github.com

# With local Ollama model
python main.py --problem "Your question" --preset ollama-llama3

# Available source types: general, academic, social, news, code
```

## API Usage

```bash
# Run with external context
curl -X POST http://localhost:8000/api/run-with-context \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "What are the latest advances in AI?",
    "context": [
      {"url": "https://example.com", "title": "AI Advances", "content": "..."}
    ],
    "method": "jury",
    "preset": "jury-premium"
  }'

# Check UI integration status
curl http://localhost:8000/api/ui/status

# History endpoints
curl http://localhost:8000/api/history
curl -X DELETE http://localhost:8000/api/history/{id}

# File upload
curl -X POST -F "file=@document.pdf" http://localhost:8000/api/upload
```

## Environment Variables

```bash
# For Ollama (local models)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=any  # dummy value

# For file extraction (optional)
pip install PyPDF2 python-docx
```

---

## Implementation Order Recommendation (Future)

1. **Citations UI** - Render clickable citations in web UI
2. **Provider Management UI** - Dynamic provider configuration
3. **Smart Suggestions** - Query suggestions endpoint
4. **Widgets** - Weather, stocks, calculations
5. **Image/Video Search** - Separate search endpoints
6. **Discover Mode** - Trending content aggregation