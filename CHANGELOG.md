# Changelog

All notable changes to the Reasoner (ARA Pipeline) project.

## [Unreleased] — Phase 6 (E2E Tests & Benchmarks)

### Added
- E2E pipeline tests: radiology, legal, aerospace verticals with mocked LLM/NLI.
- Global invariant tests: LLM call counter, taint propagation, zero magic numbers.
- Benchmark suite: latency overhead, diversity ratio, calibration Pearson correlation.
- Reproduce scripts fixed to use real codebase and pass (client URL, search yield, HyperGate regex, URL norm).
- Documentation: `docs/VS.md` (architecture & integration points), `docs/ENVIRONMENT.md` (env var reference).

---

## Phase 5 (Scale Prep & Polish)

### Added
- IndexedDB cursor-based pagination (`loadConversationsPage`) with 50-item pages to prevent UI freeze on large conversation histories.
- Widget API client-side caching (`withWidgetCache`) with 30-second TTL for weather, stocks, and calculator endpoints.
- `DB_POOL_SIZE` environment variable (default: 10) for `asyncpg` connection pool sizing.
- `requirements.lock` generated via `uv pip compile` for reproducible dependency installs.

### Changed
- Event bus queue already bounded at 1000 with `QueueFull` backpressure handling (verified in Phase 2).
- All TODO comments now reference issue numbers (`TODO(#501)`, `TODO(#502)`).

### Fixed
- No orphaned TODO comments or large commented-out code blocks.

---

## Phase 4 — VS Integration

### Added
- **Track 5A**: VS Probe Generation (`vs_probe_generation.py`), Decomposition (`vs_decomposition.py`), Coverage Audit (`vs_coverage_audit.py`).
- **Track 5B**: VS Generation Stage (`vs_generation.py`) with 3 strategies (BEST_VERIFIABLE, ENSEMBLE, TOP_PROBABILITY) and 3-level LLM fallback.
- **Track 5C**: Calibration (`vs_calibration.py`), Claim Extraction (`vs_claim_extraction.py`), Verification Routing (`vs_verification_routing.py`), Conflict Surfacing (`vs_conflict_surfacing.py`), Behavioral Audit (`vs_behavioral_audit.py`).
- **Track 5D**: Vertical domain configs for Radiology, Legal, and Aerospace with auto-registration.
- `LOG_VS_MODE_COLLAPSE` constant for observability alerts.
- `compute_verbalized_entropy` primitive in `ara_verbalized_sampling.py`.

---

## Phase 3 — VS Foundation

### Added
- `ara_vs_constants.py` — frozen single source of truth for all Verbalized Sampling numeric constants.
- `ara_verbalized_sampling.py` — VS primitives: `VSMode`, `VSCandidate`, `VSResult`, prompt building, JSON parsing, probability-weighted sampling.
- `vs_config.py` — `VSFeatureFlags`, `VSVerticalConfig`, `VSVerticalRegistry`.

---

## Phase 2 — Performance & Security

### Added
- Streaming sentence-based chunking, fire-and-forget WebSocket broadcasts.
- BM25 Counter optimization, filter-before-slice, deterministic article router.
- Shared `httpx.AsyncClient`, OrderedDict LRU auth keys, lock sharding.
- Rate limiter fail-closed, WebSocket auth, CSRF protection, router degradation, quota fallback.
- Port migration 8001 → 8003 (Windows zombie socket workaround).

### Fixed
- `DegradedLLMResponse` unpacking bug in `router.py`.
- Frontend build errors (lucide-react `Github` removal, stale auth callback file).
