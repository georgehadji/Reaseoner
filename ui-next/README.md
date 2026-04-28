# Reasoner UI — Next.js Frontend

Production-grade Next.js 14+ (App Router) frontend for the Reasoner pipeline.

## Tech Stack

- **Framework:** Next.js 16 (App Router)
- **Language:** TypeScript (strict)
- **Styling:** Tailwind CSS + Reasoner CSS variable design system
- **State:** Zustand (client), SWR (server)
- **Browser DB:** IndexedDB via `idb`
- **Testing:** Vitest + React Testing Library + Playwright

## Project Structure

```
src/
  app/              # Next.js App Router pages & API route proxies
  components/       # React components (layout, phases, widgets, UI)
  hooks/            # Custom React hooks (SSE, canvas, keyboard, etc.)
  lib/              # Types, config, utils, API client, DB wrapper
  stores/           # Zustand stores
```

## Development

```bash
npm install
npm run dev
```

The dev server starts on `http://localhost:3000` by default.

## Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

This should point to the FastAPI backend (`api.py`).

## Build

```bash
npm run build
```

## Architecture Notes

- **API Proxies:** All `/api/*` routes are proxied to the FastAPI backend to avoid CORS and allow future auth middleware.
- **SSE Streaming:** The run endpoint streams Server-Sent Events via `fetch` + `ReadableStream` in `usePipelineStream`.
- **Canvas Background:** The liquid-lava animation from the legacy UI is ported to `useLiquidCanvas` and tied to the `running` state.
- **Phase Renderers:** All legacy phase rendering logic (`renderer.js`) is ported to typed React components under `components/phases/renderers/`.
- **History:** Conversations are persisted to IndexedDB and surfaced in the sidebar.
