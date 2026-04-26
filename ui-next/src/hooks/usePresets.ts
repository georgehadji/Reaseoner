'use client';

import useSWR from 'swr';
import { TIMING, API } from '@/lib/config';
import { PresetsResponse } from '@/lib/types';

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<PresetsResponse>;
};

export function usePresets() {
  const { data, error, isLoading } = useSWR<PresetsResponse>(API.PRESETS, fetcher, {
    refreshInterval: TIMING.presetsRefreshIntervalMs,
    revalidateOnFocus: false,
    dedupingInterval: 2000,
  });

  return {
    presets: data?.presets ?? {},
    models: data?.models ?? {},
    error,
    isLoading,
  };
}
