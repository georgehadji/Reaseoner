# ARA Next.js UI — Architecture Overview

This document describes the architecture of the production-grade Next.js frontend (`ui-next/`) that proxies to the existing FastAPI backend (`api.py`).

---

## 1. Authentication Flow

### Current State (Pass-Through Proxy)

The Next.js app acts as a **transparent frontend layer**. Authentication is currently handled by the FastAPI backend.

```
┌─────────────┐      (1) Request       ┌─────────────────┐
│   Browser   │ ───────────────────────>│   Next.js App   │
│  (ui-next)  │                         │  (App Router)   │
└─────────────┘                         └─────────────────┘
                                                │
                                                │ (2) Proxy
                                                ▼
                                       ┌─────────────────┐
                                       │   FastAPI       │
                                       │   (api.py)      │
                                       │  HTTPBearer     │
                                       └─────────────────┘
```

**How it works:**
- FastAPI's `api.py` uses `HTTPBearer(auto_error=False)` and an `auth_manager` to protect routes.
- The Next.js API route proxies forward the **original headers** (including `Authorization`) to the backend.
- No secrets are exposed to the client bundle. The backend URL lives in `.env.local` as `NEXT_PUBLIC_API_BASE_URL`.

### Production Extension Path

To add auth in the Next.js layer (e.g., for a public deployment):

1. **Middleware** (`middleware.ts`): Validate a session token or JWT at the edge.
2. **API Routes**: Inject an internal service token (from `process.env`) before proxying to FastAPI.
3. **Client**: Store a short-lived access token in `httpOnly` cookies, managed by Next.js API routes.

---

## 2. API Structure

### Next.js App Router Routes

| Route | File | Purpose |
|-------|------|---------|
| `GET /` | `app/page.tsx` | Main chat interface (static prerender) |
| `POST /api/run` | `app/api/run/route.ts` | Proxy SSE stream to FastAPI |
| `POST /api/stop` | `app/api/stop/route.ts` | Proxy stop command |
| `DELETE /api/cache` | `app/api/cache/route.ts` | Proxy cache clear |
| `GET /api/presets` | `app/api/presets/route.ts` | Proxy preset metadata |
| `GET /api/weather` | `app/api/weather/route.ts` | Proxy weather widget |
| `GET /api/stocks` | `app/api/stocks/route.ts` | Proxy stock widget |
| `POST /api/calculate` | `app/api/calculate/route.ts` | Proxy calculator widget |

All proxies use the same pattern:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
```

### Why Proxy Instead of Direct Fetch?

- **CORS elimination**: The browser talks to the same origin (`localhost:3000`).
- **Header injection**: You can add auth, rate-limiting, or logging in the Next.js layer later without touching the Python backend.
- **Secret isolation**: The FastAPI URL is a server-side env var.

---

## 3. Data Flow

### 3.1 High-Level Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser   │<--->│  Zustand     │<--->│  React UI       │
│             │     │  (app-store) │     │  Components     │
└─────────────┘     └──────────────┘     └─────────────────┘
        │                                              │
        │ (SSE Stream)                                 │ (CRUD)
        ▼                                              ▼
┌─────────────┐                              ┌─────────────────┐
│  usePipeline │                              │   IndexedDB     │
│  Stream      │                              │   (idb)         │
│  Hook        │                              │   ARA_Pipeline  │
└─────────────┘                              └─────────────────┘
        │                                              ▲
        │ Proxy POST /api/run                          │ load/save
        ▼                                              │
┌─────────────────┐                          ┌─────────────────┐
│   Next.js API   │                          │ useConversation │
│   Proxy         │                          │ History Hook    │
└─────────────────┘                          └─────────────────┘
        │
        ▼
┌─────────────────┐
│   FastAPI       │
│   /api/run      │
│   (SSE source)  │
└─────────────────┘
```

### 3.2 State Management Layers

#### A. Client State — Zustand (`stores/app-store.ts`)

**Responsibilities:**
- `running`: boolean — is a pipeline currently streaming?
- `method`: selected reasoning method (`multi-perspective`, `jury`, etc.)
- `presetIndex`, `isSequential`, `isExpert`, `sidebarCollapsed`
- `composerText`: controlled textarea value
- `activeRun`: transient run metadata (progressId, phases accumulated so far)

**Persistence:** Zustand is configured with `persist` middleware using `localStorage` for user preferences (method, preset index, toggles).

#### B. Server State — SWR (`hooks/usePresets.ts`)

