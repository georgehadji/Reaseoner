'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown, Bot } from 'lucide-react';

interface SubagentInfo {
  name: string;
  model: string;
  tokens_in?: number;
  tokens_out?: number;
  duration_ms?: number;
  error?: string | null;
}

interface PhaseCardProps {
  index: number;
  phase: number;
  name: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  tokens?: { input?: number; output?: number } | null;
  models?: string[] | null;
  subagents?: SubagentInfo[] | null;
  duration?: number;
}

function formatModelLabel(model: string) {
  return model.split('/').pop() || model;
}

import { TIMING } from '@/lib/config';

function formatDurationMs(ms: number) {
  if (ms < TIMING.durationFormatMsThreshold) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
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
  subagents,
  duration,
}: PhaseCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  const subagentTooltip = subagents
    ? subagents
        .map(
          (s) =>
            `${s.name} → ${formatModelLabel(s.model)}${s.error ? ' [error]' : ''}`
        )
        .join('\n')
    : '';

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
          {subagents && subagents.length > 0 ? (
            <span
              className="inline-flex items-center gap-1 rounded-md bg-[var(--surface-2)] px-2 py-0.5 text-xs text-[var(--text-subtle)]"
              title={subagentTooltip}
            >
              <Bot className="h-3 w-3" />
              {subagents.length} subagent{subagents.length > 1 ? 's' : ''}
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
      <div className="px-4 pb-4 pt-1" style={{ display: open ? 'block' : 'none' }}>
        {subagents && subagents.length > 0 && (
          <div className="mb-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
            <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">Subagents</p>
            <div className="flex flex-wrap gap-2">
              {subagents.map((s) => (
                <div
                  key={s.name}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-2 py-1 text-xs',
                    s.error
                      ? 'bg-red-500/10 text-red-400'
                      : 'bg-[var(--surface)] text-[var(--text-subtle)]'
                  )}
                  title={s.error || undefined}
                >
                  <Bot className="h-3 w-3 shrink-0" />
                  <span className="font-medium">{s.name}</span>
                  <span className="text-[var(--text-muted)]">→</span>
                  <span>{formatModelLabel(s.model)}</span>
                  <span className="text-[var(--text-muted)]">
                    {s.tokens_in ?? 0}+{s.tokens_out ?? 0} tok
                  </span>
                  <span className="text-[var(--text-muted)]">
                    · {formatDurationMs(s.duration_ms ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
