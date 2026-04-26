# Reasoner — Master Implementation TODO

> **Merged from:**
> - `Reasoner SaaS Launch — Architectural Implementation Plan` (v1.0, 2026-04-18)
> - `ARA × Verbalized Sampling Integration Plan` (2026-04-26)
> - `Backend Security & Reliability Audit` (2026-04-25)
> - `Performance & Search Quality Plan` (2026-04-19)
>
> **Deduplication log:** Rate limiter fail-closed (×3 → ×1), `_broadcast_ws` fix (×2 → ×1),
> `asyncio.sleep(0.1)` removal (×2 → ×1), datetime UTC fixes consolidated (A.1+C.13+D.2 → T0.6).
>
> **Global invariants (apply to ALL tasks):**
> - Pydantic BaseModel σε κάθε inter-stage interface
> - TaintRecord propagation σε κάθε pipeline output
> - NLI-before-LLM — ποτέ LLM σε ranking loop
> - Named constants — zero magic numbers
> - `asyncio.gather` για independent operations
> - pytest ≥ 85% coverage ανά νέο module
> - Feature flags για κάθε VS integration point
> - Clean Architecture: domain layer έχει zero infrastructure imports

---

## Σύμβολα

| | |
|---|---|
| `[ ]` | Εκκρεμεί |
| `[~]` | Draft/partial — χρειάζεται ολοκλήρωση |
| `[x]` | Done |
| `[!]` | Blocker |
| `[?]` | Απαιτεί απόφαση |
| `[P0]` | Critical — blocks release |
| `[P1]` | High — current sprint |
| `[P2]` | Medium — next sprint |
| `[P3]` | Low — backlog |

---

## Execution Map

```
Week 1   │ TRACK 0 — System Stability ────────────────────── ALL HANDS ──┐
         │ TRACK 1A — Security P0 (Phase A) ──────────────── parallel ───┤
         │                                                                │
Week 2   │ TRACK 1B — Security P1 (Phase B) ──────────────── parallel ───┤
         │ TRACK 2  — SaaS Domain + Ports ────────────────── parallel ───┤
         │ TRACK 3  — VS Decisions + Primitives ──────────── parallel ───┤
         │ TRACK 4  — Quick Wins (perf/search) ───────────── parallel ───┤
         │                                                                │
Week 3   │ TRACK 1C — Security P2 (Phase C) ──────────────── parallel ───┤
         │ TRACK 2  — SaaS Auth (Phase 2) ────────────────── parallel ───┤
         │                                                                │
Week 4   │ TRACK 1D — Security P3 (Phase D) ──────────────── parallel ───┤
         │ TRACK 2  — SaaS Quotas (Phase 3) ──────────────── parallel ───┤
         │ TRACK 5A — VS Probe / Decomp / Coverage ───────── parallel ───┤
         │                                                                │
Week 5   │ TRACK 2  — SaaS Billing (Phase 4) ─────────────── parallel ───┤
         │ TRACK 5B — VS Generation ──── CRITICAL PATH ──────────────────┤
         │                                                                │
Week 6   │ TRACK 5C — VS Calibration/Claims/Routing/Conflict/Obs ────────┤
         │ TRACK 5D — VS Vertical Configs ─────────────────── parallel ──┤
         │                                                                │
Week 7   │ TRACK 6  — Docker + Security Hardening + Monitoring ──────────┤
         │                                                                │
Week 8   │ TRACK 7  — Frontend Self-Service UI ──────────────────────────┤
         │                                                                │
Week 9   │ TRACK 8  — Scale Prep (memory/concurrency) ───────────────────┤
         │ TRACK 9  — E2E Integration Tests ──────────────────────────────┤
         │                                                                │
Week 10  │ TRACK 10 — Benchmarks, Buffer, Documentation ─────────────────┘
```

**Hard cross-track dependencies:**
- `TRACK 1A` (SSRF, AuthZ) → must finish before VS LLM calls go to production
- `TRACK 2 Phase 2` (Auth) → required by `TRACK 5B` (VS Generation quota awareness)
- `TRACK 6` (Redis in Docker) → required by `TRACK 5C` VS BehavioralAudit rolling window
- `TRACK 3` (VS constants) → blocks all of `TRACK 5`

---

## TRACK 0 — System Stability (Week 1, All Hands)

> **Source:** SaaS §12 Reliability + Performance Plan §0
> **Risk:** Zero. Config, imports, test hygiene. Must finish Day 1-2.

### T0.1 Purge stale `__pycache__` and bytecode
- [x] Delete `tests/__pycache__/` and all `*.pyc` artifacts
- [ ] **AC:** `pytest --collect-only` shows 0 collection errors

### T0.2 Fix `pytest.ini` / `conftest.py`
- [~] Add `addopts = --durations=10` to `pytest.ini`
- [ ] Add `asyncio_mode = auto` + `asyncio_default_fixture_loop_scope = session`
- [~] Move `os.environ["CSRF_ENFORCE_BACKEND"]` into session-scoped autouse fixture with teardown
- [ ] Remove module-level `tempfile.tempdir` — rely on `writable_temp_dirs` fixture
- [ ] **AC:** No `DeprecationWarning` from `pytest-asyncio`; temp dirs under `.tmp_pytest/`

### T0.3 Update `requirements.txt`
- [ ] `stripe`: `<13.0.0` → `<16.0.0` | `redis`: `<6.0.0` → `<8.0.0` | `pypdf`: `<6.0.0` → `<7.0.0`
- [~] Remove `newspaper3k` (zero imports in `src/`)
- [ ] Move `gunicorn` from `# Testing` → `# Production WSGI`
- [ ] **AC:** `pip install -r requirements.txt` completes without conflicts

### T0.4 Complete `PyPDF2` → `pypdf` migration
- **File:** `src/reasoner/` (all `PyPDF2` imports)
- [x] Replace `import PyPDF2` → `from pypdf import PdfReader`
- [ ] Update `.getPage(n)` → `.pages[n]`, `PdfFileReader` → `PdfReader`
- [ ] **AC:** `python -c "import reasoner"` shows no `DeprecationWarning`

### T0.5 Fix asyncpg crash + lazy-load PostgreSQL
- [x] Verify `postgres_store.py:23` uses `asyncpg.PostgresError` (not `Exception`)
- [x] Convert `infrastructure/persistence/__init__.py` to `__getattr__` lazy imports
- [ ] **AC:** Backend starts without asyncpg installed (asyncpg features gracefully absent)

### T0.6 [CONSOLIDATED] Fix all naive datetime usage
> *Merges: SaaS Security A.1 (auth.py), C.13 (models.py), D.2 (healing modules)*
- **Files:** `auth.py:140,149,196,220,232,237` · `auth_store.py:100,136` · `models.py:758` · `healing/introspection_engine.py` · `healing/test_generation_engine.py`
- [~] `from datetime import timezone` at top of each file
- [~] Replace `datetime.now()` → `datetime.now(timezone.utc)` in all affected files
- [ ] On read from store, if naive → `.replace(tzinfo=timezone.utc)` coercion
- [ ] **AC:** `test_auth_key_expiration_dst.py` passes; `test_resume_naive_datetime.py` passes

