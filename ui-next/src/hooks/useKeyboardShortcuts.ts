'use client';

import { useEffect } from 'react';

export function useKeyboardShortcuts({
  onToggleSidebar,
  onShowShortcuts,
  onStop,
}: {
  onToggleSidebar?: () => void;
  onShowShortcuts?: () => void;
  onStop?: () => void;
}) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const isTyping = target.closest('textarea, input');

      if (e.key === '?' && !isTyping) {
        e.preventDefault();
        onShowShortcuts?.();
      }
      if (e.key === 'b' && !isTyping) {
        e.preventDefault();
        onToggleSidebar?.();
      }
      if (e.key === 'Escape') {
        onStop?.();
      }
    }

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onToggleSidebar, onShowShortcuts, onStop]);
}
