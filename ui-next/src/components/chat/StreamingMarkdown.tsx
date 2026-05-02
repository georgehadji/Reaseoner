'use client';

import { memo } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { TEXT_SIZES } from '@/lib/config';

/**
 * StreamingMarkdown — renders finalized markdown content with an optional cursor.
 * NOTE: Do NOT use this for live SSE streaming. During active streaming,
 * ChatFeed renders raw text directly to avoid re-parsing the full Markdown
 * AST on every chunk. Use this only for content that is complete but needs
 * a decorative cursor (e.g., typewriter effects on cached/history content).
 */
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
        <span className="inline-block h-[1em] w-0.5 animate-cursor-blink rounded-sm bg-[var(--accent)] align-middle ml-0.5" />
      )}
    </div>
  );
});