### T0.7 Unify port to 8001 + startup smoke test
- **Files:** `start_all.py`, `core/constants.py`, `README.md`
- [x] Add `DEFAULT_API_PORT = 8001` to `constants.py`
- [ ] `start_all.py`: smoke test `python -c "from reasoner.api import app"` before uvicorn
- [ ] `start_all.py`: port-in-use check → print occupying PID, exit 1
- [ ] `start_all.py`: replace `time.sleep(1)` with poll loop hitting `http://127.0.0.1:8001/`
- [ ] Update README quickstart from port 8000 → 8001
- [ ] **AC:** 4-step verification from SaaS §12 all pass

### T0.8 Fix proxy error codes + frontend dev errors
- **Files:** `ui-next/src/app/api/run/route.ts`, `run-followup/route.ts`, `hooks/usePipelineStream.ts`
- [x] Return `504` (not `400`) for connection errors; log `upstream_url`
- [ ] Show `"Backend unreachable (port 8001). Run: uvicorn asgi:app --port 8001"` on 504 (dev only)
- [ ] **AC:** Kill backend mid-request → frontend shows actionable message

### T0.9 Document environment variables
- [x] Create `docs/ENVIRONMENT.md`: `API_BASE_URL`, `NEXT_PUBLIC_API_BASE_URL`, `PORT` + defaults
- [ ] Add `SECURITY_SERVER_HASH` to `security-server.ts` for Turbopack cache invalidation

### T0.10 Fix `is_retryable()` for OpenAI errors
- **File:** `src/reasoner/exceptions.py`
- [x] Handle `status_code` attribute (OpenAI SDK) as retryable
- [ ] Handle `"fetch failed"` message as retryable

---

## TRACK 1A — Security P0: Critical Fixes (Week 1, Days 1–3)

> **Source:** SaaS Security Audit Phase A
> **[P0] — Block Release.** DO NOT reorder within this track.

### 1A.1 SSRF protection
- **Files:** `src/reasoner/security/url_validator.py` (new), `scraper.py:144-200`, `image_generation.py:224-247`
- [ ] Create `_is_safe_url(url: str) -> bool`: blocklist `127.x`, `10.x`, `172.16-31.x`, `192.168.x`, `169.254.169.254`, `::1`, `fc00::/7`, `localhost`
- [ ] Resolve hostname to IP before request; block if resolved IP in blocklist
- [ ] Restrict to `http://` and `https://` only
- [ ] Apply in `scrape_url()` and `_download_image_url()`
- [ ] **AC:** `test_ssrf_protection.py` — `http://169.254.169.254/latest/meta-data/` → 403

### 1A.2 Pipeline authorization (ownership checks)
- **File:** `src/reasoner/api/routes/pipelines.py:20-192`
- [x] Add `user_id` column to pipeline state/history records
- [x] Assert `record.user_id == user.id` in every endpoint (GET, DELETE, POST resume)
- [x] Return `HTTPException(403)` on mismatch
- [x] Filter `GET /api/pipelines` by `user_id`
- [ ] **AC:** `test_pipeline_authz.py` — User B delete User A's pipeline → 403

### 1A.3 Integrate Event Store into hot path
- **Files:** `streaming.py:318-708`, `application/handlers/handlers.py`
- [x] `PipelineStarted` event persisted at pipeline start
- [x] `PhaseCompleted` / `PhaseFailed` at each phase boundary
- [x] `PipelineCompleted` with final state snapshot
- [ ] **AC:** Event store populated after pipeline run; replay recovers state

### 1A.4 Circuit Breaker wiring
- [x] Wire existing circuit breaker to LLM providers (primary + fallback)
- [ ] `Phase A.5` complete before `1B.6` (provider router fallback)
- [ ] **AC:** Breaker opens after threshold failures; resets after cooldown

---

## TRACK 1B — Security P1: High Priority (Week 2, Days 4–7)

> **Source:** SaaS Security Audit Phase B

### 1B.1 Monotonic clock migration (TTL stability)
> *Dependency: T0.6 (datetime fixes) must be done first*
- **Files:** `neuro/cache.py`, `neuro/sessions.py`, `neuro/providers.py`, `core/search.py`, `api/csrf.py`
- [~] Replace `time.time()` with `time.monotonic()` for TTL/gap detection/cooldown/cache TTL
- [ ] Keep wall-clock for absolute expiry (document this distinction)
- [ ] **AC:** `test_monotonic_ttl_stability.py` — clock jumps don't affect TTL behavior

### 1B.2 Idempotency gates
- **Files:** `api/__init__.py:377-403`, `streaming.py:318-325`, `feedback_store.py:104-127`, `webhooks.py:54-74`
- [ ] `/api/run`: Redis `run_id → (status, started_at)` with 5-min TTL; duplicate → 409 or stream existing
- [x] `/api/feedback`: `UNIQUE(conversation_id, message_id)` in SQLite; handle `IntegrityError` as 200
- [x] Stripe webhooks: two-phase key `{event_id}:processing` → `{event_id}:completed`
- [ ] **AC:** `test_idempotency_gates.py` — duplicate run, feedback, webhook all idempotent

### 1B.3 Harden delivery semantics
- **Files:** `event_bus/bus.py:85-129`, `websocket/manager.py:102-365`, `streaming.py:774-799`
- [~] Event Bus: `asyncio.Queue(maxsize=1000)` + 3-retry exponential backoff + dead-letter table `failed_events`
- [~] WebSocket: per-pipeline ring buffer (last 50 events); replay on reconnect
- [~] SSE: `Last-Event-ID` parsing; per-run event sequence log for resume
- [ ] **AC:** `test_delivery_semantics.py` — kill handler mid-event → retry + DLQ; WS disconnect → replay

### 1B.4 Fix Stripe webhook dedup & subscription race
- [x] Two-phase dedup from 1B.2 applied to webhook handlers
- [ ] `sync_quota_for_subscription`: `SELECT ... FOR UPDATE` in transaction
- [ ] **AC:** `test_stripe_webhook_race.py` — 2 concurrent webhooks → exactly 1 quota update

### 1B.5 Fix SQLite event store `INSERT OR REPLACE`
- **File:** `infrastructure/persistence/event_store.py:136-195`
- [ ] `INSERT OR REPLACE` → `INSERT ... ON CONFLICT(event_id) DO NOTHING`
- [ ] `_update_aggregate` still runs on conflict (idempotent upsert)
- [ ] **AC:** Same `event_id` twice → original row untouched

