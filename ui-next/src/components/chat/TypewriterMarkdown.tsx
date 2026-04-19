'use client';

import { useState, useEffect, useRef } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { isAnimationComplete, markAnimationComplete } from '@/lib/animation-cache';

interface TypewriterMarkdownProps {
  text: string;
  wordsPerSecond?: number;
  onComplete?: () => void;
  animationKey?: string;
}

export function TypewriterMarkdown({ text, wordsPerSecond = 10, onComplete, animationKey }: TypewriterMarkdownProps) {
  const [displayedText, setDisplayedText] = useState('');
  const onCompleteRef = useRef(onComplete);
  const completedRef = useRef(false);

  // Keep callback ref up to date without re-triggering effect
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!text) {
      setDisplayedText('');
      completedRef.current = false;
      return;
    }

    // If already completed (in this instance or globally), show full text immediately
    if (completedRef.current || (animationKey && isAnimationComplete(animationKey))) {
      setDisplayedText(text);
      completedRef.current = true;
      if (animationKey) markAnimationComplete(animationKey);
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
        completedRef.current = true;
        if (animationKey) markAnimationComplete(animationKey);
        onCompleteRef.current?.();
        return;
      }
      currentIndex += 1;
      setDisplayedText(tokens.slice(0, currentIndex).join(''));
    }, intervalMs);

    return () => clearInterval(timer);
  }, [text, wordsPerSecond, animationKey]);

  return (
    <div className="markdown-body text-[17px] leading-relaxed">
      <MarkdownRenderer>{displayedText}</MarkdownRenderer>
      {displayedText.length < text.length && (
        <span className="inline-block h-[1em] w-0.5 animate-pulse bg-[var(--accent)] align-middle ml-0.5" />
      )}
    </div>
  );
}
