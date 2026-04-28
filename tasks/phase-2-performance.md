# Phase 2 — Performance Quick Wins

> **Duration:** Weeks 1–2 (Days 4–10)  
> **Risk:** Medium — isolated changes, easy rollback  
> **Goal:** Eliminate pathological latency, CPU waste, and render-path inefficiencies.

**Prerequisite:** Phase 1 merged and green.

---

## 2.1 Backend Streaming Fixes

### 2.1.1 Remove `asyncio.sleep(0.1)` from synthesis (TRACK 4.1)
**Effort:** 30 min  
**File:** `src/reasoner/api/streaming.py:636-647`

```python
# BEFORE
for i in range(0, len(words), chunk_size):
    chunk = " ".join(words[i:i + chunk_size])
    if i + chunk_size < len(words):
        chunk += " "
    yield _event({"type": "text_chunk", "text": chunk})
    await asyncio.sleep(0.1)

# AFTER
import re
sentences = re.split(r'(?<=[.!?])\s+', text)
for sentence in sentences:
    if cancel_event and cancel_event.is_set():
        break
    yield _event({"type": "text_chunk", "text": sentence})
```

**Impact:** 500-word synthesis latency drops from **~25s → <2s**.

**AC:** `test_synthesis_latency.py` — 500-word response streams in <2s.

---

### 2.1.2 Fix `_broadcast_ws` blocking + logging (TRACK 4.2)
**Effort:** 30 min  
**File:** `src/reasoner/api/streaming.py:87-98`

```python
# BEFORE
async def _broadcast_ws(run_id: str, payload: dict) -> None:
    try:
        await manager.broadcast_event(run_id, payload)
    except Exception:
        pass

# AFTER
async def _broadcast_ws(run_id: str, payload: dict) -> None:
    try:
        asyncio.create_task(manager.broadcast_event(run_id, payload))
    except Exception:
        logger.warning("WS broadcast failed for run %s", run_id, exc_info=True)
```

**AC:** WS slowdown no longer stalls SSE generator; exceptions logged.

---

### 2.1.3 BM25 Counter optimization (TRACK 4.3)
**Effort:** 30 min  
**File:** `src/reasoner/core/search.py:182-191`

```python
from collections import Counter

# BEFORE
for term in query_tokens:
    tf_title = title_tokens.count(term)
    tf_content = content_tokens.count(term)

# AFTER
title_counts = Counter(title_tokens)
content_counts = Counter(content_tokens)
for term in query_tokens:
    tf_title = title_counts.get(term, 0)
    tf_content = content_counts.get(term, 0)
```

**Impact:** Complexity drops from **O(|Q|×|T|) → O(|Q|+|T|)**.

**AC:** `pytest tests/test_search.py` passes.

---

## 2.2 Frontend Render-Path Fixes

### 2.2.1 Memoize `buildMarkdownFromPhase` (TRACK 4.4)
**Effort:** 30 min  
**File:** `ui-next/src/components/phases/PhaseRenderer.tsx`

```tsx
import { useMemo } from 'react';

export const PhaseRenderer = memo(function PhaseRenderer({ phase }) {
  const markdown = useMemo(
    () => buildMarkdownFromPhase(phase),
    [JSON.stringify(phase.data)]
  );
  // ... rest of render
});
```

**AC:** React DevTools Profiler shows `PhaseRenderer` does not re-render on every SSE tick.

---

### 2.2.2 Typewriter plain text during animation (TRACK 4.4)
**Effort:** 30 min  
**File:** `ui-next/src/components/chat/TypewriterMarkdown.tsx`

```tsx
// BEFORE — always renders MarkdownRenderer
return <MarkdownRenderer content={displayedText} />;

// AFTER — plain span during animation, MarkdownRenderer on completion
if (!isComplete) {
  return <span className="whitespace-pre-wrap">{displayedText}</span>;
}
return <MarkdownRenderer content={fullText} />;
```

**AC:** CPU usage in Chrome Performance tab drops during typewriter animation.

---

### 2.2.3 Eliminate `[...messages].reverse()` clone (TRACK 4.4)
**Effort:** 30 min  
**File:** `ui-next/src/app/page.tsx`

```tsx
const findLastAssistant = (msgs: Message[]) => {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant' && !msgs[i].isStreaming) return msgs[i];
  }
  return undefined;
};

// Replace both occurrences:
const lastAssistantMsg = useMemo(() => findLastAssistant(messages), [messages]);
```

**AC:** No new array allocations on every render.

---

### 2.2.4 Memoize `handleSubmit` / `handleStop` (TRACK 4.4)
**Effort:** 30 min  
**File:** `ui-next/src/app/page.tsx`

```tsx
const handleSubmit = useCallback(async () => {
  // ... existing logic
}, [dependencies]);

const handleStop = useCallback(() => {
  // ... existing logic
}, [dependencies]);
```

