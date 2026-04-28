'use client';

import { useState } from 'react';
import { Lock } from 'lucide-react';
import { SecurityModal } from './SecurityModal';
import { cn } from '@/lib/utils';

export function SecurityBadge({ className }: { className?: string }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          'flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-medium text-[var(--text-muted)] transition-all hover:border-[var(--text-subtle)] hover:text-[var(--text)] active:scale-[0.98]',
          className
        )}
      >
        <Lock className="h-3 w-3 text-green-500" />
        <span>Secure</span>
      </button>

      <SecurityModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
}
