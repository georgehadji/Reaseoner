'use client';

import { useState, useEffect } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';

interface TypewriterMarkdownProps {
  text: string;
  wordsPerSecond?: number;
}

export function TypewriterMarkdown({ text, wordsPerSecond = 10 }: TypewriterMarkdownProps) {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    if (!text) {
      setDisplayedText('');
      return;
    }

    // Split by whitespace but keep delimiters as separate tokens.
    // Markdown syntax without spaces (e.g. **bold**, [link](url)) stays
    // intact as a single token so it renders atomically.
    const tokens = text.split(/(\s+)/);
    let currentIndex = 0;

    const intervalMs = 1000 / wordsPerSecond; // 100 ms for 10 wps

    const timer = setInterval(() => {
      if (currentIndex >= tokens.length) {
        clearInterval(timer);
        return;
      }
      currentIndex += 1;
      setDisplayedText(tokens.slice(0, currentIndex).join(''));
    }, intervalMs);

    return () => clearInterval(timer);
  }, [text, wordsPerSecond]);

  return (
    <div className="markdown-body text-[17px] leading-relaxed">
      <MarkdownRenderer>{displayedText}</MarkdownRenderer>
      {displayedText.length < text.length && (
        <span className="inline-block h-[1em] w-0.5 animate-pulse bg-[var(--accent)] align-middle ml-0.5" />
      )}
    </div>
  );
}
