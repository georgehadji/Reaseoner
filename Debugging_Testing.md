# Debugging + Testing Protocol — Reasoner Project

> Applies to: **Backend** (`src/reasoner/` — Python 3.12+, FastAPI, pytest) and **Frontend** (`ui-next/` — Next.js 16, TypeScript 5, Vitest, Playwright).
> This is a project-specific adaptation of the generic 8-phase debugging protocol.

---

## AUTONOMOUS DEBUGGING (Proactive Scanning + Auto-Fix)

Run the autonomous debugger to proactively scan AND FIX the entire codebase:

```bash
python autonomous_debug.py
```

This will **automatically**:
1. **Phase 1:** Fix import mismatches (ara_* → reasoner_*, ARAPipeline → ReasonerPipeline, etc.)
2. **Phase 2:** Scan all Python files for syntax errors
3. **Phase 3:** Verify all 1666+ tests can be collected
4. **Phase 4:** Run critical regression tests (32 tests)
5. **Phase 5:** Check frontend test files (267 files)

### Auto-Fix Patterns (No User Input Required)

The debugger automatically fixes these patterns across all files:

| Pattern | Auto-Fix To |
|---------|-------------|
| `from reasoner.ara_verbalized_sampling import` | `from reasoner.reasoner_verbalized_sampling import` |
| `from reasoner.ara_vs_constants import` | `from reasoner.reasoner_vs_constants import` |
| `from reasoner.ara_persuasion_defense import` | `from reasoner.reasoner_persuasion_defense import` |
| `from reasoner.ara_vs_config import` | `from reasoner.vs_config import` |
| `ARAPipeline` | `ReasonerPipeline` |
| `ARAPersuasionIntegration` | `ReasonerPersuasionIntegration` |

### Exit Codes

- **0:** Codebase is healthy (no issues found or all auto-fixed)
- **1:** Issues require manual attention (syntax errors, test failures)

---

## EPISTEMIC RULES

Every claim about a bug's cause must be classified:

- **VERIFIED:** You can trace a concrete failing execution path in the code. The failure is deductively necessary from the code structure.  
- **HYPOTHESIS:** You have a plausible mechanism but cannot confirm it without runtime testing. State your confidence: Low / Medium / High.  
- **UNKNOWN:** You cannot determine the cause from available evidence. Request what you need.  
- **FALSE:** A hypothesis was tested and disproven.

If you cannot classify a claim, do not assert it.

---

## GLOBAL CONSTRAINTS

- **≥2 competing hypotheses** per issue (mutually inconsistent)
- **No fix until one hypothesis reaches VERIFIED**
- **Fix budget:** ≤15 lines AND ≤1 function (both must hold)
- **Max 3 analysis iterations** before requiring human input
- **Every fix must include a regression test**
- **Backend-first, then Frontend:** If a bug could originate in either layer, start with the backend (API + business logic) and only move to the frontend (UI + state management) after the backend is ruled out.

---

# PART A — BACKEND DEBUGGING (`src/reasoner/`)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.12+ |
| Web Framework | FastAPI 0.109+ |
| HTTP Client | httpx |
| ORM | SQLAlchemy 2 async |
| Cache / Sessions | Redis (optional) |
| Testing | pytest, pytest-asyncio, pytest-timeout |
| Linting | ruff |

## Test Configuration (`pytest.ini`)

```ini
testpaths = tests
pythonpath = src
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    timeout: marks tests with a timeout threshold
```

> **Critical:** All async fixtures share a single event loop for the entire test session because the project uses in-memory singletons (rate limiter, circuit breaker, auth store) that persist across tests.

## Commands

```bash
# Run all tests
python -m pytest -v

# Skip slow tests
python -m pytest -m "not slow"

# Include slow tests
python -m pytest --run-slow

# Run specific test file(s)
python -m pytest test_parsing.py test_models.py

# Run with coverage
python -m pytest tests/ --cov=src/reasoner --cov-report=html

# Linting
ruff check src/reasoner/
ruff format src/reasoner/

# Start API server for manual testing
uvicorn asgi:app --reload --port 8003
```

## PHASE 0: INPUT VALIDATION (Backend)

Before any analysis, confirm you have:

| Required | Status |
|----------|--------|
| Error type (exception / wrong output / no output / behavioral / asyncio-related) | [present / missing] |
| Minimal reproduction steps or failing test | [present / missing] |
| Python version, pytest output, `pytest.ini` settings | [present / missing] |
| Is the failure reproducible with `-m "not slow"`? | [yes / no / untested] |

