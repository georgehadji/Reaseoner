'use client';

import { useState, useEffect, useRef, memo } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { DEFAULTS, TEXT_SIZES } from '@/lib/config';
import { isAnimationComplete, markAnimationComplete } from '@/lib/animation-cache';

interface TypewriterMarkdownProps {
  text: string;
  wordsPerSecond?: number;
  onComplete?: () => void;
  animationKey?: string;
  className?: string;
}

export const TypewriterMarkdown = memo(function TypewriterMarkdown({ text, wordsPerSecond = DEFAULTS.typewriterWordsPerSecond, onComplete, animationKey, className = TEXT_SIZES.synthesis }: TypewriterMarkdownProps) {
  const [displayedText, setDisplayedText] = useState('');
  const onCompleteRef = useRef(onComplete);
  const completedRef = useRef(false);
  const startTimeRef = useRef<number>(0);

  // Keep callback ref up to date without re-triggering effect
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!text) {
      const raf = requestAnimationFrame(() => {
        setDisplayedText('');
        completedRef.current = false;
      });
      return () => cancelAnimationFrame(raf);
    }

    // If already completed (in this instance or globally), show full text immediately
    if (completedRef.current || (animationKey && isAnimationComplete(animationKey))) {
      const raf = requestAnimationFrame(() => {
        setDisplayedText(text);
        completedRef.current = true;
        if (animationKey) markAnimationComplete(animationKey);
      });
      return () => cancelAnimationFrame(raf);
    }

    // Split by whitespace but keep delimiters as separate tokens.
    // Markdown syntax without spaces (e.g. **bold**, [link](url)) stays
    // intact as a single token so it renders atomically.
    const tokens = text.split(/(\s+)/);

    const intervalMs = 1000 / wordsPerSecond; // ~66.7 ms for 15 wps
    startTimeRef.current = Date.now();

    const tick = () => {
      const elapsedMs = Date.now() - startTimeRef.current;
      const targetIndex = Math.min(Math.floor(elapsedMs / intervalMs), tokens.length);

      if (targetIndex >= tokens.length) {
        setDisplayedText(text);
        completedRef.current = true;
        if (animationKey) markAnimationComplete(animationKey);
        onCompleteRef.current?.();
        return;
      }

      setDisplayedText(tokens.slice(0, targetIndex).join(''));
    };

    const timer = setInterval(tick, intervalMs);

    // When user returns to the tab after switching away, browsers throttle
    // setInterval but Date.now() keeps advancing. We force an immediate
    // tick so the text jumps to where it should be without waiting for
    // the next scheduled interval fire.
    const handleVisibility = () => {
      if (!document.hidden) {
        tick();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [text, wordsPerSecond, animationKey]);

  return (
    <div className={`markdown-body ${className}`}>
      <MarkdownRenderer>{displayedText}</MarkdownRenderer>
      {displayedText.length < text.length && (
        <span className="inline-block h-[1em] w-0.5 animate-pulse bg-[var(--accent)] align-middle ml-0.5" />
      )}
    </div>
  );
});
