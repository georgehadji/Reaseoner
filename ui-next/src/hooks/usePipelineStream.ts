'use client';

import { useRef, useCallback } from 'react';
import { fetchWithCsrf } from '@/lib/security-client';
import { readSSEStream } from '@/lib/sse-reader';
import { PhaseEvent, RunRequest, RunFollowupRequest } from '@/lib/types';

function getDevErrorMessage(status: number, text: string): string {
  if (status === 504) {
    return 'Backend unreachable. Run: uvicorn asgi:app --reload';
  }
  return `HTTP ${status}: ${text.slice(0, 200)}`;
}

export function usePipelineStream() {
  const abortControllerRef = useRef<AbortController | null>(null);

  const streamEvents = useCallback(
    async (url: string, body: object, onEvent: (ev: PhaseEvent) => void) => {
      // Abort any in-flight stream before starting a new one.
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();
      const resp = await fetchWithCsrf(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      });

      if (!resp.ok) {
        const text = await resp.text().catch(() => '');
        const isDev = process.env.NODE_ENV !== 'production';
        const message = isDev
          ? getDevErrorMessage(resp.status, text)
          : `HTTP ${resp.status}: ${text.slice(0, 200)}`;
        // eslint-disable-next-line no-console
        console.error('Pipeline HTTP error:', resp.status, text);
        throw new Error(message);
      }
      if (!resp.body) throw new Error('No response body');

      await readSSEStream(resp.body, onEvent, abortControllerRef.current.signal);
    },
    []
  );

  const startRun = useCallback(
    async (req: RunRequest, onEvent: (ev: PhaseEvent) => void) => {
      await streamEvents('/api/run', req, onEvent);
    },
    [streamEvents]
  );

  const startFollowup = useCallback(
    async (req: RunFollowupRequest, onEvent: (ev: PhaseEvent) => void) => {
      await streamEvents('/api/run-followup', req, onEvent);
    },
    [streamEvents]
  );

  const stopRun = useCallback(() => {
    abortControllerRef.current?.abort();
    fetchWithCsrf('/api/stop', { method: 'POST' }).catch(() => {});
    abortControllerRef.current = null;
  }, []);

  return { startRun, startFollowup, stopRun };
}
