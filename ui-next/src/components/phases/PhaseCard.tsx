'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';

interface PhaseCardProps {
  index: number;
  phase: number;
  name: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  tokens?: { input?: number; output?: number } | null;
  models?: string[] | null;
  duration?: number;
}

function formatModelLabel(model: string) {
  return model.split('/').pop() || model;
}

export function PhaseCard({
  index,
  phase,
  name,
  children,
  defaultOpen = true,
  className,
  tokens,
  models,
  duration,
}: PhaseCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        'mb-4 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]',
        className
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-[var(--surface-2)]"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-[var(--surface-2)] px-2 py-0.5 text-xs font-medium text-[var(--text-muted)]">
            Phase {index + 1}
          </span>
          <span className="text-sm font-medium text-[var(--text)]">{name}</span>
          <span className="text-xs text-[var(--text-subtle)]">
            {(tokens?.input ?? 0).toLocaleString()} in · {(tokens?.output ?? 0).toLocaleString()} out
            {duration !== undefined && duration > 0 ? (
              <span className="ml-2">· {duration.toFixed(1)}s</span>
            ) : null}
          </span>
          {models && models.length > 0 ? (
            <span className="max-w-[200px] truncate text-xs text-[var(--text-subtle)]" title={models.join(', ')}>
              {models.length === 1 ? formatModelLabel(models[0]) : `${formatModelLabel(models[0])} +${models.length - 1}`}
            </span>
          ) : null}
        </div>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-[var(--text-muted)] transition-transform',
            !open && '-rotate-90'
          )}
        />
      </button>
      {open && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  );
}
