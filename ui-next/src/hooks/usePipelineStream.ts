'use client';

import { useRef, useCallback } from 'react';
import { fetchWithCsrf } from '@/lib/security-client';
import { PhaseEvent, RunRequest, RunFollowupRequest } from '@/lib/types';

export function usePipelineStream() {
  const abortControllerRef = useRef<AbortController | null>(null);

  const streamEvents = useCallback(
    async (url: string, body: object, onEvent: (ev: PhaseEvent) => void) => {
      abortControllerRef.current = new AbortController();
      const resp = await fetchWithCsrf(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      });

      if (!resp.ok) {
        const text = await resp.text().catch(() => '');
        // eslint-disable-next-line no-console
        console.error('Pipeline HTTP error:', resp.status, text);
        throw new Error(`HTTP ${resp.status}: ${text.slice(0, 200)}`);
      }
      if (!resp.body) throw new Error('No response body');

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const ev: PhaseEvent = JSON.parse(line.slice(6));
                onEvent(ev);
              } catch {
                // ignore malformed sse lines
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
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
