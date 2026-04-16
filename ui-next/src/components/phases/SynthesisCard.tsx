'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown, Sparkles } from 'lucide-react';

interface SynthesisCardProps {
  index: number;
  phase: number;
  name: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  tokens?: { input?: number; output?: number } | null;
  models?: string[] | null;
}

function formatModelLabel(model: string) {
  return model.split('/').pop() || model;
}

export function SynthesisCard({
  index,
  phase,
  name,
  children,
  defaultOpen = true,
  tokens,
  models,
}: SynthesisCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-2)]">
      <div className="border-l-4 border-[var(--accent)]">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-[var(--surface-3)]"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-md bg-[var(--accent)] px-2 py-0.5 text-xs font-medium text-[var(--accent-text)]">
              <Sparkles className="h-3 w-3" />
              Phase {index + 1}
            </span>
            <span className="text-sm font-semibold text-[var(--text)]">{name}</span>
            <span className="text-xs text-[var(--text-subtle)]">
              {(tokens?.input ?? 0).toLocaleString()} in · {(tokens?.output ?? 0).toLocaleString()} out
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
    </div>
  );
}
