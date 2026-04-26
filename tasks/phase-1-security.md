# Phase 1 — Critical Security & Stability

> **Duration:** Week 1 (Days 1–3)  
> **Risk:** High — touches auth, rate limiting, WebSocket security  
> **Goal:** Close all critical security gaps before any production deployment.

---

## Pre-Phase Checklist

- [ ] `git checkout -b phase-1-security`
- [ ] `python -m pytest -v` passes on baseline
- [ ] `cd ui-next && npm run build` passes on baseline

---

## 1.1 Infrastructure Fixes (TRACK 0 Remaining)

### T0.2 Fix `pytest.ini` / `conftest.py`
**Effort:** 30 min  
**Files:** `pytest.ini`, `tests/conftest.py`

```ini
# pytest.ini — append these lines
addopts = --durations=10
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
```

```python
# tests/conftest.py — wrap module-level mutations in session fixture
@pytest.fixture(scope="session", autouse=True)
def _test_env_setup():
    import os, tempfile
    old_csrf = os.environ.get("CSRF_ENFORCE_BACKEND")
    old_tempdir = tempfile.tempdir
    os.environ["CSRF_ENFORCE_BACKEND"] = "false"
    tempfile.tempdir = str(temp_root)  # type: ignore[assignment]
    yield
    if old_csrf is None:
        os.environ.pop("CSRF_ENFORCE_BACKEND", None)
    else:
        os.environ["CSRF_ENFORCE_BACKEND"] = old_csrf
    tempfile.tempdir = old_tempdir
```

**AC:** `pytest --collect-only` shows 0 errors; no `DeprecationWarning` from `pytest-asyncio`.

---

### T0.3 Update `requirements.txt`
**Effort:** 15 min  
**File:** `requirements.txt`

- `stripe>=12.0.0,<13.0.0` → `stripe>=12.0.0,<16.0.0`
- `redis>=5.0.0,<6.0.0` → `redis>=5.0.0,<8.0.0`
- `pypdf>=4.0.0,<6.0.0` → `pypdf>=4.0.0,<7.0.0`
- Remove `newspaper3k>=0.2.8,<0.3.0` (line 41)
- Move `gunicorn>=22.0.0,<24.0.0` from `# Testing` section to new `# Production WSGI` section

**AC:** `pip install -r requirements.txt` completes without conflicts.

---

### T0.6 Fix naive datetime usage
**Effort:** 30 min  
**Files:** `src/reasoner/auth.py`, `src/reasoner/healing/introspection_engine.py`, `src/reasoner/healing/test_generation_engine.py`

```python
# auth.py:197
from datetime import timezone
cached.last_used_at = datetime.now(timezone.utc)

# introspection_engine.py:609
timestamp=datetime.now(timezone.utc).isoformat()

# test_generation_engine.py:275
timestamp=datetime.now(timezone.utc).isoformat()
```

**AC:** `grep -n "datetime.now()" src/reasoner/auth.py src/reasoner/healing/*.py` returns 0 matches.

---

## 1.2 Rate Limiter Fail-Closed (TRACK 1C.10) — CRITICAL

**Effort:** 1 hour  
**File:** `src/reasoner/api/auth_deps.py:50-56`  
**Severity:** Critical — currently fail-open on any exception

```python
# BEFORE
except Exception as exc:
    logger.error("Rate limiter error: %s", exc)
    allowed = True
    info = {"limit_minute": 60, "remaining_minute": 60, "retry_after": None}

# AFTER
from reasoner.rate_limiter import RateLimitError

except RateLimitError:
    allowed = False
    info = {"limit_minute": 60, "remaining_minute": 0, "retry_after": 60}
except Exception as exc:
    logger.exception("Rate limiter infrastructure failure")
    raise HTTPException(status_code=503, detail="Rate limiting unavailable")
```

**AC:** `pytest tests/test_auth_deps.py::test_rate_limiter_fail_closed` — mock `is_allowed` to raise `RuntimeError` → expect 503.

---

## 1.3 WebSocket Authentication (TRACK 1B.8) — CRITICAL

**Effort:** 3 hours  
**Files:** `src/reasoner/api/routes/websocket.py`, `src/reasoner/infrastructure/websocket/manager.py`

### Step 1: Parse JWT in WebSocket handshake
```python
# websocket.py — inside websocket_connect()
async def websocket_connect(websocket: WebSocket, pipeline_id: str | None = None):
    token = websocket.query_params.get("token") or _extract_bearer(websocket.headers)
    if not token:
        await websocket.close(code=1008, reason="Missing auth token")
        return
    user = await _authenticate_ws_token(token)
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return
    await websocket_endpoint(websocket, pipeline_id, user)
```

### Step 2: Enforce pipeline ownership on subscribe
```python
# websocket/manager.py — inside subscribe()
async def subscribe(self, websocket, pipeline_id: str, user: User):
    owner = _get_pipeline_owner(pipeline_id)
    if owner and str(user.id) != owner and Scope.ADMIN.value not in user.scopes:
        await websocket.send_json({"type": "error", "detail": "Not authorized for this pipeline"})
        return
    # ... existing subscription logic
```

**AC:**
- `test_websocket_auth.py` — no token → connection closed with 1008.
- `test_websocket_authz.py` — User B subscribes to User A's pipeline → error message, no events received.

---

## 1.4 CSRF Monotonic Clock (TRACK 1B.1)

