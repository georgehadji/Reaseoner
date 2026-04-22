'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown, Sparkles, Bot, Cpu, Timer, Boxes, ListChecks } from 'lucide-react';

interface SubagentInfo {
  name: string;
  model: string;
  tokens_in?: number;
  tokens_out?: number;
  duration_ms?: number;
  error?: string | null;
}

interface SynthesisCardProps {
  index: number;
  phase: number;
  name: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  tokens?: { input?: number; output?: number } | null;
  models?: string[] | null;
  subagents?: SubagentInfo[] | null;
  duration?: number;
  highlights?: Array<{ label: string; value: number }> | null;
}

function formatModelLabel(model: string) {
  return model.split('/').pop() || model;
}

import { TIMING } from '@/lib/config';

function formatDurationMs(ms: number) {
  if (ms < TIMING.durationFormatMsThreshold) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function SynthesisCard({
  index,
  phase,
  name,
  children,
  defaultOpen = true,
  tokens,
  models,
  subagents,
  duration,
  highlights,
}: SynthesisCardProps) {
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
    <div className="mb-6 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-2)]">
      <div className="border-l-4 border-[var(--accent)]">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-[var(--surface-3)]"
        >
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1.5 rounded-md bg-[var(--accent)] px-2 py-0.5 text-xs font-medium text-[var(--accent-text)]">
                <Sparkles className="h-3 w-3" />
                Phase {index + 1}
              </span>
              <span className="text-sm font-semibold text-[var(--text)]">{name}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-subtle)]">
              <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-1">
                <Boxes className="h-3 w-3" />
                {(tokens?.input ?? 0).toLocaleString()} in · {(tokens?.output ?? 0).toLocaleString()} out
              </span>
              {duration !== undefined && duration > 0 ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-1">
                  <Timer className="h-3 w-3" />
                  {duration.toFixed(1)}s
                </span>
              ) : null}
              {models && models.length > 0
                ? models.map((model) => (
                    <span
                      key={model}
                      className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-1"
                      title={model}
                    >
                      <Cpu className="h-3 w-3" />
                      {formatModelLabel(model)}
                    </span>
                  ))
                : null}
              {subagents && subagents.length > 0 ? (
                <span
                  className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-1"
                  title={subagentTooltip}
                >
                  <Bot className="h-3 w-3" />
                  {subagents.length} subagent{subagents.length > 1 ? 's' : ''}
                </span>
              ) : null}
            </div>
          </div>
          <ChevronDown
            className={cn(
              'h-4 w-4 text-[var(--text-muted)] transition-transform',
              !open && '-rotate-90'
            )}
          />
        </button>
        <div className="px-4 pb-4 pt-1" style={{ display: open ? 'block' : 'none' }}>
          {highlights && highlights.length > 0 && (
            <div className="mb-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
              <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">Synthesis Highlights</p>
              <div className="flex flex-wrap gap-2">
                {highlights.map((highlight) => (
                  <div
                    key={highlight.label}
                    className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1 text-xs text-[var(--text)]"
                  >
                    <ListChecks className="h-3 w-3 text-[var(--accent)]" />
                    {highlight.value} {highlight.label}
                  </div>
                ))}
              </div>
            </div>
          )}
          {highlights && highlights.length > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-[var(--text-subtle)]">
              <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-[var(--text-muted)]">Jump to</span>
              {highlights.map((highlight) => {
                const anchor =
                  highlight.label === 'insights'
                    ? 'critical-insights'
                    : highlight.label === 'actions'
                    ? 'action-blueprint'
                    : highlight.label === 'questions'
                    ? 'open-questions'
                    : highlight.label === 'sources'
                    ? 'sources'
                    : '';
                if (!anchor) return null;
                return (
                  <a
                    key={highlight.label}
                    href={`#${anchor}`}
                    className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
                  >
                    {highlight.label}
                  </a>
                );
              })}
            </div>
          )}
          {subagents && subagents.length > 0 && (
            <div className="mb-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
              <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">Subagents</p>
              <div className="flex flex-wrap gap-2">
                {subagents.map((s) => (
                  <div
                    key={s.name}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1 text-xs',
                      s.error
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-[var(--surface-2)] text-[var(--text-subtle)]'
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
    </div>
  );
}
