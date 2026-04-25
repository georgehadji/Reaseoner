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

export function useScrollAnchor(containerRef: React.RefObject<HTMLElement | null>): ScrollAnchor {
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [showNewContentIndicator, setShowNewContentIndicator] = useState(false);
  const isNearBottomRef = useRef(true);

  const scrollToBottom = useCallback(
    (opts?: { behavior?: ScrollBehavior }) => {
      const el = containerRef.current;
      if (!el) return;
      el.scrollTo({
        top: el.scrollHeight,
        behavior: opts?.behavior ?? 'auto',
      });
    },
    [containerRef]
  );

  const checkPosition = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
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
  // RAF-debounced to avoid forcing layout on every streaming text mutation.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let pendingRaf: number | null = null;
    const observer = new MutationObserver(() => {
      if (pendingRaf !== null) return;
      pendingRaf = requestAnimationFrame(() => {
        pendingRaf = null;
        if (isNearBottomRef.current) {
          scrollToBottom({ behavior: 'smooth' });
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
  }, [containerRef, scrollToBottom]);

  return {
    isNearBottom,
    scrollToBottom,
    showNewContentIndicator,
    dismissIndicator,
  };
}
