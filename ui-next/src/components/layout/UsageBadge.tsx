'use client';

import { useQuota } from '@/hooks/useQuota';

export function UsageBadge() {
  const { quota } = useQuota();
  if (!quota) return null;

  const percent = (quota.used / quota.max) * 100;
  const color = percent >= 90 ? 'text-red-500' : percent >= 70 ? 'text-yellow-500' : 'text-green-500';

  return (
    <div className={`text-xs font-medium ${color}`}>
      {quota.used} / {quota.max} queries
    </div>
  );
}
