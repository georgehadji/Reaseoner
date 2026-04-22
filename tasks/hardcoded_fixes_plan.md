# Plan: Remove Hardcoded Values

## Goal
Eliminate all hardcoded URLs, ports, hosts, and magic constants that cause portability issues or environment mismatches. Keep the project deployable across different ports, hosts, and Docker setups without code changes.

## Strategy
1. **Backend-first**: Fix Python source (settings, constants, API routes) before touching frontend
2. **Shared config**: Introduce `REASONER_API_URL` and `CORS_ORIGINS` env vars
3. **Centralize fallbacks**: Every hardcoded fallback must read from `settings` or `constants`
4. **Test after each batch**: Run backend tests + frontend build before proceeding to next batch
5. **Backward compatibility**: Every env var must have a sensible default matching current behavior

---

## Phase 1 — Settings & Constants Foundation (P0)

### 1.1 Extend `src/reasoner/core/settings.py`

Add new environment-aware properties:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8001,http://127.0.0.1:8001` | Comma-separated CORS allow-origins |
| `UVICORN_HOST` | `0.0.0.0` | Host for uvicorn bind |
| `OPENROUTER_HTTP_REFERER` | `https://github.com/Reasoner` | OpenRouter analytics referer |
| `OPENROUTER_APP_TITLE` | `Reasoner` | OpenRouter app title |

Add `cors_origins_list` computed property that splits the comma string.

### 1.2 Update `.env.example`

Add the new variables with comments explaining when to change them.

### 1.3 Verify no regressions

- `python -c "from reasoner.core.settings import settings; print(settings.cors_origins_list)"`
- 51 backend tests must still pass

---

## Phase 2 — Backend API & Routes (P0)

### 2.1 Fix CORS origins in `src/reasoner/api/__init__.py`

**Current:**
```python
allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", ...]
```

**Target:**
```python
allow_origins=settings.cors_origins_list
```

### 2.2 Fix startup log messages in same file

Use `settings.SERVER_HOST` and `settings.SERVER_PORT` to print correct URLs on startup.

### 2.3 Fix WebSocket docstrings

- `src/reasoner/api/routes/websocket.py:24-25`
- `src/reasoner/infrastructure/websocket/manager.py:310-311`

Replace hardcoded `ws://localhost:8000/ws` with dynamic docstrings using `settings.SERVER_PORT`, or add a clear `NOTE: example URL` comment.

### 2.4 Fix legacy widget URLs in `src/reasoner/widgets.py`

**Lines 520-521, 562-563:** Replace hardcoded `localhost:8080` with `settings.SEARXNG_URL` (port 8888) or `get_searxng_urls()`.

### 2.5 Fix SearXNG fallback in `src/reasoner/core/search.py`

**Line 658:** Remove the literal `http://127.0.0.1:8888/search` fallback. `get_searxng_urls()` should return only the configured base URL variants.

### 2.6 Fix OpenRouter headers in `neuro/providers.py` and `core/rerank.py`

Replace hardcoded strings with `settings.OPENROUTER_HTTP_REFERER` and `settings.OPENROUTER_APP_TITLE`.

### 2.7 Fix `start_all.py` uvicorn host

Make `--host` read from `UVICORN_HOST` env var.

### 2.8 Fix `server_check.py` startup message

Use dynamic host/port in the "Then open:" message.

### 2.9 Verify

- Run `python -m pytest tests/ -q`
- Start backend on a non-default port and confirm CORS + logs are correct

---

## Phase 3 — Frontend Proxy & Config (P0)

### 3.1 Unify frontend API base config

**Problem:** Two sources of truth:
- `ui-next/src/lib/server-config.ts` (new, used by neuro routes)
- `ui-next/src/lib/security-server.ts:82` (old fallback, used by general API)

**Fix:** Make `security-server.ts` import from `server-config.ts`.

### 3.2 Fix `usePipelineStream.ts` hardcoded error message

**Line 10:** Replace hardcoded `port 8001` with dynamic text using `REASONER_API_BASE`.

### 3.3 Verify frontend build

- `cd ui-next && npm run build` must succeed

---

## Phase 4 — Scripts & Batch Files (P1)

### 4.1 `start_all.bat`

- Accept `%*` arguments and pass them to `start_all.py`
- PowerShell port-check snippets should loop over a configurable port list instead of hardcoding 8000/8001

### 4.2 `kill_servers.bat`

- Same: accept port arguments or read from `.env`

### 4.3 `docker-compose.searxng.yml`

- Change `SEARXNG_BASE_URL=http://localhost:8888/` to use `${SEARXNG_URL:-http://localhost:8888/}`

### 4.4 Verify

- Manual test: run `start_all.bat --main-port 9000` and confirm it starts on 9000

---

## Phase 5 — Documentation Cleanup (P2)

### 5.1 Update docstrings with dynamic examples

- `websocket.py`, `manager.py`, `server_check.py`
- Add `NOTE: example URL — actual port depends on SERVER_PORT` where dynamic isn't possible

### 5.2 Update `README.md`, `AGENTS.md`, `QWEN.md`, `GEMINI.md`

Replace stale `localhost:8000` references with `localhost:8001` (or note that port is configurable).

### 5.3 Update `docs/ENVIRONMENT.md`

Document all new env vars added in Phase 1.

---

## Rollback Plan

If any test fails:
1. Revert the file that caused the failure
2. Re-run tests to confirm green
3. Re-examine the fix approach before re-applying

---

## Acceptance Criteria

- [ ] `grep -r "localhost:8000" src/reasoner/api/` returns **only** docstring comments marked as examples
- [ ] `grep -r "localhost:8080" src/reasoner/` returns **zero** results
- [ ] `grep -r "github.com/Reasoner" src/reasoner/` returns **zero** results (or reads from env)
- [ ] 51 backend tests pass
- [ ] Frontend build succeeds
- [ ] Backend starts and logs correct URL when run on `--port 9000`
- [ ] CORS allows origins from `.env` correctly
