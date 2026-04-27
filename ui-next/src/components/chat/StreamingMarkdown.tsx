'use client';

import { memo } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { TEXT_SIZES } from '@/lib/config';

interface StreamingMarkdownProps {
  text: string;
  isStreaming?: boolean;
  className?: string;
}

export const StreamingMarkdown = memo(function StreamingMarkdown({
  text,
  isStreaming = true,
  className = TEXT_SIZES.synthesis,
}: StreamingMarkdownProps) {
  return (
    <div className={`markdown-body ${className}`}>
      <MarkdownRenderer>{text}</MarkdownRenderer>
      {isStreaming && (
        <span className="inline-block h-[1em] w-0.5 animate-pulse bg-[var(--accent)] align-middle ml-0.5" />
      )}
    </div>
  );
});