**Backend-specific checks:**
- Is this an `asyncio`/`await` issue (e.g., `RuntimeError: cannot be called from a running event loop`)?
- Is this a database/connection pool issue (e.g., `asyncpg.exceptions.InterfaceError: connection is closed`)?
- Is this a Redis/cache singleton issue (e.g., stale state across tests)?
- Is this a circuit breaker / rate limiter issue (e.g., fail-open vs fail-closed)?
- Is this a Pydantic v2 validation error?
- Is this a CSRF/auth scope issue?

If required inputs are missing, request them. Do not proceed with incomplete information.

## PHASE 1: SYSTEM MAPPING (Backend)

Trace from entry points to the failure locus:

- **Entry point:**
  - CLI: `python main.py ...`
  - API: FastAPI route in `src/reasoner/api/routes/`
  - Test: `tests/test_*.py`
  - Internal: Pipeline/mixin/phase call
- **Critical path:** Step-by-step execution flow to the failure
- **State variables:** What mutable state exists along this path?
  - In-memory singletons (rate limiter, circuit breaker, auth store)
  - Redis state (if `RATE_LIMITER_MODE=redis`)
  - PostgreSQL connection pool (`DB_POOL_SIZE`)
  - Token cache (`clear_token_cache` fixture clears this)
- **Failure locus:** Precise location (function, file, line)

**Backend-specific state hazards:**
- Singletons persist across tests due to `asyncio_default_fixture_loop_scope = session`
- `extract_json()` is called in ~80 locations — a bug there affects many mixins
- `TRUNCATION` is a dataclass — subscripting it (`TRUNCATION["problem"]`) raises TypeError

## PHASE 2: HYPOTHESIS GENERATION (Backend)

Generate ≥2 competing root cause hypotheses. They must be mutually inconsistent.

For each hypothesis:

```
H[N]: [mechanism — how this causes the failure]
  Evidence for: [list specific code references]
  Evidence against: [mandatory self-refutation]
  Confidence: Low / Medium / High
  Testability: Easy / Hard / Infeasible
  Priority: [order by testability]
```

**Backend-specific hypothesis categories:**
1. **Async/Concurrency:** `CancelledError` not re-raised, `gather()` without `return_exceptions=True`, semaphore exhaustion
2. **Type Safety:** `extract_json()` returning `str`/`list` instead of `dict`, dataclass subscripting
3. **State Leakage:** Singleton not cleared between tests, stale token cache
4. **Infrastructure:** LLM timeout, OpenRouter connection error, SearXNG circuit breaker
5. **Auth/Security:** CSRF secret mismatch, tier check bypass, rate limiter fail-open
6. **Database:** Pool exhaustion, connection not returned to pool, migration mismatch

## PHASE 3: TEST DESIGN (Backend)

For each hypothesis, design two tests:

### Detection Test
Proves the bug EXISTS under this hypothesis.
- Must be executable with `python -m pytest -v`
- Must fail if hypothesis is correct
- If no executable detection test can be written → mark hypothesis as UNKNOWN

**Backend-specific detection patterns:**
```python
# Async bug detection
import asyncio
import pytest

@pytest.mark.asyncio
async def test_cancelled_error_not_poisoning_circuit_breaker():
    circuit = CircuitBreaker()
    with pytest.raises(asyncio.CancelledError):
        await _call_with_circuit_breaker(circuit, ...)
    assert circuit.state == "CLOSED"  # Should NOT flip to OPEN

# Type bug detection
from reasoner.parsing import extract_json, ParseError

def test_extract_json_rejects_non_dict():
    with pytest.raises(ParseError):
        extract_json('["array"]')
```

### Falsification Attempt
Tries to BREAK the hypothesis mechanism.
- Can you construct a valid execution where the failure occurs WITHOUT this hypothesis's proposed cause?
- If yes → reduce confidence

## PHASE 4: ELIMINATION (Backend)

Evaluate all hypotheses:

| Hypothesis | Detection Result | Falsification Result | Status |
|------------|-----------------|---------------------|--------|
| H1 | [test outcome] | [attempt outcome] | VERIFIED / HYPOTHESIS / FALSE |
| H2 | [test outcome] | [attempt outcome] | VERIFIED / HYPOTHESIS / FALSE |

**Resolution:**
- ≥1 VERIFIED → proceed to PHASE 5
- All HYPOTHESIS → return to PHASE 3
- All FALSE → return to PHASE 2
- If iteration 3 with no VERIFIED → ABORT

