# Feedback System Enhancement — Implementation Plan

## 1. Executive Summary

This plan implements a 4-phase upgrade to the existing feedback system, moving it from a silent JSONL dump to a structured, queryable, admin-visible, and user-actionable feedback loop. Each phase is independently shippable and gated behind feature flags.

**Current state:**
- UI shows thumbs-up/down buttons (feature-flagged via `feedback-loop`)
- Only `rating` is sent; `reason` and `comment` fields exist in schema but are always `null`
- Backend appends JSONL lines to `feedback/feedback.jsonl`
- No admin visibility, no user follow-up, no analytics

**Target state:**
- Down-vote reveals a reason dropdown + optional comment (Phase 1)
- Each feedback entry captures lightweight message context (Phase 2)
- Persistent SQLite storage with admin stats dashboard endpoint (Phase 3)
- Down-voted messages offer a "Regenerate" action to the user (Phase 4)

---

## 2. Architecture Principles

1. **Backward compatibility:** Existing JSONL file remains readable; no data loss on migration.
2. **Minimal footprint:** Reuse existing SQLite patterns (`EventStore` style), feature-flag system, and API proxy conventions.
3. **Async-safe DB:** Follow the `threading.Lock` + `ThreadPoolExecutor(max_workers=1)` pattern already used in `event_store.py`.
4. **Admin-only stats:** Stats endpoint requires `X-Admin-Key` header matching `Settings.ADMIN_API_KEY`.
5. **Type safety:** Update `FeedbackRequest`, `submitFeedback`, `ChatFeedProps`, and `ChatFeedMessage` types together.

---

## 3. Phase 1 — Reason Dropdown (Frontend-Heavy)

**Goal:** When a user clicks thumbs-down, present a small inline form to collect a reason and optional free-text comment before submitting.

### 3.1 Files Changed

| File | Change |
|------|--------|
| `ui-next/src/hooks/useFeatureFlags.ts` | Add `feedback-reason-dropdown: false` to `DEFAULT_FEATURES` |
| `ui-next/src/components/chat/ChatFeed.tsx` | Replace instant `handleFeedback` with a two-step flow for down-votes; add inline `<select>` + `<textarea>` |
| `ui-next/src/lib/api-client.ts` | No change — `submitFeedback` already accepts `reason` and `comment` |
| `ui-next/src/app/page.tsx` | Update `handleFeedback` signature to accept optional `reason` and `comment` |

### 3.2 UI/UX Specification

**Happy path (up-vote):**
1. User clicks thumbs-up → button turns green immediately → `submitFeedback({rating:'up'})` fires → button stays disabled.

**Down-vote flow:**
1. User clicks thumbs-down → inline panel appears below the message action bar (no modal, no toast).
2. Panel contains:
   - `<select>` with options: `incorrect`, `outdated`, `off_topic`, `too_verbose`, `unsafe`, `other`
   - Optional `<textarea>` placeholder: "What could be improved?"
   - "Submit" button (primary) + "Cancel" button (ghost)
3. On Submit: call `submitFeedback({rating:'down', reason, comment})`, then collapse panel and turn thumbs-down red.
4. On Cancel: collapse panel, re-enable both buttons.

**Accessibility:**
- Use `<label htmlFor="...">` for the select.
- Escape key collapses the panel.
- Focus trap not required (panel is tiny and inline).

### 3.3 State Model

```typescript
// ChatFeed.tsx — local state per message (inside MessageActions)
const [feedbackPanelOpen, setFeedbackPanelOpen] = useState(false);
const [selectedReason, setSelectedReason] = useState('');
const [commentText, setCommentText] = useState('');
```

### 3.4 API Contract

No backend changes required in Phase 1. `FeedbackRequest` already supports `reason` and `comment`.

---

## 4. Phase 2 — Lightweight Context Attachment

**Goal:** Attach a small, privacy-respecting context snapshot to every feedback entry so admins can understand *what* was disliked without exposing full conversation history.

### 4.1 Context Payload Schema