### 1B.6 Provider Router graceful degradation
> *Dependency: 1A.4 (circuit breaker) must be done first*
- **File:** `infrastructure/llm/router.py:58-150`
- [ ] Both primary + fallback fail → `DegradedLLMResponse(degraded=True)` instead of raising
- [ ] Pipeline detects `degraded=True` → emit `phase_warning`, continue to next phase
- [ ] **AC:** `test_provider_router_total_failure.py` — all providers blocked → partial result, not 500

### 1B.7 Redis quota cache fallback
- **File:** `infrastructure/persistence/cached_quota_repo.py`
- [ ] Wrap `redis.get/set` in `try/except ConnectionError, TimeoutError`
- [ ] On failure → bypass cache, hit Postgres directly; log WARNING
- [ ] **AC:** `test_quota_redis_fallback.py` — Redis stopped → quota check via Postgres

### 1B.8 Authenticate WebSocket connections
- **Files:** `api/routes/websocket.py:15-51`, `infrastructure/websocket/manager.py`
- [ ] Parse `Authorization` header or query param during `websocket.accept()`
- [ ] Reject with 403 if invalid; attach `user_id` to connection metadata
- [ ] On `subscribe(pipeline_id)`, verify ownership
- [ ] **AC:** `test_websocket_auth.py` — unauth → 403; User B on User A's pipeline → 403

### 1B.9 Harden admin endpoint
- **File:** `api/__init__.py:750-773`
- [x] Require valid JWT with `admin` scope AND `X-Admin-Key`
- [ ] `ADMIN_API_KEY` unset → 503 (not 401)
- [ ] Log every access attempt to audit table
- [ ] **AC:** `test_admin_dual_auth.py` — valid key but no JWT scope → 403

### 1B.10 Fix upload memory exhaustion
- **Files:** `api/routes/uploads.py:18-57`, `uploader.py:245`
- [x] Enforce size limit at Starlette layer with chunked read (1MB chunks)
- [ ] Reject with 413 **before** buffering entire file
- [ ] **AC:** `test_upload_streaming_reject.py` — 100MB upload → 413 within 1s

### 1B.11 JSON depth limits
- **File:** `src/reasoner/utils/json_safe.py` (new)
- [ ] `safe_json_loads(data, max_depth=100) -> Any` — iterative or decoder patch
- [ ] Replace all `json.loads` on untrusted input in: `api/cache.py`, `event_store.py`, `websocket/manager.py`, `neuro/server.py`, `api/routes/history.py`
- [ ] **AC:** `test_json_depth_limit.py` — 200 nested → `ValueError`; 50 nested → OK

### 1B.12 Fix logging secret leakage
- **Files:** `logging_utils.py`, `api/__init__.py`, `streaming.py`, `scraper.py`, `core/search.py`
- [x] Create `SafeLoggingFilter` that redacts URLs with `?key=...` patterns
- [ ] Register globally at app startup
- [ ] Call `sanitize_for_logging` before any `logger.error` with external error strings
- [ ] **AC:** `test_logging_redaction.py` — `?key=sk-live-xxx` in logs → `***REDACTED***`

---

## TRACK 1C — Security P2: Medium Priority (Week 3, Days 8–12)

> **Source:** SaaS Security Audit Phase C

### 1C.1 `require_tier` enforcement
- **File:** `src/reasoner/api/dependencies.py:146-165`
- [x] Fetch subscription inside `checker()`
- [ ] Compare tier enum ordering; return 403 `"Tier upgrade required"` if insufficient
- [ ] **AC:** `test_tier_enforcement.py` — Free user hits Pro endpoint → 403

### 1C.2 Timing attack fix for API key validation
- **File:** `src/reasoner/auth.py:108-110,191-225`
- [x] Replace `hashlib.sha256 + dict lookup` with `secrets.compare_digest`
- [ ] **AC:** `test_auth_timing_attack.py` — 1000 valid vs invalid; timing variance < 5ms

### 1C.3 Auth error message normalization
- **File:** `src/reasoner/api/auth_deps.py:75-97`
- [x] Replace `detail=e.message` → generic `"Authentication failed"` for all `AuthenticationError`
- [ ] Log specific error internally only
- [ ] **AC:** Expired vs invalid key → identical response body

### 1C.4 Upload content-hash deduplication
- **File:** `src/reasoner/uploader.py:223-361`
- [ ] `sha256(content).hexdigest()` before saving; lookup existing; return existing `file_id`
- [ ] **AC:** Same file uploaded twice → identical `file_id`

### 1C.5 Harden `/keys/status` endpoint
- **File:** `src/reasoner/api/routes/keys.py:29-66`
- [x] Require `admin` scope; remove `key_length`; return only `is_set: bool` + `provider_name`
- [ ] **AC:** Non-admin → 403

### 1C.6 Calculator widget CPU sandbox
- **File:** `src/reasoner/widgets.py:70-124`
- [x] Max AST depth 100 → 20; char limit 10K; wrap in `asyncio.wait_for(timeout=1.0)`
- [ ] **AC:** Deep nested pow → graceful 400 (not hang)

### 1C.7 Validate URLs in `ContextAnalysisRequest.context`
- [x] Iterate context values; if URL-like → pass through `_is_safe_url()` (from 1A.1)
- [ ] Reject unsafe with 403 before pipeline injection
- [ ] **AC:** `http://169.254.169.254/` in context → 403

### 1C.8 Fix traceback leakage in logs
- **Files:** `api/routes/context.py:104-106`, `streaming.py:561`
- [ ] Replace `traceback.format_exc()` with `logger.exception(msg, exc_info=False)` + `exc_type` only
- [ ] Full tracebacks only behind `DEBUG=true`
- [ ] **AC:** `test_log_no_locals.py` — local secret absent from captured logs

### 1C.9 Cap token cache entry count
- **File:** `src/reasoner/token_cache.py:80-88,197-242`
- [ ] Add `max_entries=1000`; LRU eviction by count **in addition to** token budget
- [ ] **AC:** 1001 entries → oldest evicted

### 1C.10 [DEDUPLICATED] Rate limiter fail-closed
> *Previously: SaaS §12 "fix proxy error codes", C.10, Performance Plan 3.1 — all same fix.*
- **File:** `src/reasoner/api/auth_deps.py:50-56`
- [ ] Catch `RateLimitError` → `allowed=False`
- [ ] Catch `Exception` → log + `HTTPException(503, "Rate limiting unavailable")`
- [ ] **[?] Decision needed:** fail-open vs fail-closed — document in ADR before implementing
- [ ] **AC:** Mock `is_allowed` raises `RuntimeError` → 503, not 200

### 1C.11 Remove hardcoded default DB password
- **File:** `src/reasoner/core/settings.py:119`
- [x] Default `DATABASE_URL` → `""` (not `postgres:postgres@...`)
- [ ] Postgres features enabled + empty URL → `RuntimeError` at startup with message
- [ ] **AC:** Unset env → actionable startup failure

