# Reasoner SaaS Launch — Architectural Implementation Plan

> **Version:** 1.0  
> **Author:** Senior Software Architect  
> **Date:** 2026-04-18  
> **Estimated Duration:** 8–10 weeks  
> **Target:** Transform Reasoner from a single-tenant research tool into a production-grade, multi-tenant SaaS product while preserving existing architectural investments and minimizing blast radius.

---

## 0. Executive Summary

This plan translates the product requirements from `SAAS.md` into a rigorously architected implementation roadmap. It respects the existing **Modular Monolith** structure, extends the already-established **Hexagonal / Ports & Adapters** pattern (evident in `infrastructure/llm/ports.py`), and resolves the **architectural smells** documented in `CODEBASE_MINDMAP.md` (global mutable state, tight coupling, dual-architecture drift).

**Key strategic decisions:**
- **Auth:** Port/Adapter pattern — domain depends on an `AuthPort`, Supabase is the default adapter.
- **Billing:** Port/Adapter pattern — domain depends on a `BillingPort`, Stripe is the default adapter.
- **Quotas:** Domain service (`QuotaService`) with a `QuotaRepository` port. Implementation uses PostgreSQL + Redis cache.
- **Rate Limiting:** Extend existing `RateLimiter` to accept a `user_id` bucketing strategy, preserving the token-bucket algorithm.
- **State Management:** Begin replacing module-level globals (`_cancelled_runs`, `_active_runs`) with request-scoped or Redis-backed state to support horizontal scaling.

---

## 1. Guiding Principles & Patterns

| Principle | Rationale | Enforcement |
|---|---|---|
| **Dependency Rule (Clean Architecture)** | Domain must not know about Supabase, Stripe, Redis, or FastAPI. | All SaaS domain code lives in `src/reasoner/domain/` or `src/reasoner/application/`. Adapters live in `src/reasoner/infrastructure/`. |
| **Open/Closed** | Add auth/quota/billing without touching `pipeline.py` or `phases.py`. | Use FastAPI `Depends()` wrappers; no changes to core reasoning domain. |
| **Ports & Adapters** | Already used for LLM providers; extend to SaaS concerns. | `AuthPort`, `BillingPort`, `QuotaRepository` are abstract protocols. |
| **Single Responsibility** | A module changes for only one reason. | `auth.py` → legacy API-key adapter; `infrastructure/auth/` → SaaS auth adapters. |
| **Don't Repeat Yourself** | Reuse existing middleware, serializer, and event patterns. | `SecurityHeadersMiddleware`, `_event()` SSE helper, `application/event_bus/bus.py` reused. |
| **Fail-Safe by Design** | Every new integration has a graceful degradation path. | Auth down → 401 with retry guidance. Billing webhook down → idempotent replay via Stripe dashboard. |

---

## 2. Domain Model Extensions

New entities belong in the **Domain Layer**. They are pure dataclasses with zero infrastructure knowledge.

```python
# src/reasoner/domain/saas.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from uuid import UUID

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"

@dataclass(frozen=True)
class User:
    """Canonical user entity — auth-provider agnostic."""
    id: UUID
    email: str
    display_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Subscription:
    id: UUID
    user_id: UUID
    tier: SubscriptionTier
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class UsageQuota:
    user_id: UUID
    tier: SubscriptionTier
    used_queries: int = 0
    max_queries: int = 20          # free default; -1 == unlimited
    period_start: datetime = field(default_factory=lambda: datetime.utcnow().replace(day=1))
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class QueryAuditLog:
    id: UUID
    user_id: UUID
    preset: str
    method: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class QuotaResult:
    allowed: bool
    remaining: int
    retry_after: Optional[int] = None   # seconds
    reason: Optional[str] = None
```

---

## 3. Ports (Interfaces)

Defined in `src/reasoner/application/ports/` so the Application Layer can orchestrate without knowing implementation details.

### 3.1 Auth Port
```python
# src/reasoner/application/ports/auth_port.py
from typing import Protocol
from reasoner.domain.saas import User

class AuthPort(Protocol):
    async def authenticate(self, token: str) -> User:
        ...
    async def refresh_session(self, token: str) -> str:
        ...
```

### 3.2 Billing Port
```python
# src/reasoner/application/ports/billing_port.py
from typing import Protocol
from reasoner.domain.saas import Subscription, SubscriptionTier

class BillingPort(Protocol):
    async def create_checkout_session(self, user_id: str, tier: SubscriptionTier, success_url: str, cancel_url: str) -> str:
        """Return checkout URL."""
        ...
    async def create_portal_session(self, user_id: str, return_url: str) -> str:
        """Return billing portal URL."""
        ...
    async def sync_subscription(self, stripe_event: dict) -> Subscription:
        """Idempotent event handler."""
        ...
```

### 3.3 Quota Repository Port
```python
# src/reasoner/application/ports/quota_repository.py
from typing import Protocol
from reasoner.domain.saas import UsageQuota, QuotaResult

class QuotaRepository(Protocol):
    async def get_quota(self, user_id: str) -> UsageQuota:
        ...
    async def check_and_increment(self, user_id: str, preset: str) -> QuotaResult:
        ...
    async def reset_monthly(self, user_id: str) -> None:
        ...
    async def log_query(self, user_id: str, preset: str, method: str, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        ...
```

---

## 4. Application Services

Orchestration layer. These are stateless, testable, and depend only on Ports.

```
src/reasoner/application/
├── services/
│   ├── __init__.py
│   ├── auth_service.py          # Delegates to AuthPort; adds caching
│   ├── quota_service.py         # Business rules: free=20, pro=500, enterprise=-1
│   ├── billing_service.py       # Checkout + portal + webhook orchestration
│   └── audit_service.py         # Writes QueryAuditLog; fire-and-forget via event bus
```

