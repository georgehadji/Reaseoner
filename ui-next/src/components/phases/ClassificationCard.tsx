'use client';

import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer';
import { TEXT_SIZES } from '@/lib/config';

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
    analytical: 'bg-[#808080]/10 text-[#A0A0A0]',
    strategic: 'bg-[#808080]/10 text-[#A0A0A0]',
    creative: 'bg-[#808080]/10 text-[#A0A0A0]',
    technical: 'bg-[#808080]/10 text-[#A0A0A0]',
    hybrid: 'bg-[#808080]/10 text-[#A0A0A0]',
    predictive: 'bg-[#808080]/10 text-[#A0A0A0]',
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
        <div className={`${TEXT_SIZES.phaseCard} text-[var(--text-2)]`}>
          <MarkdownRenderer>{rationale}</MarkdownRenderer>
        </div>
      )}

      {/* Tokens shown in PhaseCard header */}
    </div>
  );
}
