'use client';

import useSWR from 'swr';
import { PresetsResponse } from '@/lib/types';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export function usePresets() {
  const { data, error, isLoading } = useSWR<PresetsResponse>('/api/presets', fetcher, {
    refreshInterval: 60000,
    revalidateOnFocus: false,
  });

  return {
    presets: data?.presets ?? {},
    models: data?.models ?? {},
    error,
    isLoading,
  };
}