### 4.1 Quota Service Logic
```python
# src/reasoner/application/services/quota_service.py
TIER_LIMITS = {
    SubscriptionTier.FREE: 20,
    SubscriptionTier.PRO: 500,
    SubscriptionTier.ENTERPRISE: -1,   # unlimited
}

class QuotaService:
    def __init__(self, repo: QuotaRepository):
        self._repo = repo

    async def check(self, user_id: str, preset: str, tier: SubscriptionTier) -> QuotaResult:
        limit = TIER_LIMITS[tier]
        if limit == -1:
            return QuotaResult(allowed=True, remaining=-1)
        result = await self._repo.check_and_increment(user_id, preset)
        return result
```

---

## 5. Adapters (Infrastructure)

Concrete implementations of Ports. These are the **only** files allowed to import third-party SDKs (`supabase`, `stripe`, `redis`).

```
src/reasoner/infrastructure/
├── auth/
│   ├── __init__.py
│   ├── supabase_adapter.py      # Implements AuthPort using supabase-py
│   └── local_adapter.py         # Fallback: reads from local JWT secret (dev/test)
├── billing/
│   ├── __init__.py
│   ├── stripe_adapter.py        # Implements BillingPort
│   └── webhooks.py              # Stripe webhook handler (FastAPI router)
├── persistence/
│   ├── quota_repo_postgres.py   # Implements QuotaRepository via asyncpg
│   └── quota_repo_redis.py      # Optional: Redis-backed cache-aside for hot quota reads
└── redis/
    └── client.py                # Shared Redis connection pool
```

---

## 6. Implementation Phases

### Phase 1 — Foundation: Domain + Ports + Postgres Schema (Week 1)

**Goal:** Establish the architectural skeleton. Zero runtime impact on existing code.

