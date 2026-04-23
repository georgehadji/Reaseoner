'use client';

import { useEffect } from 'react';

export function useKeyboardShortcuts({
  onToggleSidebar,
  onShowShortcuts,
  onStop,
  onClearComposer,
  onFocusComposer,
  onCopyLastResponse,
  onCommandPalette,
}: {
  onToggleSidebar?: () => void;
  onShowShortcuts?: () => void;
  onStop?: () => void;
  onClearComposer?: () => void;
  onFocusComposer?: () => void;
  onCopyLastResponse?: () => void;
  onCommandPalette?: () => void;
}) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const isTyping = target.closest('textarea, input');

      // Command palette: Ctrl/Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key === 'k' && !isTyping) {
        e.preventDefault();
        onCommandPalette?.();
        return;
      }

      // Focus composer: /
      if (e.key === '/' && !isTyping) {
        e.preventDefault();
        onFocusComposer?.();
        return;
      }

      // Clear composer: Ctrl/Cmd+L
      if ((e.ctrlKey || e.metaKey) && e.key === 'l' && !isTyping) {
        e.preventDefault();
        onClearComposer?.();
        return;
      }

      // Copy last response: Ctrl/Cmd+Shift+C
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C' && !isTyping) {
        e.preventDefault();
        onCopyLastResponse?.();
        return;
      }

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
  }, [onToggleSidebar, onShowShortcuts, onStop, onClearComposer, onFocusComposer, onCopyLastResponse, onCommandPalette]);
}