### 1C.12 Pin dependency versions + lockfile
- [~] Add upper bounds: `pypdf>=4,<5`, `gunicorn>=22,<24`
- [ ] `uv pip compile requirements.txt -o requirements.lock`
- [ ] CI installs from lockfile

### 1C.13 Add `pip-audit` + `npm audit` to CI
- [x] `pip-audit` on backend; `npm audit` on frontend
- [ ] **AC:** Zero high-severity vulnerabilities at merge

---

## TRACK 1D — Security P3: Cleanup (Week 4, Days 13–16)

> **Source:** SaaS Security Audit Phase D

### 1D.1 Latency measurements → `time.perf_counter()`
- **Files:** `infrastructure/llm/ports.py:289,296`, `neuro/server.py:217-297`, `infrastructure/widgets/protocol.py:204-217`
- [ ] Replace `time.time()` → `time.perf_counter()` for latency measurements
- [ ] **AC:** `test_perf_counter_usage.py` — assert no `time.time()` in latency paths

### 1D.2 Miscellaneous cleanup
- [ ] Remove all commented-out code blocks > 10 lines
- [ ] Ensure all `TODO` comments have linked issue numbers
- [ ] Update `CHANGELOG.md` with all Phase A-C changes

---

## TRACK 2 — SaaS Infrastructure (Weeks 2–5)

> **Source:** SaaS Launch Plan Phases 1–4
> Sequential within this track.

### 2.1 Domain Model + Postgres Schema (Week 2)

- [x] Create `src/reasoner/domain/saas.py`: `User`, `Subscription`, `UsageQuota`, `QueryAuditLog`, `QuotaResult`, `SubscriptionTier`, `SubscriptionStatus`
- [x] Create ports: `application/ports/{auth_port,billing_port,quota_repository}.py`
- [x] Create services: `application/services/{auth_service,quota_service,billing_service,audit_service}.py`
- [x] Alembic migration: `user_profiles`, `subscriptions`, `usage_quotas`, `query_log` tables with indexes
- [x] Add `required_tier: SubscriptionTier = FREE` to `PipelinePreset`; tag `*-premium` as `PRO`
- [ ] **AC:** `pytest tests/test_saas_domain.py` passes; migration applies cleanly; zero regression

### 2.2 Auth Integration: Supabase + FastAPI (Week 3)

- [x] `infrastructure/auth/supabase_adapter.py`: validates JWT via Supabase `auth.get_user(token)`; caches in Redis (TTL = expiry - 60s)
- [x] `infrastructure/auth/local_adapter.py`: HS256 JWT with `SECRET_KEY` for dev/tests
- [x] `api/dependencies.py`: `get_current_user()`, `require_tier(min_tier)` FastAPI dependencies
- [x] Modify `api/__init__.py`: add `user: User = Depends(get_current_user)` to `/api/run`, `/api/run-followup`, `/api/history/*`
- [x] Keep legacy API-key behind `ENABLE_LEGACY_API_KEY=true`
- [x] Add `/api/auth/me` — returns user + subscription + quota
- [x] Create `api/saas_router.py` for all SaaS routes
- [ ] **AC:** No token → 401; valid Supabase JWT → 200, `user_id` in `query_log`; legacy key works

### 2.3 Quota Enforcement (Week 4)

- [x] `infrastructure/persistence/quota_repo_postgres.py`: atomic `check_and_increment` via `SELECT ... FOR UPDATE`
- [x] Redis cache-aside: `GET quota:{user_id}` TTL 60s; write-through invalidates Redis
- [x] Extend `RateLimiter`: optional `user_id` bucket key (`user:{user_id}` vs IP)
- [x] Update `/api/run` flow: auth → rate_limit → quota_check → tier_check → run → audit (fire-and-forget) → quota_increment
- [x] Add `/api/quota` endpoint: `{used, max, remaining, reset_date}`
- [ ] **AC:** Free user 21st query → 429 with `upgrade_url`; Enterprise → never blocked

### 2.4 Stripe Billing (Weeks 4–5)

- [x] `infrastructure/billing/stripe_adapter.py`: wraps `stripe-python` with idempotency keys
- [x] `api/billing_router.py`: `POST /checkout`, `POST /portal`, `GET /subscription`, `GET /invoices`
- [x] `infrastructure/billing/webhooks.py`: `POST /api/billing/webhook` — verify `stripe-signature`
- [ ] Handled webhook events: `checkout.session.completed`, `subscription.updated`, `subscription.deleted`, `invoice.payment_failed`, `invoice.payment_succeeded`
- [x] Allow `promotion_codes=True` in checkout
- [ ] **AC:** Upgrade → tier changes <5s; webhook replay → no duplicate rows

---

## TRACK 3 — VS Foundation (Weeks 2–3)

> **Source:** VS TODO Phases 0–1
> *Can run parallel to Tracks 1B and 2*

### 3.0 [!] Phase 0 Decisions (Week 2, Day 1 — BLOCKER for all VS tracks)

- [ ] **[!] 3.0.1** k defaults per stage: Decomp=5, Gen=5, Probes=5, Coverage=3, Claims=5; Radiology Gen=7
- [ ] **[!] 3.0.2** `VSDeploymentProfile`: LATENCY_SENSITIVE (nli=1), BALANCED (nli=3), MAX_ACCURACY (nli=5)
- [ ] **[!] 3.0.3** `GenerationStrategy` default: `BEST_VERIFIABLE` for all regulated verticals
- [ ] **[?] 3.0.4** Benchmark VS on deployed OpenRouter model (20 queries direct vs VS); AC: VS ≥ 1.3× diversity
- [ ] **[?] 3.0.5** Tail thresholds: radiology=0.10, legal=0.08, aerospace=0.06; embedding model for distance filter
- [ ] **[!] 3.0.6** Verify `LLMClient` supports `system` + `user` separation; write adapter if not
- [ ] **[!] 3.0.7** Verify `NLIGate.score_entailment()` has async interface; write `asyncio.to_thread` wrapper if not
- [ ] **[!] 3.0.8** Extend `TaintRecord`: `vs_metadata: dict | None` field
- [ ] **[?] 3.0.9** JSON parse error strategy: confirm 2-retry + direct fallback

### 3.1 `ara_vs_constants.py` ← First file written

- [ ] Stage k defaults (`VS_K_*`)
- [ ] Tail thresholds per vertical (`VS_TAIL_THRESHOLD_*`)
- [ ] Routing thresholds (`VS_ROUTING_HIGH_PROB=0.70`, `VS_ROUTING_MEDIUM_PROB=0.30`)
- [ ] Calibration weights (sum=1.0): `W_ENTROPY=0.30`, `W_SUPPORT=0.25`, `W_NLI=0.35`, `W_RANK=0.10`
- [ ] Operational: `VS_PARSE_MAX_RETRIES=2`, `VS_CONSENSUS_MIN_SUPPORT=2`, `VS_PROBE_MIN_SEMANTIC_DISTANCE=0.15`
- [ ] Feature flags (all default `True`): `VS_*_ENABLED` for each integration point
- [ ] Structured log keys: `LOG_VS_ENTROPY`, `LOG_VS_STRATEGY`, `LOG_VS_CANDIDATE_RANK`, `LOG_VS_PROBE_DOMAIN`, `LOG_VS_PROBE_COUNT`, `LOG_VS_NLI_SCORES`, `LOG_VS_K`
- [ ] **AC:** `test_vs_constants.py` — weights sum=1.0; thresholds in (0,1); k≥2; all flags default True

