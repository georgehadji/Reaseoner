'use client';

import { X } from 'lucide-react';

interface ShortcutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ShortcutModal({ isOpen, onClose }: ShortcutModalProps) {
  if (!isOpen) return null;
  return (
    <div
      className="fixed inset-0 z-[300] flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-lg)]">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-base font-semibold text-[var(--text)]">Keyboard Shortcuts</span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            aria-label="Close shortcuts"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <kbd className="rounded bg-[var(--surface-2)] px-2 py-1 font-mono text-[var(--text-2)]">Enter</kbd>
            <span className="text-[var(--text-muted)]">Run pipeline</span>
          </div>
          <div className="flex items-center justify-between">
            <kbd className="rounded bg-[var(--surface-2)] px-2 py-1 font-mono text-[var(--text-2)]">Shift + Enter</kbd>
            <span className="text-[var(--text-muted)]">New line in composer</span>
          </div>
          <div className="flex items-center justify-between">
            <kbd className="rounded bg-[var(--surface-2)] px-2 py-1 font-mono text-[var(--text-2)]">Esc</kbd>
            <span className="text-[var(--text-muted)]">Stop running pipeline</span>
          </div>
          <div className="flex items-center justify-between">
            <kbd className="rounded bg-[var(--surface-2)] px-2 py-1 font-mono text-[var(--text-2)]">B</kbd>
            <span className="text-[var(--text-muted)]">Toggle sidebar</span>
          </div>
          <div className="flex items-center justify-between">
            <kbd className="rounded bg-[var(--surface-2)] px-2 py-1 font-mono text-[var(--text-2)]">?</kbd>
            <span className="text-[var(--text-muted)]">Show this panel</span>
          </div>
        </div>
      </div>
    </div>
  );
}