```typescript
interface FeedbackContext {
  // Message metadata (no PII)
  message_length: number;           // character count
  phase_count: number;              // how many phases rendered
  current_phase_name?: string;      // e.g. "Synthesis"
  model_aliases?: string[];         // models used in this message
  has_images: boolean;
  has_widgets: boolean;
  duration_ms?: number;
  token_count?: { input: number; output: number; total: number };
  cost_usd?: number;

  // Conversation metadata
  preset_used?: string;
  method_used?: string;
  message_index: number;            // 0-based position in conversation
}
```

### 4.2 Files Changed

| File | Change |
|------|--------|
| `src/reasoner/api/__init__.py` | Extend `FeedbackRequest` with `context: dict \| None = None`; write it to JSONL |
| `ui-next/src/lib/types.ts` | Export `FeedbackContext` interface |
| `ui-next/src/lib/api-client.ts` | `submitFeedback` accepts optional `context` field |
| `ui-next/src/app/page.tsx` | `handleFeedback` gathers context from the target message before sending |
| `ui-next/src/components/chat/ChatFeed.tsx` | Pass `message` object (or context subset) up through `onFeedback` |

### 4.3 Data Collection Rules

- **Never collect:** user prompt text, assistant response text, image base64 data, file names, conversation IDs beyond the existing `conversation_id`.
- **Only collect:** structural metadata already present in `ChatFeedMessage` (token counts, phase names, model list, booleans).
- **Size budget:** JSON stringified context < 2 KB.

### 4.4 Page.tsx Integration

```typescript
function buildFeedbackContext(message: ChatFeedMessage, index: number): FeedbackContext {
  return {
    message_length: message.content.length,
    phase_count: message.phases?.length ?? 0,
    current_phase_name: message.currentPhaseName,
    model_aliases: message.phaseModels,
    has_images: !!message.images?.length,
    has_widgets: !!message.widgets?.length,
    duration_ms: message.duration,
    token_count: message.tokens,
    cost_usd: message.cost,
    preset_used: currentPreset,   // from page-level state
    method_used: currentMethod,   // from page-level state
    message_index: index,
  };
}
```

---

## 5. Phase 3 — SQLite Migration + Stats Endpoint

**Goal:** Replace JSONL with SQLite for durability and queryability; expose an admin-protected stats endpoint.

### 5.1 Database Design

**Table:** `feedback_entries`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | — |
| `timestamp` | `TEXT NOT NULL DEFAULT (datetime('now'))` | ISO-8601 UTC |
| `conversation_id` | `TEXT NOT NULL` | indexed |
| `message_id` | `TEXT NOT NULL` | indexed |
| `rating` | `TEXT NOT NULL` | `CHECK(rating IN ('up','down'))` |
| `reason` | `TEXT` | nullable |
| `comment` | `TEXT` | nullable |
| `context_json` | `TEXT` | nullable — JSON string |

**Indexes:**
```sql
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback_entries(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_reason ON feedback_entries(reason);
CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback_entries(timestamp);
```

### 5.2 New Module: `src/reasoner/infrastructure/persistence/feedback_store.py`

Follows the exact patterns from `event_store.py`:

```python
class FeedbackStore:
    def __init__(self, db_path: str | Path | None = None):
        ...

    def _init_db(self) -> None:
        ...

    async def insert(self, entry: FeedbackEntry) -> int:
        """Returns inserted row id."""
        ...

    async def get_stats(self, days: int = 30) -> FeedbackStats:
        """Aggregated stats for the last N days."""
        ...

    async def get_entries(self, limit: int = 100, offset: int = 0) -> list[FeedbackEntry]:
        ...
```

**Migration path:**
- On first import, if `feedback/feedback.jsonl` exists and `feedback_entries` table is empty, backfill from JSONL.
- After successful backfill, rename `feedback.jsonl` → `feedback.jsonl.migrated` (never delete).

### 5.3 FastAPI Endpoints

```python
# Existing — updated to use FeedbackStore
@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    row_id = await feedback_store.insert(...)
    return {"status": "received", "id": row_id}

# New — admin only
@app.get("/api/admin/feedback-stats")
async def feedback_stats(
    days: int = Query(30, ge=1, le=365),
    admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if not admin_key or admin_key != Settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await feedback_store.get_stats(days=days)
```

### 5.4 Files Changed