### 3.2 `ara_verbalized_sampling.py`

- [~] `VSMode` enum: `STANDARD | TAIL | COT`
- [~] `VSCandidate` model: `text`, `probability`; validator: non-empty text
- [~] `VSResult` model: normalize probs; all-zero → uniform; len invariant
- [~] `build_vs_prompt()` → `tuple[str, str]`; no literals (constants only)
- [~] `parse_vs_response()` — strip fences, regex extract JSON; 7 test cases (see prior spec)
- [~] `sample_from_vs()` — probability-weighted; KL < 0.05 statistical test
- [~] `top_candidate()` — deterministic; tie → first
- [ ] **AC:** `test_vs_primitives.py` ~25 tests all pass

### 3.3 Config Models

- [ ] `VSDeploymentProfile` enum (from 3.0.2)
- [ ] `VSFeatureFlags` Pydantic model with `all_disabled()` factory
- [ ] `VSVerticalConfig` base model (domain, k, tail_threshold, strategy, probe_template, compliance flags)
- [ ] `VSVerticalRegistry` singleton: `register()`, `get()` with default fallback
- [ ] **AC:** `test_vs_config_models.py` ~10 tests

---

## TRACK 4 — Quick Wins: Performance + Search (Week 2, Parallel)

> **Source:** Performance Plan §1-2 + SaaS §13 Search Quality + Article Writing Plan

### 4.1 [DEDUPLICATED] Remove `asyncio.sleep(0.1)` + cancel check
> *Merges: Performance Plan 2.1 + SaaS Plan 7.4 — same file, same loop*
- **File:** `src/reasoner/api/streaming.py:636-647`
- [ ] Delete `await asyncio.sleep(0.1)` from synthesis word-chunking loop
- [ ] Add `if cancel_event and cancel_event.is_set(): break` inside loop
- [ ] **AC:** 500-word synthesis streams in <2s (was ~25s); abort stops stream immediately

### 4.2 [DEDUPLICATED] Fix `_broadcast_ws` — fire-and-forget + logging
> *Merges: Performance 2.3 + 2.4 — same function*
- **File:** `src/reasoner/api/streaming.py:87-98`
- [ ] Change `await manager.broadcast_event(...)` → `asyncio.create_task(...)`
- [ ] Replace bare `except: pass` with `logger.warning("WS broadcast failed", exc_info=True)`
- [ ] **AC:** WS slowdown no longer stalls SSE; exceptions logged not swallowed

### 4.3 BM25 scoring with `Counter`
- **File:** `src/reasoner/core/search.py:182-191`
- [ ] Pre-compute `Counter(title_tokens)` and `Counter(content_tokens)` before term loop
- [ ] **AC:** O(|Q|×|T|) → O(|Q|+|T|); search unit tests pass

### 4.4 Frontend quick wins
- **Files:** `PhaseRenderer.tsx`, `TypewriterMarkdown.tsx`, `page.tsx`, `CodeBlock.tsx`, `useServerStatus.ts`
- [ ] `useMemo` for `buildMarkdownFromPhase` in `PhaseRenderer.tsx`
- [ ] `TypewriterMarkdown`: plain `<span>` during animation, full `<MarkdownRenderer>` on completion
- [ ] Replace `[...messages].reverse().find(...)` with `findLastAssistant()` helper (no clone)
- [ ] Memoize `handleSubmit` and `handleStop` with `useCallback`
- [ ] Memoize `CodeBlock` style objects with `useMemo`
- [ ] Pause `useServerStatus` polling when `document.visibilityState === 'hidden'`
- [ ] Add `dedupingInterval: 2000` to `usePresets` SWR config
- [ ] **AC:** React DevTools shows no unnecessary re-renders for above components

### 4.5 React Error Boundary
- [ ] New `ui-next/src/components/chat/ChatErrorBoundary.tsx`
- [ ] Wrap `<ChatFeed />` and `<PhaseRenderer />` in boundary
- [ ] **AC:** Synthetic throw in `PhaseRenderer` → page stays alive, fallback UI shown

### 4.6 Search quality fixes
> **Source:** SaaS §13 Search Quality
- [ ] **[CRITICAL]** Fix search fallback bug: when all results fail `_should_include_result()`, return `[]` not unfiltered raw
- [x] Expand `_OFF_TOPIC_PATTERNS`: add `wordreference.com`, `facebook.com`, `biography.com`, `imdb.com`, `thetimes.com`, `reddit.com`
- [x] Add keyword extraction fallback for failed decomposition (regex `_extract_search_keywords()`)
- [ ] Skip disambiguation LLM call if `len(problem) < 120` and no ambiguous terms
- [x] Add in-memory TTL cache around `_decompose_query()` (`_DECOMPOSITION_CACHE`)
- [ ] Log decomposition failures with raw query visible
- [ ] Add telemetry: `"Search quality: X/Y results passed filtering (Z%)"`
- [ ] **AC:** `test_search_quality.py` — biography/dictionary rejection; empty fallback; regression tests pass

### 4.7 Article writing pipeline fixes
> **Source:** Article Writing Failure Remediation Plan
- [ ] Deterministic writing router: server-side detector for article/essay/blog/report/explainer prompts; bypass generic classification
- [ ] Safe follow-up scoping: only send context when referential signals present ("continue", "expand", "revise that")
- [ ] Context minimization: stop injecting raw multi-turn history into classification/decomp/perspective/synthesis
- [ ] `previous_synthesis` hygiene: only real final answer, not rendered phase output
- [x] Fix `_phase_article_retrieve`: correct `get_discovery_client()` unpacking; use shared search/ranking
- [ ] Strengthen source safety: block adult-content, forum-spam, low-signal UGC; topical relevance scoring
- [ ] Fail-closed writing quality gates: require minimum trustworthy sources; abort if claim-support ratio below threshold
- [ ] Observability: log routing/follow-up decisions (hashed IDs, no raw content)
- [ ] **AC:** Article request always enters writing workflow; non-referential new request doesn't inherit prior context; unsafe sources rejected

---

## TRACK 5A — VS Integration: Probes + Decomposition + Coverage (Week 4)

> **Source:** VS TODO Phases 2A, 2B, 2C
> **Dependency:** Track 3 complete. Parallel between 5A sub-tracks.
> All 3 sub-tracks can run in parallel.

### 5A-P (Probe Generation — IntentConsistencyStage)

