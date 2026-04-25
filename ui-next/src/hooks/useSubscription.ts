import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api-client';

export interface SubscriptionStatus {
  tier: string;
  status: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
}

export function useSubscription() {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/billing/subscription');
      if (signal?.aborted) return;
      if (res.ok) {
        const data = await res.json();
        setSubscription(data);
      } else {
        setSubscription(null);
      }
    } catch (err) {
      if (signal?.aborted) return;
      setError(err instanceof Error ? err.message : 'Failed to fetch subscription');
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  return { subscription, loading, error, refresh };
}