| File | Change |
|------|--------|
| `src/reasoner/infrastructure/persistence/feedback_store.py` | **New** — SQLite store with migration logic |
| `src/reasoner/api/__init__.py` | Replace JSONL logic with `FeedbackStore`; add admin stats endpoint |
| `src/reasoner/core/settings.py` | No change — `ADMIN_API_KEY` already exists |
| `tests/test_feedback.py` | **New** — unit tests for store + endpoint (see §7) |

---

## 6. Phase 4 — User-Facing Rerun Action

**Goal:** After a down-vote is submitted, show a "Regenerate response" button that re-runs the last user prompt with identical parameters.

### 6.1 UX Specification

1. Down-vote panel (from Phase 1) now shows an additional checkbox: "Include my feedback in the regeneration" (default unchecked).
2. After submitting the down-vote, the message action bar shows a subtle "Regenerate ↻" button next to the red thumbs-down.
3. Clicking it:
   - Re-sends the original user prompt through the pipeline
   - Optionally appends a system hint: `User feedback: [reason] — [comment]` (if checkbox was checked)
   - Replaces the down-voted assistant message with a fresh streaming response (or appends a new one — decision needed, see §8)

### 6.2 State Requirements

The page-level state must remember, per message:
- The original user prompt that generated this assistant response
- The preset / method / source-type settings at generation time

**Approach:** Store `generationParams` on `ChatFeedMessage` when the assistant message is first created:

```typescript
interface ChatFeedMessage {
  // ... existing fields ...
  generationParams?: {
    prompt: string;
    preset: string;
    method: string;
    sourceType: string;
    topK: number;
    includeFeedback?: boolean;
  };
}
```

### 6.3 Files Changed

| File | Change |
|------|--------|
| `ui-next/src/hooks/useFeatureFlags.ts` | Add `feedback-rerun: false` to `DEFAULT_FEATURES` |
| `ui-next/src/lib/types.ts` | Add `GenerationParams` interface |
| `ui-next/src/app/page.tsx` | Persist `generationParams` when assistant message is created; implement `handleRegenerate(messageId)` |
| `ui-next/src/components/chat/ChatFeed.tsx` | Show "Regenerate" button on down-voted messages; pass `onRegenerate` prop |
| `src/reasoner/api/__init__.py` | Optional: accept `user_feedback_hint` in `RunRequest` and prepend to system prompt (if we want backend-side injection) |

### 6.4 Open Decision

**Replacement vs. Append:**
- **Replace:** The down-voted message is removed from the array and replaced by the new streaming message. Simpler UX, but loses history.
- **Append:** A new assistant message is appended. The old down-voted message remains visible with its red thumb. More honest, but clutters the feed.

**Recommendation:** Replace. Set `message.isReplacing = true` and animate it out, then stream the new response into the same slot. The conversation array index stays stable.

---

## 7. Testing Strategy

### 7.1 Backend Tests (`tests/test_feedback.py`)

```python
class TestFeedbackStore:
    def test_init_creates_schema(self, tmp_path):
        ...

    def test_insert_and_retrieve(self, tmp_path):
        ...

    def test_jsonl_migration(self, tmp_path):
        """Write sample JSONL, init store, assert backfill, assert renamed file."""
        ...

    def test_stats_aggregation(self, tmp_path):
        ...

class TestFeedbackEndpoint:
    def test_submit_feedback(self, client):
        ...

    def test_admin_stats_unauthorized(self, client):
        ...

    def test_admin_stats_authorized(self, client, monkeypatch):
        monkeypatch.setattr(Settings, "ADMIN_API_KEY", "test-admin-key")
        ...
```

### 7.2 Frontend Tests

| Test | Scope |
|------|-------|
| `ChatFeed` — down-vote opens reason panel | Component (Vitest) |
| `ChatFeed` — up-vote submits immediately | Component (Vitest) |
| `ChatFeed` — cancel closes panel without submit | Component (Vitest) |
| `page.tsx` — `handleFeedback` builds correct context | Integration (Vitest) |
| `page.tsx` — `handleRegenerate` reuses generation params | Integration (Vitest) |
| Feature flags — `feedback-reason-dropdown` gates Phase 1 UI | Unit |
| Feature flags — `feedback-rerun` gates Phase 4 UI | Unit |

