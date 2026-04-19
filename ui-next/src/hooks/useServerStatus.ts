'use client';

import { useState, useEffect } from 'react';

export function useServerStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;

    async function check() {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
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
    const id = setInterval(check, 10000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return online;
}
