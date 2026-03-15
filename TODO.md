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

### 20. SRE Reliability Pass — Provider Safety & API Robustness (2026-03-15, Pass 7)
- **Status**: ✅ Fixed
- **Branch**: `security-fixes-implementation`
- **Files changed**: `api.py`, `llm.py`
- **Bugs fixed**:
  22. **Cache/History clear crashes on locked files** — `f.unlink() or True` in `clear_cache()` and `clear_history()` — if `unlink()` raises `OSError` (file locked on Windows, permission denied), the exception propagates and crashes the DELETE endpoint. Also `or True` is semantically misleading (always truthy). Replaced with explicit for-loop + try/except per file.
  23. **OpenAI/Mistral empty choices IndexError** — `response.choices[0]` in `OpenAICompatibleProvider.complete()` and `MistralProvider.complete()` raises `IndexError` when the provider returns an empty choices array (content filtering, moderation, malformed response). Added `if not response.choices` guard that raises `ProviderUnavailableError` with context.
  24. **Anthropic empty content IndexError + None propagation** — `response.content[0].text` in `AnthropicProvider.complete()` raises `IndexError` on empty content array; if `.text` is `None`, returns `None` to the JSON parser instead of an empty string. Added `if not response.content` guard + `or ""` fallback.

---

## 🎯 Sprint 1+2: Method Improvements & 6 New Reasoning Methods (2026-03-16)

### Track A — Existing Method Improvements (5 surgical patches)

#### A1. Scientific: Inline Bayesian Posterior Update
- **Status**: ✅ Implemented
- **Files changed**: `pipeline.py`, `renderer.py`
- **Changes**:
  - Added Bayesian posterior computation in `_phase_scientific_test()` after test results collected
  - Computes `posterior_probability = supported_count / total_tests` for each hypothesis
  - Stores updated hypotheses in `state.scientific_state["hypotheses"]`
  - Renderer now displays posterior probabilities alongside hypotheses
  - Scientific method now properly integrates test evidence into hypothesis strength

#### A2. Iterative: Early Convergence Exit
- **Status**: ✅ Implemented
- **Files changed**: `pipeline.py`
- **Changes**:
  - Added convergence check in `_run_iterative_pipeline()` after each round's critique phase
  - Computes mean `logical_consistency` score across all solution candidates
  - Exits early if mean score ≥ 8.5 (threshold for "converged solution")
  - Saves tokens by avoiding unnecessary rounds when solution quality is high

#### A3. Jury: Reliability-Weighted Generator Ranking
- **Status**: ✅ Implemented
- **Files changed**: `pipeline.py`, `renderer.py`
- **Changes**:
  - Added `_phase_jury_weighted_ranking()` method to apply reliability weights
  - Computes weighted generator ranking: `weighted_score = sum(score * reliability) / sum(reliabilities)`
  - Stores result in `state.jury_weighted_ranking` (list of generator IDs, best→worst)
  - Renderer displays weighted ranking alongside critic reliability scores
  - Fixes previous issue where biased critics had same weight as reliable ones

#### A4. Socratic: Dual-Role Split (Questioner ≠ Answerer)
- **Status**: ✅ Implemented
- **Files changed**: `pipeline.py`
- **Changes**:
  - Changed `_phase_socratic_question()` to use role="destructive" (challenges & probes)
  - Changed `_phase_socratic_answer()` to use role="constructive" (builds & defends)
  - Two distinct LLM instances now genuinely challenge each other
  - Restores original Socratic principle: separate questioner and answerer personas

#### A5. Debate: Cross-Examination Round
- **Status**: ✅ Implemented
- **Files changed**: `pipeline.py`, `phases.py`
- **Changes**:
  - New phase `_phase_debate_cross_examine()` inserted between rebuttal and judge
  - Added prompts: `DEBATE_CROSS_SYSTEM` + `debate_cross_examine_prompt()`
  - Both sides directly challenge opponent's specific claims with evidence
  - Judge sees full debate transcript including cross-examination before verdict
  - Increases factual precision and claim-by-claim contestation

### Track B — 6 New Reasoning Methods

#### B1. Pre-Mortem Analysis
- **Status**: ✅ Implemented
- **Scientific basis**: Gary Klein (1989) — prospective hindsight increases risk identification ~30%
- **Files changed**: `pipeline.py`, `phases.py`, `models.py`, `presets.py`, `renderer.py`, `ui/js/config.js`, `ui/index.html`
- **Architecture**:
  ```
  Phase 0: Classification (shared)
  Phase 1: Failure Narrative — "It is 1 year later. Solution catastrophically failed. Write post-mortem."
  Phase 2: Root Cause Backtrack — "Which single decision was the pivot point?"
  Phase 3: Early Warning Signals — "What observable signals appeared in first 30 days?"
  Phase 4: Hardened Redesign — reconstruct solution addressing each failure mode
  Phase 5: Synthesis (shared)
  ```
- **State field**: `pre_mortem_state: dict` with keys: `failure_narratives`, `root_causes`, `early_signals`, `hardened_solution`
- **Presets**: `pre-mortem-budget`, `pre-mortem-premium`
- **Routing keys**: Uses existing `primary`, `constructive`, `synthesis` (no new keys)
- **UI**: Dropdown option + method-specific guidance + phase definitions
- **Estimated lines**: ~280

