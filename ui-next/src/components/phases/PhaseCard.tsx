'use client';

import { useEffect, useState, memo } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown, Bot, Timer, Cpu, Boxes } from 'lucide-react';
import { Tooltip } from '@/components/ui/Tooltip';

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
  forceOpen?: boolean | null;
  className?: string;
  tokens?: { input?: number; output?: number } | null;
  models?: string[] | null;
  subagents?: SubagentInfo[] | null;
  duration?: number;
  compact?: boolean;
  status?: 'idle' | 'active' | 'completed' | 'error';
}

function formatModelLabel(model: string) {
  return model.split('/').pop() || model;
}

import { TIMING } from '@/lib/config';

function formatDurationMs(ms: number) {
  if (ms < TIMING.durationFormatMsThreshold) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export const PhaseCard = memo(function PhaseCard({
  index,
  phase,
  name,
  children,
  defaultOpen = true,
  forceOpen = null,
  className,
  tokens,
  models,
  subagents,
  duration,
  compact = false,
  status = 'idle',
}: PhaseCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    if (forceOpen === null) return;
    setOpen(forceOpen);
  }, [forceOpen]);

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
        className={cn(
          'flex w-full items-center justify-between text-left hover:bg-[var(--surface-2)]',
          compact && !open ? 'px-3 py-2' : 'px-4 py-3'
        )}
      >
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {compact && !open ? (
            <>
              <span
                className={cn(
                  'h-2 w-2 shrink-0 rounded-full',
                  status === 'error' ? 'bg-red-500' :
                  status === 'active' ? 'bg-[var(--accent)] animate-pulse' :
                  status === 'completed' ? 'bg-green-500' :
                  'bg-[var(--border-strong)]'
                )}
              />
              <span className="text-xs font-medium text-[var(--text)]">{name}</span>
              {duration !== undefined && duration > 0 ? (
                <span className="text-[10px] text-[var(--text-subtle)]">
                  <Timer className="inline h-3 w-3" /> {duration.toFixed(1)}s
                </span>
              ) : null}
            </>
          ) : (
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-[var(--surface-2)] px-2 py-0.5 text-xs font-medium text-[var(--text-muted)]">
                  Phase {index + 1}
                </span>
                <span className="text-sm font-medium text-[var(--text)]">{name}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-subtle)]">
                <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1">
                  <Boxes className="h-3 w-3" />
                  {(tokens?.input ?? 0).toLocaleString()} in · {(tokens?.output ?? 0).toLocaleString()} out
                </span>
                {duration !== undefined && duration > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1">
                    <Timer className="h-3 w-3" />
                    {duration.toFixed(1)}s
                  </span>
                ) : null}
                {models && models.length > 0
                  ? models.map((model) => (
                      <Tooltip key={model} text={model}>
                        <span
                          className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1"
                        >
                          <Cpu className="h-3 w-3" />
                          {formatModelLabel(model)}
                        </span>
                      </Tooltip>
                    ))
                  : null}
                {subagents && subagents.length > 0 ? (
                  <Tooltip text={subagentTooltip}>
                    <span
                      className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1"
                    >
                      <Bot className="h-3 w-3" />
                      {subagents.length} subagent{subagents.length > 1 ? 's' : ''}
                    </span>
                  </Tooltip>
                ) : null}
              </div>
            </div>
          )}
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
              {subagents.map((s) => {
                const el = (
                  <div
                    key={s.name}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1 text-xs',
                      s.error
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-[var(--surface)] text-[var(--text-subtle)]'
                    )}
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
                );
                return s.error ? <Tooltip key={s.name} text={s.error}>{el}</Tooltip> : el;
              })}
            </div>
          </div>
        )}
        {children}
      </div>
    </div>
  );
});