**Responsibilities:**
- `usePresets()` fetches `/api/presets` with 60-second stale-while-revalidate.
- `useServerStatus()` pings `/api/presets` every 10 seconds to update the server status dot.

#### C. Browser Persistence — IndexedDB (`lib/db.ts`)

**Schema:**
- Database: `ARA_Pipeline`
- Store: `conversations` (keyPath: `id`)
- Records: `{ id, timestamp, problem, phases[], errors, preset, method, total_tokens }`

**Lifecycle:**
1. Pipeline finishes (`done` SSE event).
2. `page.tsx` constructs a `Conversation` object.
3. `saveConversation()` writes to IndexedDB.
4. `useConversationHistory` refreshes the sidebar list.

---

### 3.3 Streaming Data Flow (SSE)

The most complex data path is the **pipeline run**:

```typescript
// 1. User submits from Composer
handleSubmit() -> usePipelineStream.startRun(req, onEvent)

// 2. Hook opens fetch() to /api/run with ReadableStream
const reader = resp.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  buffer += decoder.decode(value, { stream: true });
  // Parse SSE lines: "data: {json}\n"
  const ev: PhaseEvent = JSON.parse(line.slice(6));
  onEvent(ev);
}

// 3. page.tsx onEvent dispatcher handles each event type:
//    - 'start' / 'cached' -> visual badge
//    - 'phase_start' -> progress card active step
//    - 'phase_complete' -> add PhaseDispatcher component to message list
//    - 'phase_error' -> mark step error
//    - 'cancelled' -> InfoCard
//    - 'done' -> ErrorCard (if errors), RunFooter, save to IndexedDB
```

**Abort/Stop Flow:**
- User presses `Esc` or clicks **Stop**.
- `stopRun()` aborts the `fetch()` via `AbortController` and sends `POST /api/stop` to the backend.
- The backend terminates the active pipeline run.

---

### 3.4 Component Rendering Flow

Messages are stored as a discriminated union in `page.tsx`:

```typescript
type MessageItem =
  | { type: 'problem'; text: string }
  | { type: 'progress'; id: string }
  | { type: 'phase'; id: string; phase: number; name: string; data: unknown }
  | { type: 'error'; id: string; errors: string[] }
  | { type: 'info'; id: string; messages: string[] }
  | { type: 'footer'; id: string; tokens: TokenCount };
```

Rendering in `page.tsx`:

```tsx
{messages.map((msg) => {
  if (msg.type === 'problem') return <ProblemBubble ... />;
  if (msg.type === 'progress') return <ProgressCard ... />;
  if (msg.type === 'phase') return <PhaseDispatcher phase={...} data={...} />;
  if (msg.type === 'error') return <ErrorCard ... />;
  if (msg.type === 'info') return <InfoCard ... />;
  if (msg.type === 'footer') return <RunFooter ... />;
})}
```

`PhaseDispatcher` maps `(method, phase, data)` to the correct renderer:
- `ClassificationRenderer`
- `DecompositionRenderer`
- `PerspectivesRenderer` / `ScoringRenderer` / `StressRenderer`
- `SynthesisRenderer`
- Method-specific variants: `SocraticRenderer`, `ScientificRenderer`, `DebateRenderer`, `JuryRenderer`

---

## 4. File-to-Responsibility Map

| Concern | Entry Point |
|---------|-------------|
| **App Shell** | `app/layout.tsx` |
| **Main Page** | `app/page.tsx` |
| **API Proxies** | `app/api/*/route.ts` |
| **Global State** | `stores/app-store.ts` |
| **SSE Stream** | `hooks/usePipelineStream.ts` |
| **Canvas Background** | `hooks/useLiquidCanvas.ts` + `components/canvas/LiquidCanvas.tsx` |
| **IndexedDB** | `lib/db.ts` |
| **Phase Rendering** | `components/phases/PhaseDispatcher.tsx` |
| **Config/Constants** | `lib/config.ts` |
| **Types** | `lib/types.ts` |

---

## 5. Security & Performance Notes

- **No server secrets leak to the client**: `API_BASE` is only used in API Route handlers or `next.config.ts` rewrites.
- **CSP-friendly**: No inline `eval()` or dangerous DOM operations; widgets use typed data props.
- **Reduced motion support**: `useLiquidCanvas` checks `prefers-reduced-motion` and skips animation.
- **Error boundaries**: Can be added at `app/error.tsx` to catch render crashes without white-screening the app.
