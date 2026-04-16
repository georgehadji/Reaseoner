'use client';

import { cn } from '@/lib/utils';
import { Star } from 'lucide-react';

interface CritiqueCardProps {
  data: unknown;
}

export function CritiqueCard({ data }: CritiqueCardProps) {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  const scores = Array.isArray(d.scores) ? d.scores : [];
  if (!scores.length) return null;

  return (
    <div className="space-y-4">
      {scores.map((s: Record<string, unknown>, idx: number) => {
        const perspective =
          typeof s.perspective === 'string'
            ? s.perspective
            : (s.perspective as Record<string, string>)?.name ?? '?';
        const total = typeof s.total === 'number' ? s.total : 0;
        const isTop = !!s.is_top;
        const biasFlags = Array.isArray(s.bias_flags) ? s.bias_flags : [];
        const steelMan = typeof s.steel_man === 'string' ? s.steel_man : '';
        const barWidth = Math.min(100, total);

        return (
          <div
            key={idx}
            className={cn(
              'rounded-xl border p-3',
              isTop
                ? 'border-[var(--accent)]/30 bg-[var(--accent)]/5'
                : 'border-[var(--border)] bg-[var(--surface)]'
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-medium text-[var(--text)]">
                  {perspective}
                </span>
                {isTop && (
                  <span className="flex items-center gap-1 rounded-full bg-[var(--accent)] px-2 py-0.5 text-sm font-medium text-[var(--accent-text)]">
                    <Star className="h-3.5 w-3.5" /> Top
                  </span>
                )}
              </div>
              <span className="font-mono text-base font-semibold text-[var(--text)]">
                {total.toFixed(1)}
              </span>
            </div>

            <div className="mt-2 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--surface-3)]">
                <div
                  className="h-full rounded-full bg-[var(--accent)] transition-all"
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>

            {biasFlags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {biasFlags.map((b: string, i: number) => (
                  <span
                    key={i}
                    className="rounded-full border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-sm text-red-500"
                  >
                    {b}
                  </span>
                ))}
              </div>
            )}

            {steelMan && (
              <div className="mt-2 text-sm text-[var(--text-muted)]">
                <span className="font-medium text-[var(--text-subtle)]">Steel man:</span>{' '}
                {steelMan}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
