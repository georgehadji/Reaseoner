'use client';

import useSWR from 'swr';
import { TIMING } from '@/lib/config';
import { PresetsResponse } from '@/lib/types';

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<PresetsResponse>;
};

export function usePresets() {
  const { data, error, isLoading } = useSWR<PresetsResponse>('/api/presets', fetcher, {
    refreshInterval: TIMING.presetsRefreshIntervalMs,
    revalidateOnFocus: false,
  });

  return {
    presets: data?.presets ?? {},
    models: data?.models ?? {},
    error,
    isLoading,
  };
}
