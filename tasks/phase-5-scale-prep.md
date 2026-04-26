# Phase 5 — Scale Prep & Polish

> **Duration:** Week 6 (Days 39–42)  
> **Risk:** Low — mostly config, pagination, and cleanup  
> **Goal:** Prepare for horizontal scaling and close remaining hygiene gaps.

**Prerequisite:** Phase 4 merged and green. Can run parallel to late Phase 4 after Week 5.

---

## 5.1 Frontend Data Layer

### 5.1.1 IndexedDB Pagination
**Effort:** 3 hours  
**File:** `ui-next/src/lib/db.ts`

```typescript
const PAGE_SIZE = 50;

export interface ConversationPage {
  items: Conversation[];
  nextCursor?: IDBValidKey;
}

export async function loadConversationsPage(
  cursor?: IDBValidKey,
  direction: 'prev' = 'prev'
): Promise<ConversationPage> {
  const db = await getDB();
  const tx = db.transaction(STORE_NAME, 'readonly');
  const store = tx.objectStore(STORE_NAME);
  const index = store.index('timestamp');
  const results: Conversation[] = [];

  await new Promise<void>((resolve, reject) => {
    const req = cursor
      ? index.openCursor(cursor, direction)
      : index.openCursor(null, direction);
    req.onsuccess = (e) => {
      const cursor = (e.target as IDBRequest).result;
      if (!cursor || results.length >= PAGE_SIZE) {
        resolve();
        return;
      }
      results.push(cursor.value);
      cursor.continue();
    };
    req.onerror = () => reject(req.error);
  });

  return { items: results };
}
```

Update `useConversationHistory.ts`:
```typescript
const [page, setPage] = useState<ConversationPage | null>(null);
const [loadingMore, setLoadingMore] = useState(false);

useEffect(() => {
  loadConversationsPage().then(setPage).catch(console.error);
}, []);

const loadMore = async () => {
  if (!page?.nextCursor || loadingMore) return;
  setLoadingMore(true);
  const next = await loadConversationsPage(page.nextCursor);
  setPage(prev => prev ? { items: [...prev.items, ...next.items], nextCursor: next.nextCursor } : next);
  setLoadingMore(false);
};
```

**AC:** 1,000 mock conversations → first page loads in <100ms; no UI freeze.

---

### 5.1.2 Widget API Client-Side Caching
**Effort:** 1 hour  
**File:** `ui-next/src/lib/api-client.ts`

```typescript
const cache = new Map<string, { data: any; expiry: number }>();
const TTL_MS = 30_000;

function withCache<T>(fn: (...args: any[]) => Promise<T>, keyFn: (...args: any[]) => string) {
  return async (...args: any[]): Promise<T> => {
    const key = keyFn(...args);
    const cached = cache.get(key);
    if (cached && cached.expiry > Date.now()) {
      return cached.data;
    }
    const data = await fn(...args);
    cache.set(key, { data, expiry: Date.now() + TTL_MS });
    return data;
  };
}

export const fetchWeather = withCache(
  _fetchWeather,
  (city: string) => `weather:${city}`
);
```

**AC:** Widget re-renders do not re-fetch identical data within 30s.

---

### 5.1.3 `dedupingInterval` for `usePresets`
**Effort:** 15 min  
**File:** `ui-next/src/hooks/usePresets.ts`

```typescript
const { data, error } = useSWR('/api/presets', fetcher, {
  refreshInterval: 30000,
  revalidateOnFocus: false,
  dedupingInterval: 2000,
});
```

**AC:** Rapid mount/unmount triggers only one network request.

---

## 5.2 Backend Config & Cleanup

### 5.2.1 `asyncpg` Pool Size Config
**Effort:** 30 min  
**File:** `src/reasoner/core/settings.py`

```python
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
```

Pass through to `asyncpg.create_pool(min_size=..., max_size=settings.DB_POOL_SIZE)`.

**AC:** Pool size respected; no connection exhaustion under load.

---

### 5.2.2 Dependency Lockfile
**Effort:** 1 hour  
**New file:** `requirements.lock`

```bash
pip install uv
uv pip compile requirements.txt -o requirements.lock
```

Update CI to install from lockfile:
```yaml
- run: uv pip install --system -r requirements.lock
```

**AC:** `requirements.lock` exists; CI installs from it; versions are pinned exactly.

---

### 5.2.3 Event Bus Queue `maxsize`
**Effort:** 30 min  
**File:** `src/reasoner/application/event_bus/bus.py`

```python
self._task_queue: asyncio.Queue | None = None
self._max_queue_size: int = 1000

# In start()
self._task_queue = asyncio.Queue(maxsize=self._max_queue_size)

# In publish()
try:
    self._task_queue.put_nowait((event, handler))
except asyncio.QueueFull:
    logger.error("Event bus queue full; dropping event %s", event.event_id)
```

**AC:** `test_event_bus_backpressure.py` — 1001 events → 1 dropped.

---

### 5.2.4 Code Cleanup
**Effort:** 2 hours  
**Scope:** Entire `src/reasoner/` and `ui-next/src/`

- Remove all commented-out code blocks > 10 lines.
- Ensure all `TODO` comments have linked issue numbers (e.g., `TODO(#123):`).
- Update `CHANGELOG.md` with all Phase 1–4 changes.

**AC:** `grep -r "TODO" src/ ui-next/src/` — every match has issue number or is in CHANGELOG.

---

## Testing Strategy

| Test File | Coverage |
|---|---|
| `test_indexeddb_pagination.py` | Cursor-based load, <100ms first page |
| `test_widget_cache.py` | TTL hit/miss, re-render no refetch |
| `test_event_bus_backpressure.py` | QueueFull, drop behavior |
| `test_db_pool_size.py` | Pool size env var respected |

---

## Definition of Done

- [ ] IndexedDB pagination loads 1,000 conversations without UI freeze.
- [ ] Widget cache prevents redundant fetches.
- [ ] `requirements.lock` pinned and CI uses it.
- [ ] Event bus queue bounded at 1000.
- [ ] Zero orphaned TODO comments.
- [ ] `cd ui-next && npm run build && npm run lint` pass.