## PHASE 5: FIX DESIGN (Backend)

ONLY activate for a VERIFIED hypothesis.

**Constraints:**
- ≤15 lines changed
- ≤1 function modified
- Fix must be causally linked to the verified mechanism

**Backend-specific fix patterns:**
```python
# Async: Re-raise CancelledError before circuit breaker records failure
except asyncio.CancelledError:
    raise  # Don't poison circuit breaker

# Concurrency: Add return_exceptions=True to gather
results = await asyncio.gather(*tasks, return_exceptions=True)
results = [r for r in results if not isinstance(r, Exception)]

# Type safety: Guard non-dict JSON returns
parsed = safe_json_loads(text)
if isinstance(parsed, dict):
    return parsed
# fall through to fallback or raise ParseError

# Dataclass: Use dot notation, not subscripting
problem = state.problem[:TRUNCATION.PROBLEM]  # NOT TRUNCATION["problem"]
```

**Output:**
- **Diff:** [minimal unified diff]
- **Causal justification:** "The verified mechanism is [X]. This fix breaks that mechanism by [Y]."
- **Risk assessment:**
  - Scope: LOCAL / MODULE / SYSTEM
  - Side effects: [list or NONE]
  - Regression risk: LOW / MEDIUM / HIGH

## PHASE 6: SELF-REVIEW (Backend)

Answer honestly:

1. **Boundary attack:** Empty strings, `None`, max token budgets, empty lists?
2. **Invalid input attack:** Malformed JSON, wrong Pydantic model, `None` where `dict` expected?
3. **State attack:** Singleton corrupt, Redis unavailable, DB pool exhausted?
4. **Regression check:** Would `extract_json()` callers break? Would async event loop behavior change?
5. **Concurrency check:** Two simultaneous requests hitting rate limiter / circuit breaker / token cache?

For each: FIX HOLDS / FIX BREAKS / CANNOT DETERMINE

If FIX BREAKS, revise once. Second break → REQUIRES HUMAN REVIEW.

## PHASE 7: REGRESSION TEST (Backend)

Generate a test that:
- Reproduces the original bug (fails without the fix)
- Passes with the fix applied
- Uses pytest with `pytest-asyncio` when async code is involved
- Includes edge cases from Phase 6

**Placement:**
- Add to `tests/test_bugfixes_regression_round[N].py` for bugfix regression suites
- Add to `tests/test_parsing.py`, `tests/test_router.py`, etc. for module-specific tests
- Follow existing test style in the file

**Example:**
```python
# tests/test_bugfixes_regression_round3.py
import asyncio
import pytest
from reasoner.infrastructure.llm.router import ProviderRouter

class TestRouterCircuitBreakerCancelledError:
    @pytest.mark.asyncio
    async def test_cancelled_error_not_counted_as_failure(self):
        """CancelledError should NOT poison the circuit breaker."""
        router = ProviderRouter()
        circuit = router._get_circuit("test-provider")
        # Simulate a task cancellation during a provider call
        async def cancelled_call():
            raise asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await router._call_with_circuit(cancelled_call, circuit, timeout=10)
        assert circuit.failure_count == 0
```

## PHASE 8: VERDICT (Backend)

| Check | Status |
|-------|--------|
| Exactly one VERIFIED hypothesis | ✅ / ❌ |
| Fix is ≤15 lines AND ≤1 function | ✅ / ❌ |
| All self-review attacks → FIX HOLDS | ✅ / ❌ |
| Regression test included | ✅ / ❌ |
| Regression risk is LOW or MEDIUM | ✅ / ❌ |

**Decision:**
- All ✅ → ACCEPT
- Any ❌ → RE-ITERATE or ABORT

---

# PART B — FRONTEND DEBUGGING (`ui-next/`)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 16.2.3 (App Router) |
| Language | TypeScript 5 |
| UI | React 19.2.4 |
| Styling | Tailwind CSS v4 |
| State | Zustand v5 (client), SWR v2 (server) |
| Testing | Vitest v4, @testing-library/react, @playwright/test |
| Linting | ESLint 9 flat config |

## Test Configuration

### Vitest (`vitest.config.ts`)
- Environment: `jsdom`
- Globals: `true`
- Alias: `@/` → `./src`

### Playwright (`playwright.config.ts`)
- Test directory: `./e2e`
- Base URL: `http://localhost:3000`
- Browser: Chromium
- Web server auto-starts `npm run dev`

