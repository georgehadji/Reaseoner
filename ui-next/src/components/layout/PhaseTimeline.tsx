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
}

export function PhaseTimeline({
  method,
  currentPhase,
  completedPhases,
  errorPhases = [],
  phaseDurations,
  onPhaseClick,
}: PhaseTimelineProps) {
  const phases = METHOD_PHASES[method] || METHOD_PHASES['multi_perspective'] || METHOD_PHASES['multi-perspective'];

  return (
    <nav
      aria-label="Pipeline phases"
      className="sticky top-14 z-20 flex items-center gap-3 overflow-x-auto border-b border-[var(--border)] bg-[var(--bg)] px-4 py-2"
      aria-live="polite"
    >
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
              'flex shrink-0 items-center gap-1.5 rounded-full px-2 py-1 text-left transition-colors',
              isActive
                ? 'bg-[var(--surface-2)] text-[var(--text)]'
                : 'text-[var(--text-muted)] hover:bg-[var(--surface)]',
              !isCompleted && 'opacity-60'
            )}
          >
            <span
              className={cn(
                'relative flex h-2 w-2 shrink-0 items-center justify-center rounded-full',
                isError
                  ? 'bg-red-500'
                  : isActive
                    ? 'bg-[var(--accent)]'
                    : isCompleted
                      ? 'bg-[var(--text-subtle)]'
                      : 'bg-[var(--border-strong)]'
              )}
            >
              {isActive && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--accent)] opacity-40 motion-reduce:animate-none" />
              )}
            </span>
            <span
              className={cn(
                'text-xs transition-colors',
                isActive ? 'font-medium text-[var(--text)]' : 'text-[var(--text-muted)]'
              )}
            >
              {p.short}
              {isCompleted && phaseDurations && phaseDurations[p.id] !== undefined ? (
                <span className="ml-1 text-[10px] opacity-70">
                  {phaseDurations[p.id].toFixed(1)}s
                </span>
              ) : null}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