**Tasks:**
1. Create `src/reasoner/domain/saas.py` — User, Subscription, UsageQuota, QueryAuditLog, QuotaResult.
2. Create `src/reasoner/application/ports/{auth_port,billing_port,quota_repository}.py`.
3. Create `src/reasoner/application/services/{auth_service,quota_service,billing_service,audit_service}.py`.
4. Write Alembic migration:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

   CREATE TABLE user_profiles (
       id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
       display_name TEXT,
       created_at TIMESTAMPTZ DEFAULT now()
   );

   CREATE TABLE subscriptions (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
       tier TEXT NOT NULL CHECK (tier IN ('free', 'pro', 'enterprise')),
       status TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'past_due', 'trialing')),
       stripe_sub_id TEXT UNIQUE,
       current_period_end TIMESTAMPTZ,
       created_at TIMESTAMPTZ DEFAULT now()
   );

   CREATE TABLE usage_quotas (
       user_id UUID PRIMARY KEY REFERENCES user_profiles(id) ON DELETE CASCADE,
       tier TEXT NOT NULL,
       used_queries INT DEFAULT 0,
       max_queries INT DEFAULT 20,
       period_start TIMESTAMPTZ DEFAULT date_trunc('month', now()),
       updated_at TIMESTAMPTZ DEFAULT now()
   );

   CREATE TABLE query_log (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
       preset TEXT NOT NULL,
       method TEXT NOT NULL,
       tokens_in INT DEFAULT 0,
       tokens_out INT DEFAULT 0,
       cost_usd NUMERIC(10,6) DEFAULT 0.0,
       created_at TIMESTAMPTZ DEFAULT now()
   );

   CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
   CREATE INDEX idx_query_log_user ON query_log(user_id, created_at DESC);
   CREATE INDEX idx_query_log_created ON query_log(created_at);
   ```
5. Add `PresetTier` metadata to existing `PipelinePreset` in `presets.py`:
   ```python
   @dataclass
   class PipelinePreset:
       ...
       required_tier: SubscriptionTier = SubscriptionTier.FREE
   ```
   Tag `*-premium` presets with `required_tier=SubscriptionTier.PRO`.

**Acceptance Criteria:**
- `pytest tests/test_saas_domain.py` passes (unit tests for domain logic).
- Migration applies cleanly to local Postgres.
- Existing `pytest` suite still passes (zero regression).

---

### Phase 2 — Auth Integration: Supabase Adapter + FastAPI Dependencies (Week 2)

**Goal:** Secure the API with real user authentication without breaking legacy API-key support.

**Tasks:**
1. Implement `SupabaseAuthAdapter` in `infrastructure/auth/supabase_adapter.py`.
   - Validates JWT via Supabase `auth.get_user(token)`.
   - Caches validated sessions in Redis (TTL = JWT expiry - 60s).
2. Implement `LocalAuthAdapter` for development/tests (signs/verifies HS256 JWT with `SECRET_KEY`).
3. Create `src/reasoner/api/dependencies.py`:
   ```python
   async def get_current_user(
       bearer: HTTPAuthorizationCredentials = Depends(security),
       auth: AuthPort = Depends(get_auth_adapter),
   ) -> User:
       ...

   async def require_tier(min_tier: SubscriptionTier):
       async def checker(user: User = Depends(get_current_user)) -> User:
           ...
       return checker
   ```
4. Modify `src/reasoner/api/__init__.py`:
   - Add `user: User = Depends(get_current_user)` to `/api/run`, `/api/run-followup`, `/api/history/*`.
   - Keep legacy API-key path behind a feature flag (`ENABLE_LEGACY_API_KEY=true`).
   - Add `/api/auth/me` — returns current user + subscription + quota.
5. Create `src/reasoner/api/saas_router.py` — FastAPI router for all SaaS routes (keeps `api/__init__.py` from growing).

**Design Pattern:**
- **Decorator / Middleware** — FastAPI `Depends()` is a decorator chain. Cross-cutting concerns (auth, quotas) are injected, not hardcoded.
- **Adapter** — `AuthPort` allows swapping Supabase → Auth0 → Clerk without touching domain code.

**Acceptance Criteria:**
- `POST /api/run` without token → 401.
- `POST /api/run` with valid Supabase JWT → 200, `user_id` appears in `query_log`.
- Legacy API key still works when `ENABLE_LEGACY_API_KEY=true`.

---

### Phase 3 — Quota Enforcement (Week 3)

**Goal:** Prevent abuse and monetize via tiered limits.

**Tasks:**
1. Implement `PostgresQuotaRepository` in `infrastructure/persistence/quota_repo_postgres.py`.
   - Uses `asyncpg` with parameterized queries.
   - `check_and_increment` is atomic (SELECT … FOR UPDATE + INSERT/UPDATE in transaction).
2. Add Redis cache-aside layer:
   - Hot read: `GET quota:{user_id}` → TTL 60s.
   - Write-through: increment updates Postgres + invalidates Redis.
3. Extend `RateLimiter` (`src/reasoner/rate_limiter.py`):
   - Add `user_id` as optional bucket key.
   - If `user_id` present, bucket key = `user:{user_id}`; else fall back to IP.
4. Update `/api/run` flow:
   ```
   1. authenticate → User
   2. rate_limiter.check(user.id) → ok | 429
   3. quota_service.check(user.id, preset, tier) → ok | 429 + upgrade_url
   4. tier_service.check(user.id, preset) → ok | 403 + upgrade_url
   5. run_pipeline(...)
   6. audit_service.log_query(...)  # fire-and-forget via event bus
   7. quota_service.increment(user.id)  # idempotent
   ```
5. Add `/api/quota` endpoint — returns `{ used: 14, max: 20, remaining: 6, reset_date: "…" }`.

**Design Pattern:**
- **Repository** — `QuotaRepository` abstracts storage; Postgres is one implementation.
- **Cache-Aside** — Redis caches quota reads, not writes. Same pattern already used for `token_cache.py`.
- **Event Bus** — `audit_service.log_query()` publishes a `QueryCompleted` domain event to `application/event_bus/bus.py`; async handler writes to `query_log`. Keeps the hot path fast.

**Acceptance Criteria:**
- Free user hits 20 queries → 21st returns 429 with `upgrade_url`.
- Pro user hits 500 → same behavior.
- Enterprise user (`max_queries = -1`) → never blocked.
- Quota resets on 1st of month (cron or Postgres trigger).

---

### Phase 4 — Stripe Billing (Week 4–5)

**Goal:** Enable self-service upgrades, downgrades, and invoicing.

**Tasks:**
1. Implement `StripeBillingAdapter` in `infrastructure/billing/stripe_adapter.py`.
   - Wraps `stripe-python` with idempotency keys (`Idempotency-Key: {user_id}:{timestamp}`).
2. Create `src/reasoner/api/billing_router.py`:
   ```python
   POST /api/billing/checkout          # Creates Stripe Checkout session
   POST /api/billing/portal            # Creates Billing Portal session
   GET  /api/billing/subscription      # Current subscription + upcoming invoice
   GET  /api/billing/invoices          # Paginated invoice list
   ```
3. Create `src/reasoner/infrastructure/billing/webhooks.py`:
   ```python
   POST /api/billing/webhook           # Public endpoint; verifies stripe-signature
   ```
   Handled events:
   - `checkout.session.completed` → create Subscription row, set tier=pro/enterprise, reset quota.
   - `customer.subscription.updated` → sync tier/status.
   - `customer.subscription.deleted` → downgrade to free, set `max_queries=20`.
   - `invoice.payment_failed` → set `status=past_due`, notify user via email (event bus).
   - `invoice.payment_succeeded` → reset quota for new period.
4. Frontend pages:
   - `/pricing` — plans table with Stripe Checkout CTA.
   - `/dashboard` — usage graph, current plan, recent queries.
   - `/upgrade` — modal redirect to Stripe.
5. Coupon support:
   - Checkout sessions use `allow_promotion_codes=True`.
   - Optional: `infrastructure/billing/coupons.py` for custom coupon logic (e.g., lifetime deals).

**Design Pattern:**
- **Adapter** — `BillingPort` isolates Stripe specifics.
- **Idempotency** — All webhook handlers are idempotent (upsert on `stripe_sub_id`).
- **Event-Driven** — Billing events publish domain events (`SubscriptionChanged`, `PaymentFailed`) to the event bus. UI and audit log react asynchronously.

**Acceptance Criteria:**
- User upgrades via checkout → tier changes in <5s after webhook.
- User cancels → tier downgrades at period end (Stripe handles this; webhook updates on `deleted`).
- Webhook replay (same event ID) → no duplicate subscription rows.

---

### Phase 5 — Docker & Deployment Packaging (Week 6)

**Goal:** Make Reasoner deployable as a single `docker compose up`.

**Tasks:**
1. `Dockerfile` (backend):
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY src/ src/
   COPY asgi.py .
   EXPOSE 8000
   CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
   ```
2. `ui-next/Dockerfile` (frontend):
   ```dockerfile
   FROM node:22-alpine AS builder
   WORKDIR /app
   COPY package*.json .
   RUN npm ci
   COPY . .
   RUN npm run build
   FROM node:22-alpine AS runner
   WORKDIR /app
   ENV NODE_ENV=production
   COPY --from=builder /app/.next .next
   COPY --from=builder /app/node_modules node_modules
   COPY --from=builder /app/package.json .
   EXPOSE 3000
   CMD ["npm", "start"]
   ```
3. `docker-compose.yml`:
   ```yaml
   version: "3.9"
   services:
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
         - ./nginx/ssl:/etc/nginx/ssl:ro
       depends_on:
         - backend
         - frontend
     backend:
       build: .
       environment:
         - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/reasoner
         - REDIS_URL=redis://redis:6379/0
         - SUPABASE_URL=${SUPABASE_URL}
         - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
         - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
         - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
       depends_on:
         - postgres
         - redis
     frontend:
       build: ./ui-next
       environment:
         - NEXT_PUBLIC_API_URL=/api
         - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
         - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
     postgres:
       image: postgres:16-alpine
       environment:
         POSTGRES_USER: postgres
         POSTGRES_PASSWORD: postgres
         POSTGRES_DB: reasoner
       volumes:
         - postgres_data:/var/lib/postgresql/data
     redis:
       image: redis:7-alpine
       volumes:
         - redis_data:/data
     searxng:
       image: searxng/searxng:latest
       volumes:
         - ./searxng-settings.yml:/etc/searxng/settings.yml:ro
   volumes:
     postgres_data:
     redis_data:
   ```
4. `nginx/nginx.conf` — reverse proxy, rate limit zone, security headers, `/api/` → backend, `/*` → frontend.
5. Health checks:
   - `/api/health` already exists; extend to report Postgres + Redis + Stripe connectivity.
   - Docker `HEALTHCHECK` on backend container.

**Acceptance Criteria:**
- `docker compose up` → all services healthy in <60s.
- `curl http://localhost/api/health` → 200 with all checks green.
- Frontend loads at `http://localhost`, API proxied correctly.

---

### Phase 6 — Security Hardening & GDPR (Week 7)

**Goal:** Production-grade security and compliance.

**Tasks:**
1. **HTTPS enforcement:**
   - Nginx redirects HTTP→HTTPS.
   - HSTS header already in `SecurityHeadersMiddleware`; ensure nginx adds it too.
2. **Secrets management:**
   - `.env.example` updated with all new vars (Supabase, Stripe, Redis).
   - Docker Compose reads from `.env` (never committed).
3. **CORS:**
   - Replace `localhost:3000` with `APP_URL` from settings in production mode.
4. **Stripe webhook security:**
   - Verify `stripe-signature` header using `STRIPE_WEBHOOK_SECRET`.
   - Reject unsigned or tampered payloads with 400.
5. **Audit logging:**
   - All auth events (login, logout, password reset) → `auth_audit_log` table.
   - All quota checks (allowed / denied) → `query_log`.
   - All billing events → `billing_event_log` table.
6. **GDPR endpoints:**
   ```python
   POST /api/account/delete   # Hard delete user + cascade all related rows
   GET  /api/account/export   # JSON dump of user_profiles + subscriptions + query_log
   ```
7. **Dependency scanning:**
   - Add `pip-audit` to CI.
   - Add `npm audit` to frontend CI.

**Design Pattern:**
- **Middleware Chain** — Security headers, CORS, rate limiting, auth are composable FastAPI middleware/dependencies.
- **Audit Trail** — Every mutating operation produces an immutable event log (CQRS-style).

**Acceptance Criteria:**
- `docker compose exec backend pip-audit` → zero high-severity vulnerabilities.
- `POST /api/account/delete` removes all user data (verified by query count = 0).
- Stripe webhook with invalid signature → 400, no DB mutation.

---

### Phase 7 — Monitoring & Observability (Week 8)

**Goal:** Know when things break before users do.

**Tasks:**
1. **Prometheus metrics endpoint** (`/api/metrics`):
   ```python
   from prometheus_client import Counter, Histogram, Gauge, generate_latest

   REASONER_QUERIES_TOTAL = Counter(
       'reasoner_queries_total',
       'Total queries',
       ['tier', 'preset', 'status']
   )
   REASONER_QUERY_DURATION = Histogram(
       'reasoner_query_duration_seconds',
       'Query duration',
       ['preset']
   )
   REASONER_ACTIVE_USERS = Gauge('reasoner_active_users_total', 'Active users (24h)')
   REASONER_QUOTA_EXCEEDED = Counter('reasoner_quota_exceeded_total', 'Quota exceeded', ['tier'])
   REASONER_LLM_ERRORS = Counter('reasoner_llm_errors_total', 'LLM errors', ['provider'])
   ```
2. **Sentry integration:**
   - Backend: `sentry-sdk[fastapi]` initialized in `api/__init__.py` (production only).
   - Frontend: `@sentry/nextjs` initialized in `ui-next/src/app/layout.tsx`.
3. **Structured logging:**
   - Extend existing `logging_utils.py` to include `user_id`, `tier`, `preset` in every log entry.
   - JSON output already implemented; just enrich fields.
4. **Uptime monitoring:**
   - Uptime Robot or Grafana OnCall pings `/api/health` every 60s.

**Acceptance Criteria:**
- `curl /api/metrics` returns Prometheus text format with all metrics > 0 after a query.
- Sentry receives a test exception within 5s of it being raised.
- Log aggregation shows `user_id` and `tier` on every query log line.

---

### Phase 8 — Frontend Self-Service UI (Week 9)

**Goal:** Users can manage their entire lifecycle without support.

**Tasks:**
1. **Auth pages:**
   - `/login` — Supabase Auth UI or custom form.
   - `/signup` — with email verification.
   - `/forgot-password` — magic link flow.
2. **Dashboard (`/dashboard`):**
   - Usage chart (queries per day, tokens per day, cost per day).
   - Current plan card with upgrade CTA.
   - Recent queries table (links to history).
   - Billing portal button.
3. **Pricing (`/pricing`):**
   - Three-tier comparison table (Free / Pro / Enterprise).
   - Stripe Checkout integration for Pro.
   - "Contact Sales" for Enterprise.
4. **Composer upgrades:**
   - Locked preset chips show lock icon + tooltip "Upgrade to Pro".
   - Usage badge in header: "14/20".
   - Upgrade modal triggered on 429 quota exceeded.
5. **Zustand store extensions:**
   ```typescript
   interface AppState {
     user: User | null;
     subscription: Subscription | null;
     quota: QuotaStatus | null;
     setUser: (u: User) => void;
     refreshQuota: () => Promise<void>;
   }
   ```

**Acceptance Criteria:**
- E2E test: sign up → run 20 queries → see 429 → click upgrade → Stripe checkout → run 21st query successfully.

---

### Phase 9 — Performance & Scale Prep (Week 10)

**Goal:** Resolve architectural smells from the mindmap so the SaaS can scale horizontally.

**Tasks:**
1. **Global state extraction:**
   - Move `_cancelled_runs`, `_active_runs` from module-level `dict` to Redis-backed state.
   - New file: `infrastructure/redis/run_state.py` — `RunStateManager` with `cancel(run_id)`, `is_cancelled(run_id)`, `register_active(run_id)`.
   - This enables multi-worker deployments (Gunicorn/Uvicorn workers can share state).
2. **Connection pool hardening:**
   - `OpenAICompatibleProvider._shared_pool` already uses `threading.Lock`.
   - Verify `asyncpg` pool size is configured (default 10; make it `DB_POOL_SIZE` env var).
3. **Database query optimization:**
   - Add composite index on `query_log(user_id, created_at DESC)` (already in Phase 1 migration).
   - Ensure `usage_quotas` read is cached in Redis (Phase 3).
4. **Load testing:**
   - Extend existing `tests/test_load.py` to simulate 100 concurrent authenticated users.
   - Verify no connection pool exhaustion under load.

**Acceptance Criteria:**
- `pytest tests/test_load.py` passes with 100 concurrent users.
- Two uvicorn workers can cancel each other's runs via Redis.

---

## 7. File Inventory

### New Files

| File | Purpose | Layer |
|---|---|---|
| `src/reasoner/domain/saas.py` | Domain entities: User, Subscription, UsageQuota, QueryAuditLog | Domain |
| `src/reasoner/application/ports/auth_port.py` | Auth abstraction (protocol) | Application |
| `src/reasoner/application/ports/billing_port.py` | Billing abstraction (protocol) | Application |
| `src/reasoner/application/ports/quota_repository.py` | Quota storage abstraction | Application |
| `src/reasoner/application/services/auth_service.py` | Auth orchestration | Application |
| `src/reasoner/application/services/quota_service.py` | Quota business rules | Application |
| `src/reasoner/application/services/billing_service.py` | Billing orchestration | Application |
| `src/reasoner/application/services/audit_service.py` | Async audit logging | Application |
| `src/reasoner/infrastructure/auth/supabase_adapter.py` | Supabase JWT adapter | Infrastructure |
| `src/reasoner/infrastructure/auth/local_adapter.py` | Dev/test JWT adapter | Infrastructure |
| `src/reasoner/infrastructure/billing/stripe_adapter.py` | Stripe SDK adapter | Infrastructure |
| `src/reasoner/infrastructure/billing/webhooks.py` | Stripe webhook router | Infrastructure |
| `src/reasoner/infrastructure/persistence/quota_repo_postgres.py` | Quota postgres impl | Infrastructure |
| `src/reasoner/infrastructure/redis/client.py` | Shared Redis pool | Infrastructure |
| `src/reasoner/infrastructure/redis/run_state.py` | Distributed run cancellation | Infrastructure |
| `src/reasoner/api/dependencies.py` | FastAPI dependency injectors | Interface |
| `src/reasoner/api/saas_router.py` | SaaS REST routes | Interface |
| `src/reasoner/api/billing_router.py` | Billing REST routes | Interface |
| `migrations/001_saas_init.py` | Alembic migration | Infrastructure |
| `Dockerfile` | Backend container | Deployment |
| `ui-next/Dockerfile` | Frontend container | Deployment |
| `docker-compose.yml` | Full stack orchestration | Deployment |
| `nginx/nginx.conf` | Reverse proxy + TLS | Deployment |

### Modified Files

| File | Change | Risk |
|---|---|---|
| `src/reasoner/presets.py` | Add `required_tier` to `PipelinePreset`; tag premium presets | LOW — additive only |
| `src/reasoner/api/__init__.py` | Inject `get_current_user` into `/api/run`, `/api/run-followup`; mount new routers | MEDIUM — test all SSE paths |
| `src/reasoner/rate_limiter.py` | Add `user_id` bucketing support | LOW — additive, fallback to IP |
| `src/reasoner/auth.py` | Deprecate in-memory store; delegate to `AuthPort` when SaaS mode enabled | MEDIUM — preserve legacy API key path |
| `src/reasoner/logging_utils.py` | Enrich structured logs with `user_id`, `tier`, `preset` | LOW — additive fields |
| `src/reasoner/core/settings.py` | Add `SUPABASE_*`, `STRIPE_*`, `REDIS_URL`, `ENABLE_LEGACY_API_KEY` | LOW — env loading only |
| `ui-next/src/stores/app-store.ts` | Add user, subscription, quota state | LOW — additive |
| `ui-next/src/app/page.tsx` | Add auth gate, usage badge, locked preset UI | MEDIUM — UI regression risk |
| `.env.example` | Add all new environment variables | LOW |

---

## 8. Testing Strategy

| Layer | Strategy | Tools |
|---|---|---|
| **Domain** | Pure unit tests, no I/O | `pytest` |
| **Application Services** | Mocked ports (protocol fakes) | `pytest` + `unittest.mock` |
| **Adapters** | Integration tests against real services (Supabase test project, Stripe test mode) | `pytest-asyncio` |
| **API** | End-to-end authenticated requests | `httpx.AsyncClient` + `TestClient` |
| **Frontend** | Component + E2E tests for auth flow | `Playwright` (recommended) or `Cypress` |
| **Load** | 100 concurrent users, verify quotas + connection pools | `locust` or `pytest` async tasks |
| **Security** | Dependency audit, webhook signature fuzzing | `pip-audit`, custom pytest |

**Critical test cases:**
1. `test_quota_free_user_blocked_at_21` — deterministic boundary.
2. `test_stripe_webhook_idempotent` — replay same event ID twice, assert one subscription row.
3. `test_redis_run_state_cross_worker` — worker A cancels, worker B detects cancellation.
4. `test_gdpr_delete_cascades_all_data` — verify zero orphan rows.
5. `test_legacy_api_key_backward_compat` — `ENABLE_LEGACY_API_KEY=true` still works.

---

## 9. Risk Mitigation

| Risk | Mitigation | Owner |
|---|---|---|
| **Dual architecture confusion** | All SaaS code routes through `application/` layer; legacy `ARAPipeline` untouched except for injected `user_id`. | Architect |
| **Global mutable state** | Phase 9 extracts `_cancelled_runs` / `_active_runs` to Redis. Deploy after SaaS launch if timeline tight. | Backend Lead |
| **Stripe webhook downtime** | Webhooks are idempotent; Stripe retries with exponential backoff for 3 days. | Backend Lead |
| **Supabase rate limits** | Cache validated JWTs in Redis (TTL = expiry - 60s). | Backend Lead |
| **Database migration failure** | Alembic migration tested against copy of production schema before deploy. | DBA / DevOps |
| **Frontend/Backend contract drift** | Document SSE event schema changes in `docs/OPENROUTER_IMPLEMENTATION_SUMMARY.md` and add `tests/test_api_contract.py`. | Full Stack |
| **Secrets leak** | `.env` never committed; Docker secrets or env injection only; `pip-audit` + `npm audit` in CI. | Security |

---

## 10. Definition of Done (SaaS MVP)

- [ ] User can register, log in, and reset password.
- [ ] Free tier: 20 queries/month, budget presets only.
- [ ] Pro tier: $12/month, 500 queries/month, all presets.
- [ ] Quota exceeded → 429 + upgrade CTA.
- [ ] Stripe checkout → instant tier upgrade.
- [ ] Billing portal → self-service cancel/upgrade.
- [ ] `docker compose up` deploys full stack.
- [ ] HTTPS enforced with HSTS.
- [ ] Prometheus metrics + Sentry error tracking live.
- [ ] GDPR delete/export works.
- [ ] All existing tests pass + new SaaS tests pass.
- [ ] Zero breaking changes to legacy API-key path (behind feature flag).

---

## 11. Appendix: Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Auth Provider** | Supabase Auth | Managed OAuth + email + JWT; free tier; no infra; aligns with existing PostgreSQL choice. |
| **Billing Provider** | Stripe | Industry standard; native coupons; billing portal; excellent Python SDK. |
| **Session Cache** | Redis | Already needed for distributed rate limiting and run-state; minimal additional complexity. |
| **Container Orchestration** | Docker Compose | Matches current single-process model; migrate to K8s only after product-market fit. |
| **Reverse Proxy** | Nginx | Familiar, well-documented, integrates with Let's Encrypt/Caddy for TLS. |
| **Frontend Auth** | Supabase SSR (`@supabase/ssr`) | Secure server-side JWT handling in Next.js App Router; no token leakage to client JS. |
| **Database Migrations** | Alembic | Standard SQLAlchemy companion; already implied by existing Postgres support. |

---

*End of Plan*


---

## 12. Reliability & Developer Experience Fixes

> **Source:** Debugging session (2026-04-19)  
> **Goal:** Eliminate opaque startup failures and "fetch failed" errors.

### Critical (Do First)

- [ ] **Fix `asyncpg` crash** — Verify `src/reasoner/infrastructure/persistence/postgres_store.py` line 23 uses `asyncpg.PostgresError`
- [ ] **Lazy-load PostgreSQL** — Edit `src/reasoner/infrastructure/persistence/__init__.py` to use `__getattr__` instead of eager imports. Prevents backend crash when asyncpg is missing/broken.
- [ ] **Add import smoke test** — In `src/reasoner/start_all.py`, run `python -c "import sys; sys.path.insert(0, 'src'); from reasoner.api import app"` before spawning uvicorn. Exit with clear error if it fails.
- [ ] **Unify ports to 8001** — Change `README.md` quickstart from `8000` to `8001`. Add `DEFAULT_API_PORT = 8001` to `src/reasoner/core/constants.py`.

### High Value

- [ ] **Fix proxy error codes** — In `ui-next/src/app/api/run/route.ts` (and `run-followup.ts`), return `504` for connection errors instead of `400`. Log `upstream_url` and error type to console.
- [ ] **Actionable frontend errors** — In `ui-next/src/hooks/usePipelineStream.ts`, show `"Backend unreachable (port 8001). Run: uvicorn asgi:app --port 8001"` when status is 504 (dev mode only).
- [ ] **Port conflict check** — In `start_all.py`, check if port is in use before spawning. Print the occupying PID if found.
- [ ] **Health polling** — Replace `time.sleep(1)` in `start_all.py` with a poll loop hitting `http://127.0.0.1:8001/` until 200 or timeout.
- [ ] **Fix `is_retryable()`** — In `src/reasoner/exceptions.py`, handle OpenAI SDK errors (`status_code` attribute) and `"fetch failed"` message as retryable.

### Polish

- [ ] **Turbopack cache bust** — Add `SECURITY_SERVER_HASH` export to `security-server.ts` and import it in API routes so Turbopack recompiles when ports change.
- [ ] **Document env vars** — Add `docs/ENVIRONMENT.md` listing `API_BASE_URL`, `NEXT_PUBLIC_API_BASE_URL`, `PORT`, and their defaults.
- [ ] **Add dev note** — Document in `README.md` or `AGENTS.md` that Next.js dev server must be restarted after changing `security-server.ts`.

### Files to Edit

| File | What to Change |
|------|---------------|
| `src/reasoner/infrastructure/persistence/__init__.py` | Lazy-load PostgreSQL exports |
| `src/reasoner/infrastructure/persistence/postgres_store.py` | Verify `asyncpg.PostgresError` |
| `src/reasoner/core/constants.py` | Add `DEFAULT_API_PORT = 8001` |
| `src/reasoner/start_all.py` | Smoke test, port check, health poll |
| `src/reasoner/exceptions.py` | Fix `is_retryable()` |
| `ui-next/src/lib/security-server.ts` | Add `SECURITY_SERVER_HASH` |
| `ui-next/src/app/api/run/route.ts` | Fix error codes, log upstream URL |
| `ui-next/src/app/api/run-followup/route.ts` | Same error-code fix |
| `ui-next/src/hooks/usePipelineStream.ts` | Actionable dev-mode errors |
| `README.md` | Change quickstart port to `8001` |
| `docs/ENVIRONMENT.md` (new) | Env var schema |

### Verification

1. `python -c "import sys; sys.path.insert(0, 'src'); from reasoner.api import app"` → exits 0
2. `python start_all.py` with backend already on 8001 → clear error, exits 1
3. Start backend on 8001, frontend on 3000 → pipeline runs successfully
4. Kill backend mid-request → frontend shows "Backend unreachable" not "HTTP 400"


---

## 13. Search Quality & Response Time Enhancements

> **Source:** Production debugging session (2026-04-19)  
> **Goal:** Fix search fallback bug, filter irrelevant sources, reduce token waste, and improve response times.

### Critical (Do First)

- [ ] **Fix search fallback bug** — In `src/reasoner/core/search.py` lines 183–194, remove the block that returns unfiltered raw results when all results fail `_should_include_result()`. Return `[]` instead.
- [ ] **Expand `_OFF_TOPIC_PATTERNS`** — Add `wordreference.com`, `facebook.com`, `biography.com`, `imdb.com`, `thetimes.com`, `reddit.com`, and other low-signal domains.

### High Value

- [ ] **Log decomposition failures** — In `smart_search()`, when `_decompose_query()` fails and falls back to direct search, emit a `logger.warning()` with the raw query visible.
- [ ] **Add keyword extraction fallback** — When decomposition fails, extract English keywords from mixed-language prompts using regex (`_extract_search_keywords()`) instead of searching with the raw prompt.
- [ ] **Skip disambiguation for clear queries** — In `_phase_context_vetting()`, skip the disambiguation LLM call if `len(problem) < 120` and no ambiguous terms are present.
- [ ] **Cache decomposition results** — Add an in-memory TTL cache (`_DECOMPOSITION_CACHE`) around `_decompose_query()` to avoid recomputing for identical queries.

### Medium Value

- [ ] **Early-exit on terrible results** — In `_phase_context_vetting()`, if `<3` results pass `_should_include_result()` after the first iteration, break the loop and proceed with LLM-only analysis.
- [ ] **Add search telemetry** — In `DiscoveryClient.search()`, log the pass rate: `"Search quality: X/Y results passed filtering (Z%)"`.
- [ ] **Reduce synthesis context** — In `to_context_dict()` or synthesis prompt builder, summarize web results as `"Title: Snippet"` instead of embedding full `web_discovery_results` objects.

### Testing

- [ ] **Unit tests** — Create `tests/test_search_quality.py` with tests for biography/dictionary rejection and empty fallback behavior.
- [ ] **Integration test** — Re-run "Orthodox-Informed Wellbeing & Habits Coach" query → verify Deep Read returns 0 garbage sources.
- [ ] **Regression test** — Run "Scientific method for hypothesis testing" → verify relevant academic sources are still found.

### Files to Edit

| File | Changes |
|------|---------|
| `src/reasoner/core/search.py` | Fallback bugfix, expanded patterns, keyword extraction, decomposition cache, telemetry |
| `src/reasoner/pipeline.py` | Skip disambiguation, early-exit on poor results |
| `src/reasoner/models.py` (or `phases.py`) | Truncate web results in synthesis context |
| `tests/test_search_quality.py` (new) | Unit tests |
## Article Writing Failure Remediation Plan

### Problem
- Article requests can be routed into the generic multi-perspective pipeline instead of the dedicated writing pipeline.
- Follow-up context handling can leak unrelated prior prompts and rendered phase output into new analytical or writing requests.
- Search and source filtering are too weak for research-backed writing, allowing irrelevant and unsafe sources into the evidence set.
- The article retrieval path has an implementation defect around discovery-client usage and is not robust enough to be the primary writing retrieval path as-is.

### Root Cause Chain
- The frontend treats nearly every later turn as a follow-up and sends prior chat history plus the previous assistant output back to the backend.
- The backend injects that follow-up context into classification, decomposition, perspective, and synthesis prompts without checking whether the new request is actually a continuation.
- Method routing for article requests is still heuristic/LLM-driven, so an article prompt can fall back to `multi_perspective` instead of `writing`.
- Once misrouted, contaminated context influences decomposition and perspective generation, which then poisons search intent and source selection.
- Search gating relies on a limited denylist and weak heuristic filters, so junk or unsafe sources can survive if they look superficially article-like.
- The dedicated article retrieval path currently calls `get_discovery_client()` incorrectly and also uses simplistic query expansion and ranking.

### Fix Plan

#### 1. Deterministic Writing Routing
- Add a server-side writing-intent detector for prompts requesting an article, essay, blog post, report, explainer, or research-backed writeup.
- If writing intent is detected, bypass generic method classification and force `writing-budget` or `writing-premium` based on the active tier.
- Keep this override on the backend so it applies regardless of client behavior.
- Add regression tests proving article/essay prompts resolve to the writing workflow and phase sequence.

#### 2. Safe Follow-Up Scoping
- Replace the current “any existing assistant message means follow-up” behavior with explicit continuation detection.
- Only send follow-up context when the new turn is referential, such as “continue,” “expand,” “revise that,” “same topic,” or equivalent signals.
- For non-referential new requests, start a fresh run context even if they occur in the same visible chat session.
- Add frontend and backend safeguards so non-conforming clients cannot reintroduce this bug.

#### 3. Context Minimization
- Stop injecting raw multi-turn history into classification, decomposition, perspective, and synthesis prompts by default.
- Build a compact structured continuation context with only bounded fields such as prior topic, prior constraints, prior method, and a concise summary.
- Never pass rendered phase markdown or raw intermediate reasoning back into follow-up prompts.
- Exclude image-generation prompts/results from unrelated analytical or writing turns unless the user explicitly references them.

#### 4. Previous Synthesis Hygiene
- Change follow-up payload construction so `previous_synthesis` contains only the real final answer payload, not rendered phase output.
- Store a dedicated summary or `final_solution.core_solution` for follow-up use.
- Add tests for cross-mode contamination: image request followed by article request must not leak character names, scene details, or prior failures.

#### 5. Repair the Article Retrieval Path
- Fix `_phase_article_retrieve` to correctly unpack `get_discovery_client()` and use the returned client object safely.
- Replace naive query variants like “overview” and “evidence analysis” with retrieval grounded in decomposed subquestions plus shared search utilities.
- Prefer using the existing shared search/ranking pipeline instead of a second weaker retrieval stack.
- Add focused regression tests for retrieval success, failure handling, and tuple-unpacking correctness.

#### 6. Strengthen Source Safety and Relevance Filtering
- Extend domain rejection to explicitly block adult-content, forum-spam, low-signal UGC, and irrelevant aggregator surfaces.
- Add topical relevance scoring between the user’s request and candidate results before admission to the article evidence set.
- Add trust weighting by source class: peer-reviewed, academic, government, primary archive, reputable newsroom, and known low-trust surfaces.
- Fail closed when the evidence set is dominated by weak or off-topic sources.
- Add regression tests for known bad domains and obviously irrelevant titles/snippets.

#### 7. Writing Pipeline Fail-Closed Rules
- Require a minimum count of trustworthy, on-topic sources before article drafting proceeds.
- Abort with an evidence-insufficient response when claim-support ratio remains below threshold after verification.
- Prevent final assembly from presenting a polished article if retrieval or verification quality gates fail.
- Ensure the user gets a clear explanation of evidence limits instead of a contaminated or low-trust article.

#### 8. End-to-End Verification
- Add unit tests for routing, follow-up scoping, source filtering, and article retrieval.
- Add integration tests for same-chat mode changes:
- Image generation turn followed by unrelated article request.
- Generic analytical turn followed by unrelated writing request.
- True continuation request followed by correctly scoped follow-up context.
- Assert the writing phase sequence appears for article requests and that contaminated terms do not appear in decomposition/perspective prompts.

#### 9. Safe Observability
- Add debug logging that records phase/method/routing decisions and follow-up-mode decisions without logging raw user content.
- Log hashed request identifiers and structured reasons for “fresh run” vs “follow-up continuation.”
- Log source-filter rejection reasons so unsafe or irrelevant admissions can be diagnosed without exposing sensitive prompt text.

### Implementation Order
- 1. Deterministic writing routing.
- 2. Follow-up scoping and context minimization.
- 3. `previous_synthesis` hygiene.
- 4. Article retrieval bug fix and shared-search integration.
- 5. Stronger source safety/relevance filters.
- 6. Fail-closed writing quality gates.
- 7. Regression and integration coverage.
- 8. Observability improvements.

### Acceptance Criteria
- An explicit article request always enters the writing workflow.
- A non-referential new request in the same chat does not inherit prior task details.
- Prior image-generation prompts do not appear in later article decomposition or perspective output unless explicitly referenced.
- Unsafe/off-topic sources are rejected before claim extraction.
- The article pipeline either produces a research-backed article with traceable sources or fails explicitly with an evidence-insufficient response.
- Regression coverage exists for routing, context isolation, retrieval, and source safety.


---

# Implementation Plan — Remaining Tasks (Post-Audit)

> **Created:** 2026-04-26  
> **Source:** TODO_1.md audit results  
> **Total remaining:** ~150 atomic tasks across 6 phases  
> **Estimated duration:** 6–7 weeks (single developer, sequential phases)

## Guiding Principles
1. **Security before speed.** Phase 1 closes all critical gaps before any performance work.
2. **Backend before frontend.** API contracts must stabilize before UI polish.
3. **VS tracks are sequential.** Foundation (Phase 3) blocks all integration (Phase 4).
4. **Test at every phase.** No phase merges without passing its own test suite.

---

## Phase Overview

| Phase | Focus | Duration | Risk | Blocking |
|-------|-------|----------|------|----------|
| **1** | Critical Security & Stability | Week 1 | High | All production deployments |
| **2** | Performance Quick Wins | Weeks 1–2 | Medium | User experience, throughput |
| **3** | VS Foundation | Weeks 2–3 | Medium | All VS integration tracks |
| **4** | VS Integration | Weeks 3–6 | High | Product roadmap |
| **5** | Scale Prep & Polish | Week 6 | Low | Horizontal scaling readiness |
| **6** | E2E Tests & Benchmarks | Week 7 | Low | Release confidence |

**Hard dependencies:**
- Phase 1 must finish before Phase 2 starts.
- Phase 3 must finish before Phase 4 starts.
- Phase 4 must finish before Phase 6 starts (E2E tests need VS stages).
- Phase 5 can run parallel to Phase 4 after Week 4.

**Detailed plans for each phase live in separate files:**
- `tasks/phase-1-security.md`
- `tasks/phase-2-performance.md`
- `tasks/phase-3-vs-foundation.md`
- `tasks/phase-4-vs-integration.md`
- `tasks/phase-5-scale-prep.md`
- `tasks/phase-6-e2e-benchmarks.md`

---

## Cross-Phase Rules

- Every Python function gets type hints; `Any` requires a `# reason:` comment.
- Every new module needs ≥ 85 % pytest coverage.
- All inter-stage interfaces are `pydantic.BaseModel`.
- `TaintRecord.vs_metadata` propagates to every pipeline output that touches VS.
- Feature flags (`VSFeatureFlags.all_disabled()` regression test) guard every VS integration point.
- Zero magic numbers — all constants live in `ara_vs_constants.py`.
- `asyncio.gather` for independent operations.
- Structured logging with named key constants.