**AC:** React DevTools shows `Composer` and `Sidebar` do not re-render on unrelated state changes.

---

### 2.2.5 Memoize `CodeBlock` styles (TRACK 4.4)
**Effort:** 15 min  
**File:** `ui-next/src/components/chat/CodeBlock.tsx`

```tsx
const codeStyle = useMemo(() => (isDark ? vscDarkPlus : vs), [isDark]);
const customStyle = useMemo(() => ({ borderRadius: '0.5rem', fontSize: '0.875rem' }), []);
```

**AC:** `react-syntax-highlighter` does not re-compute highlight tree on parent re-renders.

---

### 2.2.6 Pause `useServerStatus` polling when hidden (TRACK 4.4)
**Effort:** 30 min  
**File:** `ui-next/src/hooks/useServerStatus.ts`

```typescript
useEffect(() => {
  let interval: NodeJS.Timeout;
  const start = () => { interval = setInterval(check, 10000); };
  const stop = () => clearInterval(interval);
  
  start();
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop(); else start();
  });
  return stop;
}, []);
```

**AC:** Chrome DevTools Network tab shows zero `/api/presets` requests while tab is backgrounded.

---

### 2.2.7 Add `dedupingInterval` to `usePresets` (TRACK 4.4)
**Effort:** 15 min  
**File:** `ui-next/src/hooks/usePresets.ts`

```typescript
const { data, error } = useSWR('/api/presets', fetcher, {
  refreshInterval: 30000,
  revalidateOnFocus: false,
  dedupingInterval: 2000,  // NEW
});
```

**AC:** Rapid mount/unmount triggers only one network request.

---

### 2.2.8 React Error Boundary (TRACK 4.5)
**Effort:** 1 hour  
**New file:** `ui-next/src/components/chat/ChatErrorBoundary.tsx`

```tsx
'use client';
import { Component, ReactNode } from 'react';

export class ChatErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error: Error) { console.error('Chat render error:', error); }
  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
```

**File:** `ui-next/src/app/page.tsx` — wrap `ChatFeed` and `PhaseRenderer`:

```tsx
<ChatErrorBoundary fallback={<div className="p-4 text-red-500">Display error. Please refresh.</div>}>
  <ChatFeed messages={messages} ... />
</ChatErrorBoundary>
```

**AC:** Intentional throw inside `PhaseRenderer` → page stays alive, fallback UI shown.

---

## 2.3 Search Quality Fixes (TRACK 4.6)

### 2.3.1 Filter-before-slice fallback
**File:** `src/reasoner/core/search.py:328-333`

```python
# BEFORE — returns empty if all filtered out
refined = [r for r in raw if _should_include_result(r)]
return refined, len(raw)

# AFTER
refined = [r for r in raw if _should_include_result(r)]
if not refined and raw:
    refined = raw[:num_results]  # fallback to unfiltered
return refined, len(raw)
```

**AC:** `test_search_fallback.py` — all results filtered out → returns top `num_results` unfiltered.

---

### 2.3.2 Guard `json.loads` in `_decompose_query`
**File:** `src/reasoner/core/search.py:552`

```python
# AFTER
try:
    arr = json.loads(text)
except json.JSONDecodeError:
    logger.warning("Decomposition JSON parse failed for query: %s", query)
    arr = []
```

**AC:** Malformed LLM output in decomposition → graceful fallback, no crash.

---

## 2.4 Article Writing Fixes (TRACK 4.7)

### 2.4.1 Deterministic writing router
**File:** `src/reasoner/application/mixins/article_pipeline.py` or new `hypergate/article_detector.py`

```python
_WRITING_INDICATORS = [
    r"\b(write|draft|compose|author|create)\b.*\b(article|essay|blog|report|paper|explainer)\b",
    r"\barticle\b.*\b(about|on)\b",
]

def is_article_request(problem: str) -> bool:
    lower = problem.lower()
    return any(re.search(p, lower) for p in _WRITING_INDICATORS)
```

Integrate into `ReasonerPipeline.run()` — if `is_article_request(state.problem)` → bypass generic classification, enter article workflow directly.

**AC:** Article request always enters writing workflow.

---

### 2.4.2 Safe follow-up scoping
**File:** `src/reasoner/application/mixins/article_pipeline.py`

```python
_REFERENTIAL_SIGNALS = ["continue", "expand", "revise that", "elaborate", "add more"]

def is_referential_followup(problem: str, history: list[Message]) -> bool:
    if not history:
        return False
    lower = problem.lower()
    return any(sig in lower for sig in _REFERENTIAL_SIGNALS)
```

Only inject previous context when `is_referential_followup()` returns `True`.

**AC:** Non-referential new request does not inherit prior context.

---

## 2.5 Scale Prep (TRACK 8 Partial)

