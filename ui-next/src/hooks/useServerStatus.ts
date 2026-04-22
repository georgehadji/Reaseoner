'use client';

import { TIMING } from '@/lib/config';
import { useState, useEffect } from 'react';

export function useServerStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;

    async function check() {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMING.serverStatusAbortTimeoutMs);
      try {
        const resp = await fetch('/api/presets', { signal: controller.signal });
        if (mounted) setOnline(resp.ok);
      } catch {
        if (mounted) setOnline(false);
      } finally {
        clearTimeout(timeoutId);
      }
    }

    check();
    const id = setInterval(check, TIMING.serverStatusCheckIntervalMs);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return online;
}