- [ ] `DOMAIN_PROBE_TEMPLATES` dict: radiology, legal, aerospace, default (with `{k}`, `{query}` placeholders)
- [ ] `ProbeGenerationConfig` model; `ProbeSet` model (len invariant)
- [ ] `generate_probes_with_vs()`: TAIL VS → parse → identity filter → semantic distance filter → fallback to STANDARD if <2
- [ ] Integration in `IntentConsistencyStage` with feature flag gate
- [ ] **AC:** `test_vs_probe_generation.py` (8 tests) — templates, tail threshold, identity filter, fallback, taint, regression

### 5A-D (Decomposition — QueryDecompositionStage)

- [ ] `DecompositionVSConfig` model (validator: `top_n ≤ k`); `VSDecompositionResult` model
- [ ] `decompose_with_vs()`: STANDARD VS → sort by prob → top_n; retry `VS_PARSE_MAX_RETRIES`; final fallback to direct
- [ ] Integration with feature flag gate
- [ ] **AC:** `test_vs_decomposition.py` (6 tests) — sort, validation, retry, fallback, taint, flag

### 5A-C (Coverage Audit — CoverageAuditStage)

- [ ] `GapType` enum: `GENUINE | PHRASING_MISMATCH | COVERED`; `CoverageAuditResult` model
- [ ] `audit_claim_coverage_vs()`: VS paraphrases → overlap check → gap classification → taint severity
- [ ] Integration with feature flag gate
- [ ] **AC:** `test_vs_coverage_audit.py` (6 tests) — all 3 gap types, taint severity

---

## TRACK 5B — VS Generation Stage (Week 5 — CRITICAL PATH)

> **Dependency:** Track 5A complete + Track 3 complete.
> **All VS Tracks 5C–5D blocked until this is done.**

- [ ] `GenerationStrategy` enum: `BEST_VERIFIABLE | ENSEMBLE | TOP_PROBABILITY`
- [ ] `VSGenerationConfig` model (validator: `max_parallel_nli ≤ k`; profile integration)
- [ ] `GenerationCandidate` model; `VSGenerationResult` model (post-validator: exactly one `selected=True`)
- [ ] `generate_with_vs()` — `BEST_VERIFIABLE`: 1 LLM call → parse → pre-commit NLI budget → `asyncio.gather` NLI scoring → max NLI → select
- [ ] `generate_with_vs()` — `ENSEMBLE`: max probability selection
- [ ] `generate_with_vs()` — `TOP_PROBABILITY`: `candidates[0]`
- [ ] 3-level error fallback: L1 retry → L2 simplified prompt → L3 direct generation (with correct log levels)
- [ ] TaintRecord: `vs_metadata = {strategy, k, nli_scores, selected_rank}`
- [ ] Integration in `GenerationStage` with feature flag gate
- [ ] **AC:** `test_vs_generation_strategies.py` (10 tests) + `test_vs_generation_invariants.py` (4 tests — NLI ordering, pre-commit budget, LLM counter=1, race condition preservation)

---

## TRACK 5C — VS Post-Generation Integration (Week 6, Parallel)

> **Dependency:** Track 5B complete. All 5 sub-tracks run parallel.

### 5C-A (OutputCalibrationStage)
- [ ] `VSCalibrationSignals` model; `compute_verbalized_entropy()`; `compute_vs_calibrated_confidence()`; `extract_calibration_signals()`
- [ ] Integration with feature flag gate
- [ ] **AC:** `test_vs_calibration.py` (7 tests) — entropy known values, perfect/worst signals, unit interval, weights sum

### 5C-B (ClaimExtractionStage)
- [ ] `ClaimExtractionMode` enum: `SINGLE | UNION | CONSENSUS`; `VSClaimExtractionConfig`; `ExtractedClaimSet`
- [ ] `extract_claims_from_vs_candidates()`: parallel extraction, normalization, mode routing
- [ ] Integration: optional `VSGenerationResult`; absent → SINGLE (backward compat)
- [ ] **AC:** `test_vs_claim_extraction.py` (7 tests)

### 5C-C (TwoTierVerification Routing)
- [ ] `VerificationRoute` enum: `NLI_ONLY | NLI_THEN_LLM | CONSERVATIVE`
- [ ] `route_claim_by_vs_probability()` — pure function, 4-region routing logic from constants
- [ ] `CONSERVATIVE` → `UNKNOWN` + `human_review_flag=True` — never LLM
- [ ] **AC:** `test_vs_verification_routing.py` (6 tests) — truth table, no LLM in CONSERVATIVE, backward compat

### 5C-D (ConflictSurfacingStage — NEW MODULE)
> *Was entirely absent from original VS TODO*
- [ ] `CrossCandidateConflict` model: `claim`, `support_ratio`, `conflict_priority`, `recommendation`
- [ ] `surface_cross_candidate_conflicts()`: support ratio per claim → NLI contradiction (no extra LLM) → HUMAN_REVIEW/FLAG/MONITOR → sort by priority
- [ ] Integration with feature flag gate
- [ ] **AC:** `test_vs_conflict_surfacing.py` (6 tests) — all 3 recommendation types, sorted, zero LLM calls

### 5C-E (BehavioralAudit Observability)
> *Dependency: Redis must be available. Use `InMemoryVSEntropyStore` until Track 6 Docker setup.*
- [ ] Extend `BehavioralAuditStage`: fire-and-forget VS metrics logging using `LOG_VS_*` keys from constants
- [ ] `VSEntropyStore` abstract interface: `push(entropy)`, `get_mean()` → `RedisVSEntropyStore` + `InMemoryVSEntropyStore`
- [ ] Rolling window (N=100); alert on >30% entropy drop
- [ ] **AC:** `test_vs_observability.py` (5 tests) — log keys, non-blocking, rolling mean, alert, in-memory works

---

## TRACK 5D — VS Vertical Domain Configs (Week 6, Parallel with 5C)

> **Dependency:** Track 3.3 (VSVerticalConfig base) + Track 5A-P (DOMAIN_PROBE_TEMPLATES)

- [ ] `vs_vertical_configs/radiology_config.py`: k=7, tail=0.10, BEST_VERIFIABLE, `conservative_routing_enabled=True`
- [ ] `vs_vertical_configs/legal_config.py`: tail=0.08, `human_review_on_low_prob=True`
- [ ] `vs_vertical_configs/aerospace_config.py`: tail=0.06 (most aggressive), CMMC compliance flags
- [ ] `vs_vertical_configs/__init__.py`: auto-register all 3 on import
- [ ] **NEW — VS + SaaS tier integration:** Tag vertical configs with `min_subscription_tier` — radiology/aerospace = PRO, legal = PRO; enforce in `require_tier`
- [ ] **AC:** `test_vertical_configs.py` (6 tests); auto-register; tier enforcement for VS premium verticals

---

## TRACK 6 — Deployment & Observability (Week 7)