### 2.5.1 Neuro HTTP connection pooling
**Effort:** 2 hours  
**New file:** `src/reasoner/api/clients.py`

```python
import httpx

_neuro_client: httpx.AsyncClient | None = None

def get_neuro_client() -> httpx.AsyncClient:
    global _neuro_client
    if _neuro_client is None:
        _neuro_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            timeout=httpx.Timeout(30.0)
        )
    return _neuro_client
```

Replace all `httpx.AsyncClient()` context managers in `streaming.py` with `get_neuro_client()`.

**AC:** 10 pipeline runs → stable TCP connection count to Neuro endpoint.

---

### 2.5.2 AuthManager LRU eviction
**File:** `src/reasoner/auth.py:89`

```python
from collections import OrderedDict

class AuthManager:
    _MAX_KEYS = 10_000

    def __init__(self):
        self._keys: OrderedDict[str, APIKey] = OrderedDict()

    def _set_key(self, key: str, value: APIKey) -> None:
        if key not in self._keys and len(self._keys) >= self._MAX_KEYS:
            self._keys.popitem(last=False)
        self._keys[key] = value
        self._keys.move_to_end(key)
```

**AC:** Unit test inserts 10,001 keys → oldest evicted.

---

### 2.5.3 RateLimiter lock sharding
**File:** `src/reasoner/rate_limiter.py`

```python
self._shard_count = 64
self._locks = [asyncio.Lock() for _ in range(self._shard_count)]

def _lock_for(self, key: str) -> asyncio.Lock:
    return self._locks[hash(key) % self._shard_count]
```

Feature flag: `ENABLE_SHARDED_LOCKS=true` env var.

**AC:** Load test P99 latency improvement vs single lock.

---

### 2.5.4 Remove PostgresEventStore global lock
**File:** `src/reasoner/infrastructure/persistence/postgres_store.py:211`

```python
# AFTER — remove self._lock, rely on asyncpg pool
async def save_events(self, events: list[DomainEvent]) -> None:
    conn = await self._pool.acquire()
    try:
        async with conn.transaction():
            for evt in events:
                await conn.execute(
                    "INSERT INTO events (...) VALUES (...) ON CONFLICT(event_id) DO NOTHING",
                    ...
                )
    finally:
        await self._pool.release(conn)
```

**AC:** 50 concurrent event writes succeed without serialization.

---

### 2.5.5 WebSocketManager lock sharding
**File:** `src/reasoner/infrastructure/websocket/manager.py`

Replace single lock with per-connection dictionary of locks:
```python
self._connection_locks: dict[str, asyncio.Lock] = {}

async def subscribe(self, websocket: WebSocket, pipeline_id: str, user: User):
    conn_id = id(websocket)
    lock = self._connection_locks.setdefault(conn_id, asyncio.Lock())
    async with lock:
        # ... subscription logic
```

Broadcasts iterate over a snapshot copy of `active_connections`.

**AC:** 1,000 simultaneous WS connect/disconnect without latency spikes.

---

### 2.5.6 Bound `pipeline_owners` JSON
**File:** `src/reasoner/api/history.py:25-34`

```python
_MAX_PIPELINE_OWNERS = 50_000

def _save_pipeline_owner(run_id: str, user_id: str) -> None:
    mapping = _get_pipeline_owner_map()
    mapping[run_id] = user_id
    if len(mapping) > _MAX_PIPELINE_OWNERS:
        # Evict oldest entries by insertion order
        while len(mapping) > _MAX_PIPELINE_OWNERS:
            mapping.pop(next(iter(mapping)))
    _PIPELINE_OWNERS_PATH.write_text(json.dumps(mapping), encoding="utf-8")
```

**AC:** 60,000 runs → oldest entries evicted; file size bounded.

---

## Testing Strategy

| Test File | Coverage |
|---|---|
| `test_synthesis_latency.py` | <2s for 500 words |
| `test_search_fallback.py` | Empty filter → unfiltered fallback |
| `test_decompose_json_guard.py` | Malformed JSON → graceful fallback |
| `test_article_router.py` | Writing prompts → article workflow |
| `test_article_followup_scoping.py` | Referential detection |
| `test_auth_manager_lru.py` | 10,001 keys → eviction |
| `test_rate_limiter_sharding.py` | Concurrent load, P99 latency |
| `test_postgres_event_store_concurrent.py` | 50 parallel writes |
| `test_websocket_manager_sharding.py` | 1,000 connections |

---

## Definition of Done

- [ ] Synthesis latency for 500-word response <2s.
- [ ] React DevTools shows no unnecessary re-renders for `PhaseRenderer`, `Composer`, `Sidebar`.
- [ ] Error Boundary catches synthetic throw without crashing page.
- [ ] `pytest -v` passes with ≥ baseline count.
- [ ] `cd ui-next && npm run build && npm run lint` pass.
