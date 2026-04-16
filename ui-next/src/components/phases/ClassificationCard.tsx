'use client';

import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer';

interface ClassificationCardProps {
  data: unknown;
}

export function ClassificationCard({ data }: ClassificationCardProps) {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;

  const taskType = typeof d.task_type === 'string' ? d.task_type : null;
  const rationale = typeof d.rationale === 'string' ? d.rationale : '';
  const language = typeof d.language === 'string' ? d.language : null;
  const tokens = d.tokens as { input?: number; output?: number } | undefined;

  const badgeColor: Record<string, string> = {
    analytical: 'bg-blue-500/10 text-blue-600',
    strategic: 'bg-purple-500/10 text-purple-600',
    creative: 'bg-pink-500/10 text-pink-600',
    technical: 'bg-emerald-500/10 text-emerald-600',
    hybrid: 'bg-amber-500/10 text-amber-600',
    predictive: 'bg-indigo-500/10 text-indigo-600',
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {taskType && (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              badgeColor[taskType.toLowerCase()] || 'bg-[var(--surface-3)] text-[var(--text)]'
            }`}
          >
            {taskType}
          </span>
        )}
        {language && (
          <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--text-muted)]">
            {language}
          </span>
        )}
      </div>

      {rationale && (
        <div className="text-[17px] leading-relaxed text-[var(--text-2)]">
          <MarkdownRenderer>{rationale}</MarkdownRenderer>
        </div>
      )}

      {/* Tokens shown in PhaseCard header */}
    </div>
  );
}