> **Source:** SaaS Phases 5, 6, 7
> *After Track 6, `RedisVSEntropyStore` can replace `InMemoryVSEntropyStore` in Track 5C-E*

### 6.1 Docker packaging
- [x] `Dockerfile` (backend): Python 3.12-slim, `uvicorn --workers 2`
- [x] `ui-next/Dockerfile`: node:22-alpine multi-stage build
- [x] `docker-compose.yml`: nginx + backend + frontend + postgres + redis + searxng
- [x] `nginx/nginx.conf`: reverse proxy, rate limit zone, security headers, `/api/` → backend, `/*` → frontend
- [x] Extend `/api/health` to report Postgres + Redis + Stripe connectivity
- [x] Docker `HEALTHCHECK` on backend
- [ ] **AC:** `docker compose up` → all services healthy <60s

### 6.2 Security hardening for production
- [x] Nginx HTTP→HTTPS redirect; HSTS in both nginx and `SecurityHeadersMiddleware`
- [x] `.env.example` updated with all new vars (Supabase, Stripe, Redis)
- [x] Replace hardcoded `localhost:3000` CORS origin with `APP_URL` from settings
- [x] Stripe webhook: verify `stripe-signature`; reject unsigned with 400
- [x] GDPR endpoints: `POST /api/account/delete` (hard delete cascade), `GET /api/account/export`
- [x] Audit logs: auth events → `auth_audit_log`; billing events → `billing_event_log`
- [ ] **AC:** Invalid Stripe signature → 400; delete removes all user data; `pip-audit` zero high-severity

### 6.3 Prometheus + Sentry + Structured logging
- [x] Prometheus `/api/metrics`: `REASONER_QUERIES_TOTAL[tier,preset,status]`, `REASONER_QUERY_DURATION[preset]`, `REASONER_ACTIVE_USERS`, `REASONER_QUOTA_EXCEEDED[tier]`, `REASONER_LLM_ERRORS[provider]`
- [~] **NEW — VS metrics in Prometheus:** `VS_DIVERSITY_ENTROPY`, `VS_MODE_COLLAPSE_ALERTS`, `VS_CANDIDATE_SELECTION_STRATEGY[strategy]`
- [x] Sentry: `sentry-sdk[fastapi]` backend + `@sentry/nextjs` frontend (production only)
- [x] Enrich `logging_utils.py` structured logs with `user_id`, `tier`, `preset` on every entry
- [x] Uptime Robot / Grafana OnCall: `/api/health` every 60s
- [ ] **AC:** Prometheus metrics > 0 after query; Sentry receives test exception <5s

---

## TRACK 7 — Frontend Self-Service UI (Week 8)

> **Source:** SaaS Phase 8

- [x] Auth pages: `/login` (Supabase Auth UI), `/signup` (email verification), `/forgot-password` (magic link)
- [x] Dashboard `/dashboard`: usage chart, plan card + upgrade CTA, recent queries, billing portal button
- [x] Pricing `/pricing`: 3-tier table (Free/Pro/Enterprise), Stripe Checkout for Pro, "Contact Sales" for Enterprise
- [x] Composer upgrades: lock icon on premium presets, usage badge `"14/20"` in header, upgrade modal on 429
- [x] Zustand: extend `AppState` with `user`, `subscription`, `quota`, `setUser`, `refreshQuota`
- [ ] **AC:** E2E: sign up → 20 queries → 429 → upgrade → Stripe → 21st query succeeds

---

## TRACK 8 — Scale Prep & Resource Management (Week 9)

> **Source:** SaaS Phase 9 + Performance Plan §4-5

### 8.1 Redis-backed global state (horizontal scaling)
- [x] `infrastructure/redis/run_state.py`: `RunStateManager` with `cancel(run_id)`, `is_cancelled(run_id)`, `register_active(run_id)`
- [ ] Move `_cancelled_runs`, `_active_runs` from module-level dict → Redis-backed
- [ ] **AC:** Two Uvicorn workers share cancel state correctly

### 8.2 Connection pooling for Neuro HTTP
- [ ] Module-level `_neuro_client: httpx.AsyncClient` in `api/clients.py`
- [ ] Initialize in `@asynccontextmanager` lifespan with `httpx.Limits(...)`
- [ ] Replace all `httpx.AsyncClient()` context managers with shared client
- [ ] **AC:** 10 pipeline runs → stable TCP connection count to Neuro endpoint

### 8.3 `AuthManager._keys` LRU eviction
- **File:** `src/reasoner/auth.py:89`
- [ ] `_keys`: `dict` → `OrderedDict`; `_MAX_KEYS = 10_000`; `_set_key()` evicts oldest at capacity
- [ ] **AC:** 10,001 keys → oldest evicted; memory bounded

### 8.4 IndexedDB pagination
- [ ] Replace `loadAllConversations()` with `loadConversationsPage(cursor?, direction?)` via IndexedDB cursors
- [ ] Update `useConversationHistory.ts`
- [ ] **AC:** 1,000 mock conversations → first page <100ms

### 8.5 Shard `RateLimiter` locks
- **File:** `src/reasoner/rate_limiter.py:116`
- [ ] Single `asyncio.Lock` → array of 64 shards; `_lock_for(key)` = `locks[hash(key) % 64]`
- [ ] Feature flag: `ENABLE_SHARDED_LOCKS=true` env var
- [ ] **AC:** Load test P99 latency improvement

### 8.6 Remove `PostgresEventStore` global lock
- **File:** `infrastructure/persistence/postgres_store.py:211`
- [ ] Remove `async with self._lock:`; rely on asyncpg pool + transaction isolation
- [ ] `INSERT ... ON CONFLICT (event_id) DO NOTHING` for idempotency
- [ ] **AC:** 50 concurrent event writes succeed without serialization

### 8.7 Shard `WebSocketManager` locks
- **File:** `infrastructure/websocket/manager.py:79`
- [ ] Per-connection locks or sharded by `connection_id`
- [ ] Broadcasts iterate snapshot copy (no read lock needed)
- [ ] **AC:** 1,000 simultaneous WS connect/disconnect without latency spikes

### 8.8 Bound `pipeline_owners` JSON growth
- **File:** `src/reasoner/api/history.py:25-34`
- [ ] Max 50,000 entries + LRU eviction (or shard by date prefix)
- [ ] **AC:** 60,000 runs → oldest evicted; file size bounded

### 8.9 `asyncpg` pool size config
- [ ] `DB_POOL_SIZE` env var (default 10)
- [ ] **AC:** Pool size respected; no connection exhaustion under load

### 8.10 Add `dedupingInterval` + client-side widget caching
- [ ] `usePresets`: `dedupingInterval: 2000` (rapid mount → 1 request)
- [ ] `api-client.ts`: in-memory TTL cache (30s) for `fetchWeather`, `fetchStocks`, `calculate`

---

## TRACK 9 — E2E Integration Tests (Week 9, Parallel with Track 8)