**Effort:** 1 hour  
**File:** `src/reasoner/api/csrf.py:36,67`

**Problem:** `time.time()` is vulnerable to system clock jumps.  
**Solution:** Use signed expiry tokens instead of raw timestamps.

```python
# csrf.py — replace time.time() with HMAC-signed expiry
import hmac, hashlib, secrets

_CSRF_SECRET = secrets.token_hex(32)

def _generate_csrf_token() -> str:
    expiry = int(time.time()) + _CSRF_TOKEN_MAX_AGE
    payload = f"{expiry}:{secrets.token_urlsafe(16)}"
    sig = hmac.new(_CSRF_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}:{sig}"

def _validate_csrf_token(token: str) -> bool:
    try:
        expiry, nonce, sig = token.rsplit(":", 2)
        expected = hmac.new(_CSRF_SECRET.encode(), f"{expiry}:{nonce}".encode(), hashlib.sha256).hexdigest()[:16]
        if not secrets.compare_digest(sig, expected):
            return False
        return int(time.time()) < int(expiry)
    except Exception:
        return False
```

**AC:** `test_csrf_clock_jump.py` — system clock jumps forward 1 hour → token rejected.

---

## 1.5 Provider Router Graceful Degradation (TRACK 1B.6)

**Effort:** 2 hours  
**File:** `src/reasoner/infrastructure/llm/router.py`

```python
# NEW dataclass in router.py or ports.py
@dataclass
class DegradedLLMResponse:
    text: str = ""
    metadata: dict = field(default_factory=dict)
    degraded: bool = True
    error: str = ""

# Inside router.py fallback logic — replace raw dict returns
if not fallback_result:
    return DegradedLLMResponse(
        text="",
        error=f"{assigned.model} and {fallback.model} both failed",
        metadata={"model": fallback.model}
    )
```

Update downstream callers in `streaming.py` to detect `isinstance(result, DegradedLLMResponse)` and emit `phase_warning`.

**AC:** `test_provider_router_degradation.py` — all providers blocked → returns `DegradedLLMResponse`, pipeline continues.

---

## 1.6 Redis Quota Cache Fallback (TRACK 1B.7)

**Effort:** 3 hours  
**New file:** `src/reasoner/infrastructure/cached_quota_repo.py`

```python
from reasoner.application.ports.quota_repository import QuotaRepository

class CachedQuotaRepository(QuotaRepository):
    def __init__(self, redis_client, fallback_repo: QuotaRepository):
        self._redis = redis_client
        self._fallback = fallback_repo

    async def get_remaining(self, user_id: str) -> int:
        try:
            cached = await self._redis.get(f"quota:{user_id}")
            if cached is not None:
                return int(cached)
        except (ConnectionError, TimeoutError) as exc:
            logger.warning("Redis quota cache unavailable, falling back to DB: %s", exc)
        return await self._fallback.get_remaining(user_id)
```

**AC:** `test_quota_redis_fallback.py` — Redis stopped → quota check via Postgres succeeds.

---

## 1.7 Event Bus Queue Backpressure (TRACK 1B.3)

**Effort:** 1 hour  
**File:** `src/reasoner/application/event_bus/bus.py:49`

```python
# BEFORE
self._task_queue: asyncio.Queue | None = None

# AFTER
self._task_queue: asyncio.Queue | None = None
self._max_queue_size: int = 1000

# In __init__ or start()
self._task_queue = asyncio.Queue(maxsize=self._max_queue_size)

# In publish()
try:
    self._task_queue.put_nowait((event, handler))
except asyncio.QueueFull:
    logger.error("Event bus queue full; dropping event %s", event.event_id)
    # Optionally write to overflow dead-letter
```

**AC:** `test_event_bus_backpressure.py` — publish 1001 events → 1 dropped, 1000 processed.

---

## 1.8 Latency Measurement Fix (TRACK 1D.1)

**Effort:** 1 hour  
**Files:** `infrastructure/llm/ports.py`, `neuro/server.py`, `infrastructure/widgets/protocol.py`

Bulk replace:
```python
# BEFORE
start_time = time.time()
# ... work ...
latency_ms = (time.time() - start_time) * 1000

# AFTER
start_time = time.perf_counter()
# ... work ...
latency_ms = (time.perf_counter() - start_time) * 1000
```

**AC:** `grep -n "time.time()" src/reasoner/infrastructure/llm/ports.py src/reasoner/neuro/server.py src/reasoner/infrastructure/widgets/protocol.py` returns 0 matches in latency paths.

---

## Testing Strategy

| Test File | Coverage |
|---|---|
| `test_auth_deps_rate_limiter.py` | Fail-closed behavior |
| `test_websocket_auth.py` | JWT validation, 1008 close |
| `test_websocket_authz.py` | Pipeline ownership enforcement |
| `test_csrf_clock_jump.py` | Monotonic expiry validation |
| `test_provider_router_degradation.py` | `DegradedLLMResponse` return |
| `test_quota_redis_fallback.py` | Cache miss → DB fallback |
| `test_event_bus_backpressure.py` | QueueFull handling |
| `test_perf_counter_migration.py` | Zero `time.time()` in latency paths |

---

## Definition of Done

- [ ] All critical security gaps closed (rate limiter, WS auth).
- [ ] `pytest -v` passes with ≥ baseline count.
- [ ] `cd ui-next && npm run build` passes.
- [ ] No `time.time()` used for TTL or latency measurement.
- [ ] Every new function has type hints.
