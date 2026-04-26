'use client';

import { TIMING, API } from '@/lib/config';
import { useState, useEffect } from 'react';

export function useServerStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    let interval: NodeJS.Timeout;

    async function check() {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMING.serverStatusAbortTimeoutMs);
      try {
        const resp = await fetch(API.PRESETS, { signal: controller.signal });
        if (mounted) setOnline(resp.ok);
      } catch {
        if (mounted) setOnline(false);
      } finally {
        clearTimeout(timeoutId);
      }
    }

    function start() {
      check();
      interval = setInterval(check, TIMING.serverStatusCheckIntervalMs);
    }

    function stop() {
      clearInterval(interval);
    }

    start();
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stop();
      } else {
        start();
      }
    });

    return () => {
      mounted = false;
      stop();
    };
  }, []);

  return online;
}