> **Source:** VS TODO Phase 6 + SaaS testing strategy

### 9.1 VS pipeline E2E tests

- [ ] `test_vs_pipeline_radiology.py`: 7 assertions (decomp angles, generation by NLI, CONSENSUS claims, conflict surfacing, calibration, TaintRecord, invariant checks)
- [ ] `test_vs_pipeline_legal.py`: legal probe templates, CONSERVATIVE routing, human_review_flag
- [ ] `test_vs_pipeline_aerospace.py`: failure mode probes (tail=0.06), human_review_flag
- [ ] `test_vs_all_flags_disabled.py` ← **GOLDEN REGRESSION TEST**: `VSFeatureFlags.all_disabled()` → output identical to pre-VS pipeline

### 9.2 Global invariant tests

- [ ] `test_vs_invariants_global.py`:
  - [ ] NLI before LLM at all integration points
  - [ ] LLM call counter = 1 per VS generation
  - [ ] TaintRecord.vs_metadata at every stage output
  - [ ] Zero magic numbers (grep VS files for numeric literals outside constants)

### 9.3 SaaS E2E tests

- [ ] All `reproduce_*.py` scripts pass
- [ ] `pytest -v` ≥ baseline pass count
- [ ] `cd ui-next && npm run build` — 0 errors
- [ ] `cd ui-next && npm run lint` — passes
- [ ] Synthesis latency for 500-word response <2s
- [ ] Rate limiter failure returns 503 (not 200) ← post T1C.10
- [ ] Prompt injection strings sanitized before LLM prompts ← post T4.7
- [ ] Auth key store bounds verified by unit test ← post T8.3
- [ ] Frontend Error Boundary catches synthetic throw ← post T4.5

---

## TRACK 10 — Benchmarks & Documentation Buffer (Week 10)

> **Source:** VS TODO Phase 7

### 10.1 Benchmarks

- [ ] `benchmark_vs_latency.py`: wall-clock per stage, VS vs baseline, per deployment profile → overhead table committed
- [ ] `benchmark_vs_diversity.py`: 50 queries × 3 verticals × (direct vs VS-Standard) → VS ≥ 1.3× for ≥ 2/3 verticals
- [ ] `benchmark_vs_calibration.py`: verbalized entropy vs model uncertainty correlation → Pearson r ≥ 0.6

### 10.2 Documentation

- [ ] Docstring με explicit trade-offs σε κάθε public function (VS + SaaS ports)
- [ ] `VS.md` updated αν implementation διαφέρει από σχέδιο
- [ ] `docs/ENVIRONMENT.md`: all env vars (Supabase, Stripe, Redis, VS, port, debug flags)
- [ ] `CHANGELOG.md`: all phases documented
- [ ] `README.md`: quickstart με Docker Compose, VS features, vertical configs

### 10.3 Final PR checklist

- [ ] `test_vs_all_flags_disabled.py` (golden regression) passes
- [ ] `test_vs_invariants_global.py` (zero magic numbers) passes
- [ ] All `reproduce_*.py` pass
- [ ] `VSFeatureFlags.all_disabled()` verified
- [ ] Benchmark tables reviewed and committed
- [ ] Open Issues table updated (see below)

---

## Open Issues (Decisions Pending)

| # | Issue | Blocks | Deadline |
|---|---|---|---|
| OI-1 | VS k defaults + latency budget per vertical | Track 3.1 | Track 3 start |
| OI-2 | VSDeploymentProfile nli values | Track 3.3 | Track 3 start |
| OI-3 | GenerationStrategy default | Track 3.3 | Track 3 start |
| OI-4 | VS benchmark on deployed model | Track 3.1 k values | Track 3 start |
| OI-5 | Tail threshold + embedding model | Track 5A start | Week 4 |
| OI-6 | Redis vs PostgreSQL for BehavioralAudit state | Track 5C-E | Week 6 |
| OI-7 | Rate limiter: fail-open vs fail-closed ADR | Track 1C.10 | Week 3 |
| OI-8 | VS + SaaS tier: which verticals require PRO? | Track 5D | Week 6 |
| OI-9 | Minimum trustworthy sources threshold for article pipeline | Track 4.7 | Week 2 |

---

## Definition of Done (Global)

Task = Done when ALL of:

1. Python 3.12, full type hints, zero `Any` without justification
2. pytest ≥ 85% coverage for new module
3. Inter-stage interfaces = Pydantic BaseModel
4. TaintRecord + vs_metadata on all pipeline outputs
5. Feature flag for every VS integration point
6. `VSFeatureFlags.all_disabled()` regression passes
7. Zero magic numbers — all in `ara_vs_constants.py`
8. `asyncio.gather` for independent operations
9. Structured logging with named log key constants
10. Docstring with explicit trade-offs on every public function
11. Clean Architecture: domain layer has zero infra imports
12. Rollback strategy documented per SaaS phase risk table

---

## Merge Notes: What Changed

| Change | Source | Reason |
|---|---|---|
| Rate limiter fail-closed: 3 occurrences → 1 task (T1C.10) | SaaS §12 + C.10 + Performance 3.1 | Identical fix |
| `_broadcast_ws` fix: 2 tasks → 1 (T4.2) | Performance 2.3+2.4 | Same function |
| `asyncio.sleep(0.1)` + cancel check → 1 task (T4.1) | Performance 2.1 + SaaS 7.4 | Same loop |
| Datetime UTC fixes: 3 sections → T0.6 | Security A.1 + C.13 + D.2 | Same pattern |
| VS log keys moved to Track 3.1 (constants) | Was in VS Phase 11 | Belong with constants |
| VS Coverage Audit: Phase 7 → Track 5A-C (Week 4) | VS TODO ordering bug | Only depends on Track 3 |
| VS Observability: Phase 11 → Track 5C-E (Week 6) | VS TODO ordering bug | Only depends on Track 5B |
| VS BehavioralAudit Redis: conditional on Track 6 | NEW cross-stream dependency | Redis not available until Docker |
| `ara_vs_conflict_surfacing.py` added (Track 5C-D) | Missing from VS TODO | VS POINT 8 |
| `VSFeatureFlags` model added (Track 3.3) | Missing from VS TODO | No single source of truth |
| VS + SaaS tier integration (Track 5D) | NEW — neither plan had this | VS premium verticals need tier enforcement |
| VS Prometheus metrics (Track 6.3) | NEW | Observability gap |
| Article writing fixes (Track 4.7) | SaaS §13 sub-section | Existing but not prioritized |
| SaaS Security Audit Phases A-D | Uploaded TODO | Full security hardening |
| 226 + 95 tasks → ~195 unique tasks | Full merge | After deduplication |

---

*Δημιουργήθηκε: 2026-04-26 | ~195 atomic tasks | 10 tracks | 10 weeks*
*Sources: SaaS Launch Plan v1.0 + VS Integration Plan + Security Audit 2026-04-25 + Performance Plan 2026-04-19*
