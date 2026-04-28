'use client';

import { TIMING } from '@/lib/config';
import { useRef, useCallback, useEffect, useState } from 'react';

interface ScrollAnchor {
  isNearBottom: boolean;
  scrollToBottom: (opts?: { behavior?: ScrollBehavior }) => void;
  showNewContentIndicator: boolean;
  dismissIndicator: () => void;
}

const THRESHOLD = TIMING.scrollAnchorThresholdPx;

/**
 * Keeps the chat scroll anchored to the bottom as new content arrives.
 *
 * Smoothness features:
 * - RAF-throttled scroll to avoid layout thrashing during streaming
 * - Instant ('auto') scroll while actively streaming — smooth scroll fights itself
 * - Smooth scroll only on user-initiated actions (dismiss indicator, manual scroll)
 * - Scroll position is sampled from the ref, not React state, for zero latency
 */
export function useScrollAnchor(containerRef: React.RefObject<HTMLElement | null>): ScrollAnchor {
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [showNewContentIndicator, setShowNewContentIndicator] = useState(false);
  const isNearBottomRef = useRef(true);
  const isSmoothScrollingRef = useRef(false);

  const scrollToBottom = useCallback(
    (opts?: { behavior?: ScrollBehavior }) => {
      const el = containerRef.current;
      if (!el) return;
      const behavior = opts?.behavior ?? 'auto';
      if (behavior === 'smooth') {
        isSmoothScrollingRef.current = true;
        // Clear the flag after the smooth scroll completes (~500ms)
        setTimeout(() => { isSmoothScrollingRef.current = false; }, 500);
      }
      el.scrollTo({ top: el.scrollHeight, behavior });
    },
    [containerRef]
  );

  const checkPosition = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    // Don't override during a smooth scroll
    if (isSmoothScrollingRef.current) return;
    const nearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < THRESHOLD;
    isNearBottomRef.current = nearBottom;
    setIsNearBottom(nearBottom);
    if (nearBottom) {
      setShowNewContentIndicator(false);
    }
  }, [containerRef]);

  const dismissIndicator = useCallback(() => {
    setShowNewContentIndicator(false);
    scrollToBottom({ behavior: 'smooth' });
  }, [scrollToBottom]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('scroll', checkPosition, { passive: true });
    return () => el.removeEventListener('scroll', checkPosition);
  }, [checkPosition]);

  // When content grows and we were near bottom, stay near bottom.
  // RAF-debounced + throttled to avoid forcing layout on every streaming text mutation.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let pendingRaf: number | null = null;
    let lastScrollTime = 0;
    const SCROLL_THROTTLE_MS = 80; // Throttle scrolls to ~12fps — smooth enough, cheap enough

    const observer = new MutationObserver(() => {
      if (pendingRaf !== null) return;
      pendingRaf = requestAnimationFrame(() => {
        pendingRaf = null;
        const now = performance.now();
        if (now - lastScrollTime < SCROLL_THROTTLE_MS) return;
        lastScrollTime = now;

        if (isNearBottomRef.current) {
          // Use 'auto' (instant) during streaming — 'smooth' fights itself
          // when mutations fire faster than the scroll animation duration
          el.scrollTo({ top: el.scrollHeight, behavior: 'auto' });
        } else {
          setShowNewContentIndicator(true);
        }
      });
    });

    observer.observe(el, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      if (pendingRaf !== null) cancelAnimationFrame(pendingRaf);
    };
  }, [containerRef]);

  return {
    isNearBottom,
    scrollToBottom,
    showNewContentIndicator,
    dismissIndicator,
  };
}