## Commands

```bash
cd ui-next

# Unit tests
npm run test        # (if configured in package.json)
npx vitest          # interactive
npx vitest run      # CI mode

# E2E tests
npx playwright test
npx playwright test --ui

# Linting
npm run lint

# Dev server
npm run dev

# Type checking
npx tsc --noEmit
```

## PHASE 0: INPUT VALIDATION (Frontend)

Before any analysis, confirm you have:

| Required | Status |
|----------|--------|
| Error type (runtime exception / render error / wrong UI state / API mismatch / hydration error) | [present / missing] |
| Browser console output / Next.js error overlay | [present / missing] |
| Steps to reproduce (click sequence, route, state) | [present / missing] |
| Is the bug in SSR, CSR, or both? | [SSR / CSR / both / unknown] |

**Frontend-specific checks:**
- Is this a **hydration mismatch** (`Warning: Text content does not match server-rendered HTML`)?
- Is this a **Zustand state leak** (persisted state corrupt across sessions)?
- Is this a **SWR cache issue** (stale data from server cache)?
- Is this a **Tailwind v4 class issue** (classes not applied due to CSS-native config)?
- Is this an **API proxy issue** (Next.js API route → FastAPI failure)?
- Is this an **IndexedDB (`idb`) issue** (async storage failure)?

## PHASE 1: SYSTEM MAPPING (Frontend)

Trace from entry points to the failure locus:

- **Entry point:**
  - Page route: `app/[route]/page.tsx`
  - API route: `app/api/[...]/route.ts`
  - Component: `components/[category]/[Name].tsx`
  - Hook: `hooks/use[Name].ts`
  - Store action: `stores/app-store.ts`
- **Critical path:**
  - User action → Event handler → API call → SWR/Zustand update → Re-render
  - Or: Server render → Hydration → Client state mismatch
- **State variables:**
  - Zustand store slices
  - SWR cached keys
  - React state (`useState`, `useReducer`)
  - URL/search params
  - IndexedDB (`idb`) persisted data
- **Failure locus:** Component, hook, API route, or store

**Frontend-specific state hazards:**
- Zustand persistence to IndexedDB can corrupt across schema changes
- SWR default cache strategy may show stale data
- Next.js App Router caches pages aggressively — check `revalidate` / `dynamic` export
- Tailwind v4 uses CSS-native config (`globals.css`) not `tailwind.config.js`

## PHASE 2: HYPOTHESIS GENERATION (Frontend)

Generate ≥2 competing root cause hypotheses.

**Frontend-specific hypothesis categories:**
1. **Hydration Mismatch:** Server-rendered HTML differs from client first render (common with `Date`, `Math.random`, localStorage)
2. **State Management:** Zustand store not updating, selector missing re-render, SWR key mismatch
3. **API Proxy Failure:** Next.js API route throws, FastAPI returns non-JSON, CORS error
4. **Async Timing:** Race condition between API call and component unmount
5. **Type Safety:** TypeScript compiles but runtime value doesn't match type (e.g., API response shape changed)
6. **Build/Config:** Tailwind v4 class missing, ESLint error blocking build, environment variable missing at build time

## PHASE 3: TEST DESIGN (Frontend)

### Detection Test
- Must be executable with Vitest or Playwright
- Must fail if hypothesis is correct

**Frontend-specific detection patterns:**
```typescript
// Vitest + React Testing Library
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import MyComponent from './MyComponent'

describe('MyComponent', () => {
  it('renders data from API', async () => {
    vi.mock('@/lib/api-client', () => ({
      fetchData: () => Promise.resolve({ items: [] })
    }))
    render(<MyComponent />)
    await waitFor(() => {
      expect(screen.getByText('Loaded')).toBeInTheDocument()
    })
  })
})

// Playwright E2E
import { test, expect } from '@playwright/test'

test('pipeline runs end-to-end', async ({ page }) => {
  await page.goto('/')
  await page.fill('[data-testid="problem-input"]', 'Test problem')
  await page.click('[data-testid="submit"]')
  await expect(page.locator('[data-testid="result"]')).toBeVisible({ timeout: 30000 })
})
```

### Falsification Attempt
- Can the bug occur without this component/hook/store being involved?
- Does the bug persist with JavaScript disabled (SSR-only)?
- Does clearing IndexedDB / SWR cache fix it?

## PHASE 4: ELIMINATION (Frontend)

Same table format as Backend.

## PHASE 5: FIX DESIGN (Frontend)