#### B2. Bayesian Reasoning
- **Status**: ✅ Implemented
- **Scientific basis**: Bayesian epistemology (Jaynes 2003). Used in clinical trials, intelligence analysis (CIA ACH), ML model selection
- **Files changed**: `pipeline.py`, `phases.py`, `models.py`, `presets.py`, `renderer.py`, `ui/js/config.js`, `ui/index.html`
- **Architecture**:
  ```
  Phase 0: Classification (shared)
  Phase 1: Prior Elicitation — estimate prior P(H) for each hypothesis with reasoning
  Phase 2: Likelihood Assessment — for each observation, estimate P(E|H) vs P(E|¬H)
  Phase 3: Posterior Update — compute P(H|E) via Bayes rule; express updated belief distribution
  Phase 4: Sensitivity Analysis — which prior assumption most changes the posterior if wrong?
  Phase 5: Synthesis (shared)
  ```
- **State field**: `bayesian_state: dict` with keys: `hypotheses_with_priors`, `evidence_likelihoods`, `posteriors`, `sensitivity_results`
- **Presets**: `bayesian-budget`, `bayesian-premium`
- **Routing keys**: Uses existing `primary` (no new keys)
- **UI**: Dropdown option + method-specific guidance + phase definitions
- **Renderer**: Prior distribution table → evidence matrix → posterior bars → sensitivity tornado chart
- **Estimated lines**: ~320

#### B3. Dialectical Reasoning (Hegelian Aufhebung)
- **Status**: ✅ Implemented
- **Scientific basis**: Hegel's dialectic — thesis/antithesis/Aufhebung. Synthesis is qualitative transcendence, not compromise
- **Files changed**: `pipeline.py`, `phases.py`, `models.py`, `presets.py`, `renderer.py`, `ui/js/config.js`, `ui/index.html`
- **Architecture**:
  ```
  Phase 0: Classification (shared)
  Phase 1: Thesis — strongest affirmative position with key commitments
  Phase 2: Antithesis — internal contradictions of thesis exposed; negation of its commitments
  Phase 3: Contradiction Analysis — which contradictions are irreconcilable vs. compatible?
  Phase 4: Aufhebung — qualitatively higher position that preserves truth from both sides
  Phase 5: Synthesis (shared)
  ```
- **Roles**: `constructive` (thesis), `destructive` (antithesis) — already in routing
- **State field**: `dialectical_state: dict` with keys: `thesis`, `antithesis`, `contradictions`, `aufhebung`
- **Presets**: `dialectical-budget`, `dialectical-premium`
- **Routing keys**: Uses existing `constructive`, `destructive`, `synthesis` (no new keys)
- **UI**: Dropdown option + method-specific guidance + phase definitions
- **Renderer**: Thesis panel (green) ← → Antithesis panel (red), Contradiction table, Aufhebung panel (magenta)
- **Estimated lines**: ~300

### Implementation Summary

| Track | Item | Method | Status | Lines Added |
|-------|------|--------|--------|-------------|
| **A** | A1 | Scientific Bayesian Posterior | ✅ | ~40 |
| **A** | A2 | Iterative Convergence Exit | ✅ | ~20 |
| **A** | A3 | Jury Weighted Ranking | ✅ | ~35 |
| **A** | A4 | Socratic Dual Role | ✅ | ~5 |
| **A** | A5 | Debate Cross-Examination | ✅ | ~45 |
| **B** | B1 | Pre-Mortem Analysis | ✅ | ~280 |
| **B** | B2 | Bayesian Reasoning | ✅ | ~320 |
| **B** | B3 | Dialectical Reasoning | ✅ | ~300 |
| | **Total** | **Sprint 1+2** | ✅ | **~1,045 lines** |

**All new presets:** 6 (pre-mortem-budget/premium, bayesian-budget/premium, dialectical-budget/premium)
**All new state fields:** 3 (pre_mortem_state, bayesian_state, dialectical_state)
**Breaking changes:** 0 (all additive, existing methods unchanged)
**API changes:** 0 (CLI/API backward compatible)

### Files Modified (Sprint 1+2)
- `pipeline.py` — 5 Track A patches + 3 `_run_*_pipeline` methods + 12 phase methods (~600 lines)
- `phases.py` — Track A prompts + 12 new prompt functions (~320 lines)
- `models.py` — 3 state dict fields + `_from_dict` reconstruction (~50 lines)
- `presets.py` — 6 new presets + validation (~120 lines)
- `renderer.py` — 3 MethodType entries + 3 render functions (~450 lines)
- `ui/js/config.js` — 6 entries across 4 config objects (~100 lines)
- `ui/index.html` — 6 dropdown options (~42 lines)

### Verification Checklist
- ✅ All imports resolve cleanly (no syntax errors)
- ✅ All 6 new presets load in `--list-presets`
- ✅ MethodType enum includes all 3 new methods
- ✅ State fields exist on PipelineState with `field(default_factory=dict)`
- ✅ Renderer dispatch routes all 3 methods to correct `_render_*()` functions
- ✅ UI config and HTML dropdowns include all 3 methods
- ✅ API server starts without errors on port 8000
- ✅ No breaking changes to existing 7 methods

### Next: Sprint 3 Planning
Sprint 3 will implement B4 Analogical Reasoning + B5 Delphi Method:
- B4 requires ~340 lines
- B5 requires ~420 lines and 4 new routing keys: `expert_1`, `expert_2`, `expert_3`, `expert_4`
- Total: ~760 lines, new routing validation needed

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