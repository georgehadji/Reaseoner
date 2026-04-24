'use client';

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface BackgroundBlobsProps {
  running?: boolean;
}

// ── Blob animation keyframes are in globals.css ──

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return reduced;
}

export function BackgroundBlobs({ running = false }: BackgroundBlobsProps) {
  const reduced = usePrefersReducedMotion();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div
        className={cn(
          'fx-blob',
          running && 'fx-blob--running',
          reduced && 'fx-blob--static',
        )}
        style={{
          background: 'var(--blob-1)',
          left: '-10%',
          top: '-20%',
          animationDelay: '0s',
          animationDuration: reduced ? '0s' : '35s',
        }}
      />
      <div
        className={cn(
          'fx-blob',
          running && 'fx-blob--running',
          reduced && 'fx-blob--static',
        )}
        style={{
          background: 'var(--blob-2)',
          right: '-15%',
          bottom: '-10%',
          animationDelay: '-12s',
          animationDuration: reduced ? '0s' : '28s',
        }}
      />
      <div
        className={cn(
          'fx-blob',
          running && 'fx-blob--running',
          reduced && 'fx-blob--static',
        )}
        style={{
          background: 'var(--blob-3)',
          left: '40%',
          top: '60%',
          animationDelay: '-24s',
          animationDuration: reduced ? '0s' : '40s',
        }}
      />
      {running && (
        <div
          className={cn(
            'fx-blob fx-blob--accent',
            reduced && 'fx-blob--static',
          )}
          style={{
            background: 'var(--blob-accent)',
            left: '50%',
            top: '30%',
            animationDelay: '-6s',
            animationDuration: reduced ? '0s' : '20s',
          }}
        />
      )}
    </div>
  );
}
