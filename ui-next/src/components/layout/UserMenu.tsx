'use client';

import { useState, useRef, useEffect } from 'react';
import { useAppStore } from '@/stores/app-store';
import { signOut } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { useSubscription } from '@/hooks/useSubscription';
import { User, LayoutDashboard, CreditCard, LogOut, ChevronDown, Info } from 'lucide-react';

export function UserMenu() {
  const user = useAppStore((s) => s.user);
  const logout = useAppStore((s) => s.logout);
  const router = useRouter();
  const { subscription } = useSubscription();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) return null;

  const tierLabel = subscription?.tier ? subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1) : 'Free';

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch {
      // ignore
    }
    logout();
    router.push('/login');
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="User menu"
      >
        <User className="h-4 w-4 text-[var(--text-muted)]" />
        <span className="hidden max-w-[120px] truncate sm:inline">{user.email}</span>
        <span className="inline-flex items-center rounded-full bg-[var(--accent)]/10 px-1.5 py-0.5 text-[10px] font-medium text-[var(--accent)]">
          {tierLabel}
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-1 w-52 rounded-lg border border-[var(--border)] bg-[var(--surface)] py-1 shadow-[var(--shadow-lg)]"
          role="menu"
          aria-label="User menu"
        >
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push('/dashboard');
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
            role="menuitem"
          >
            <LayoutDashboard className="h-4 w-4 text-[var(--text-muted)]" />
            Dashboard
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push('/settings');
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
            role="menuitem"
          >
            <User className="h-4 w-4 text-[var(--text-muted)]" />
            Settings
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push('/pricing');
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
            role="menuitem"
          >
            <CreditCard className="h-4 w-4 text-[var(--text-muted)]" />
            Pricing
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push('/about');
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
            role="menuitem"
          >
            <Info className="h-4 w-4 text-[var(--text-muted)]" />
            About
          </button>
          <div className="my-1 h-px bg-[var(--border)]" />
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-500 transition-colors hover:bg-red-500/10"
            role="menuitem"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
