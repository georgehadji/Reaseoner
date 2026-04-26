import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api-client';

interface QuotaStatus {
  used: number;
  max: number;
  remaining: number;
  reset_date: string;
}

export function useQuota() {
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/quota');
      if (res.ok) {
        const data = await res.json();
        setQuota(data);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => {
      // Silently ignore quota fetch errors on mount to avoid unhandled rejection
    });
  }, [refresh]);

  return { quota, loading, refresh };
}