**Constraints:**
- ≤15 lines changed
- ≤1 function/component modified
- Fix must be causally linked to verified mechanism

**Frontend-specific fix patterns:**
```typescript
// Hydration: Guard client-only code
import { useEffect, useState } from 'react'
const [mounted, setMounted] = useState(false)
useEffect(() => setMounted(true), [])
if (!mounted) return <Skeleton />

// Zustand: Add schema validation or version migration
import { persist, createJSONStorage } from 'zustand/middleware'
persist(store, {
  name: 'app-store',
  version: 1,
  migrate: (persistedState: any, version) => {
    if (version === 0) return { ...persistedState, newField: 'default' }
    return persistedState
  }
})

// API route: Defensive response parsing
export async function POST(req: Request) {
  const data = await req.json()
  if (!data || typeof data !== 'object') {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 })
  }
  // ...
}

// Tailwind v4: Use CSS-native config in globals.css
@import "tailwindcss";
@theme {
  --color-primary: #3b82f6;
}
```

## PHASE 6: SELF-REVIEW (Frontend)

1. **Boundary attack:** Empty API response, `null` data, 0 items, loading state?
2. **Invalid input attack:** Malformed API response, `undefined` props, wrong type?
3. **State attack:** IndexedDB corrupt, Zustand hydration mismatch, SWR cache stale?
4. **Regression check:** Would other pages/components using the same hook/store break?
5. **Concurrency check:** Rapid user clicks causing duplicate API calls / race conditions?

## PHASE 7: REGRESSION TEST (Frontend)

- **Unit:** Add `.test.ts` or `.test.tsx` next to the source file (co-located)
- **E2E:** Add to `ui-next/e2e/` for critical user flows

```typescript
// hooks/usePipelineStream.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { usePipelineStream } from './usePipelineStream'

describe('usePipelineStream', () => {
  it('handles API error gracefully', async () => {
    vi.mock('@/lib/api-client', () => ({
      streamPipeline: () => { throw new Error('Network error') }
    }))
    const { result } = renderHook(() => usePipelineStream())
    await waitFor(() => {
      expect(result.current.error).toBeDefined()
    })
  })
})
```

## PHASE 8: VERDICT (Frontend)

Same checklist as Backend.

---

# PART C — CROSS-LAYER DEBUGGING (Backend ↔ Frontend)

When a bug could involve both layers, follow this order:

1. **Reproduce with backend directly:** Use `python main.py --preset ... --problem "..."` or `curl` against FastAPI.
2. **Check API response shape:** Does FastAPI return what the frontend expects? (Pydantic schema vs TypeScript type)
3. **Check Next.js API route:** Does the proxy route (`app/api/[...]/route.ts`) transform/mangle the response?
4. **Check frontend consumption:** Does the component/hook correctly handle the actual response shape?

**Common cross-layer mismatches:**
- FastAPI returns `snake_case`, frontend expects `camelCase`
- FastAPI returns `null`, frontend type says `string`
- FastAPI stream uses SSE, frontend expects JSON
- CSRF token missing in frontend request → FastAPI rejects with 403

---

# OUTPUT FORMAT

Structure your response as a single Markdown document:

```
# Debugging Analysis — [Error Summary]

## Layer: [Backend / Frontend / Cross-layer]

## Phase 0: Input Validation
[table of required inputs + status]

## Phase 1: System Map
- Entry point:
- Critical path:
- State variables:
- Failure locus:

## Phase 2: Hypotheses
### H1: [mechanism]
[evidence for, evidence against, confidence, testability, priority]

### H2: [mechanism]
[...]

## Phase 3: Test Design
### H1 Tests
- Detection test:
- Falsification attempt:
- Net verdict:

### H2 Tests
[...]

## Phase 4: Elimination
[table + resolution + routing decision]

## Phase 5: Fix
[only if VERIFIED — diff + causal justification + risk assessment]

## Phase 6: Self-Review
[5 questions + answers + overall assessment]

## Phase 7: Regression Test
[test code]

## Phase 8: Verdict
[checklist + ACCEPT / RE-ITERATE / ABORT]
```

## UNCERTAINTY ACKNOWLEDGMENT

End every response with:
1. **Claim most likely to be wrong:**
2. **What requires runtime validation:**
3. **What static analysis cannot determine:**
4. **What additional input would increase confidence:**

If you cannot reach VERIFIED within 3 iterations, state so explicitly and provide your best current hypothesis with recommended next steps for a human developer.