---

## 8. Feature Flags & Rollout

| Flag | Phase | Default |
|------|-------|---------|
| `feedback-loop` | existing | `true` |
| `feedback-reason-dropdown` | 1 | `false` |
| `feedback-context-attachment` | 2 | `false` |
| `feedback-sqlite-stats` | 3 | `false` |
| `feedback-rerun` | 4 | `false` |

**Rollout order:**
1. Enable `feedback-reason-dropdown` for internal team → fix any UX friction → enable globally.
2. Enable `feedback-context-attachment` (safe, no user-visible change beyond payload size).
3. Enable `feedback-sqlite-stats` (backend-only, admin endpoint).
4. Enable `feedback-rerun` (highest user impact, validate replacement animation first).

---

## 9. Implementation Order (File-by-File)

This is the **recommended execution sequence** to minimize merge conflicts and broken states:

### Milestone A — Phase 1 Skeleton (no backend changes)
1. `ui-next/src/hooks/useFeatureFlags.ts` — add `feedback-reason-dropdown`
2. `ui-next/src/lib/types.ts` — add `FeedbackContext` and `GenerationParams` (forward-declare for Phase 2/4)
3. `ui-next/src/components/chat/ChatFeed.tsx` — two-step down-vote UI
4. `ui-next/src/app/page.tsx` — update `handleFeedback` signature, wire new UI
5. Run `npm run build` and `vitest run` to verify.

### Milestone B — Phase 2 Context
6. `ui-next/src/lib/api-client.ts` — extend `submitFeedback` payload type with `context`
7. `ui-next/src/app/page.tsx` — implement `buildFeedbackContext`, pass into `submitFeedback`
8. `src/reasoner/api/__init__.py` — add `context: dict | None = None` to `FeedbackRequest`, persist in JSONL
9. Verify JSONL output contains `context` field.

### Milestone C — Phase 3 SQLite + Stats
10. `src/reasoner/infrastructure/persistence/feedback_store.py` — new module
11. `src/reasoner/api/__init__.py` — replace JSONL with `FeedbackStore`, add `/api/admin/feedback-stats`
12. `tests/test_feedback.py` — new test file
13. Run `python -m pytest tests/test_feedback.py -v`

### Milestone D — Phase 4 Rerun
14. `ui-next/src/hooks/useFeatureFlags.ts` — add `feedback-rerun`
15. `ui-next/src/app/page.tsx` — store `generationParams` on assistant messages, implement `handleRegenerate`
16. `ui-next/src/components/chat/ChatFeed.tsx` — show Regenerate button when `feedbackGiven === 'down'`
17. Full integration test: down-vote → submit → click regenerate → new stream replaces old message.

---

## 10. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| JSONL migration fails silently on corrupt lines | Low | Wrap `json.loads` in try/except; skip bad lines and log count. |
| SQLite DB locked under concurrent feedback submissions | Low | Use `ThreadPoolExecutor(max_workers=1)` + `threading.Lock` exactly as `EventStore` does. |
| Context payload grows too large | Low | Enforce 2 KB max; truncate `comment` to 500 chars; omit `model_aliases` if > 10. |
| Regenerate replaces wrong message index | Medium | Use `messageIndexRef` (existing O(1) lookup) to find the exact slot; never use `.find()`. |
| Admin key leaked in frontend | Very Low | Stats endpoint is GET-only; admin key is **never** referenced in frontend code. |
| Feature-flag state drift between tabs | Low | Flags are read from `localStorage` on every `isEnabled()` call; no caching layer. |

---

## 11. Success Criteria

- [ ] Down-vote opens inline reason form; up-vote submits instantly.
- [ ] Every feedback entry in SQLite contains `reason`, `comment`, and `context_json`.
- [ ] Admin `GET /api/admin/feedback-stats` returns correct aggregates only with valid `X-Admin-Key`.
- [ ] Regenerate button appears after down-vote; click re-runs pipeline and replaces the old message.
- [ ] All new backend tests pass; `npm run build` succeeds; no TypeScript errors introduced.
- [ ] Existing JSONL file is backfilled and renamed, not deleted.
