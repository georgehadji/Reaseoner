'use client';

import { METHOD_PHASES } from '@/lib/config';
import { cn } from '@/lib/utils';

interface PhaseTimelineProps {
  method: string;
  currentPhase?: number;
  completedPhases: number[];
  errorPhases?: number[];
  phaseDurations?: Record<number, number>;
  onPhaseClick?: (phaseId: number) => void;
  onExpandAll?: () => void;
  onCollapseAll?: () => void;
}

export function PhaseTimeline({
  method,
  currentPhase,
  completedPhases,
  errorPhases = [],
  phaseDurations,
  onPhaseClick,
  onExpandAll,
  onCollapseAll,
}: PhaseTimelineProps) {
  const normalized = method.replace(/_/g, '-');
  const phases = METHOD_PHASES[normalized] || METHOD_PHASES['multi-perspective'];

  return (
    <nav
      aria-label="Pipeline phases"
      aria-live="polite"
      className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--bg)]/90 px-4 py-2 backdrop-blur-sm"
    >
      <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-thin pb-px">
        {phases.map((p) => {
          const isCompleted = completedPhases.includes(p.id);
          const isActive = currentPhase === p.id;
          const isError = errorPhases.includes(p.id);

          return (
            <button
              key={p.id}
              type="button"
              disabled={!isCompleted}
              onClick={() => onPhaseClick?.(p.id)}
              className={cn(
                'flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-left transition-all',
                isActive
                  ? 'bg-[var(--accent-dim)] text-[var(--text)]'
                  : isCompleted
                    ? 'cursor-pointer text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                    : 'cursor-default text-[var(--text-subtle)] opacity-50',
              )}
            >
              {/* Dot indicator */}
              <span className="relative flex h-1.5 w-1.5 shrink-0 items-center justify-center">
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    isError
                      ? 'bg-red-400'
                      : isActive
                        ? 'bg-[var(--accent)]'
                        : isCompleted
                          ? 'bg-[var(--text-muted)]'
                          : 'bg-[var(--surface-3)]',
                  )}
                />
                {isActive && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--accent)] opacity-50 motion-reduce:animate-none" />
                )}
              </span>

              {/* Label */}
              <span className="text-xs">
                {p.short}
                {isCompleted && phaseDurations?.[p.id] !== undefined && (
                  <span className="ml-1 opacity-50">{phaseDurations[p.id].toFixed(1)}s</span>
                )}
              </span>
            </button>
          );
        })}
      </div>

      {(onExpandAll || onCollapseAll) && (
        <div className="flex shrink-0 items-center gap-1.5">
          {onExpandAll && (
            <button
              type="button"
              onClick={onExpandAll}
              className="cursor-pointer rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-medium text-[var(--text-muted)] transition-all hover:border-[var(--border-strong)] hover:text-[var(--text)]"
            >
              Expand all
            </button>
          )}
          {onCollapseAll && (
            <button
              type="button"
              onClick={onCollapseAll}
              className="cursor-pointer rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-medium text-[var(--text-muted)] transition-all hover:border-[var(--border-strong)] hover:text-[var(--text)]"
            >
              Collapse all
            </button>
          )}
        </div>
      )}
    </nav>
  );
}
