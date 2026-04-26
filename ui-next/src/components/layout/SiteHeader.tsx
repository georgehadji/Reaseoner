'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { UserMenu } from './UserMenu';
import { cn } from '@/lib/utils';

function BrainIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2a2.5 2.5 0 1 1 5 0" />
      <path d="M4 9.5a2.5 2.5 0 0 1 5-1m6 0a2.5 2.5 0 0 1 5 1" />
      <path d="M2 14a2.5 2.5 0 0 0 5 0v-4.5M17 14a2.5 2.5 0 0 0 5 0v-4.5" />
      <path d="M7 8v10a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V8" />
      <path d="M12 2v20" />
    </svg>
  );
}

export function SiteHeader() {
  const user = useAppStore((s) => s.user);
  const router = useRouter();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'glass shadow-[var(--shadow-lg)]'
          : 'bg-transparent'
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        {/* Logo */}
        <Link
          href="/"
          className="group flex items-center gap-2.5 font-semibold text-[var(--text)] transition-all duration-200 hover:opacity-90"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-text)] shadow-[var(--accent-glow)] transition-transform duration-200 group-hover:scale-110">
            <BrainIcon className="h-4.5 w-4.5" />
          </div>
          <span className="text-[15px] tracking-tight">Reasoner</span>
        </Link>

        {/* Nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {[
            { label: 'About', href: '/about' },
            { label: 'Pricing', href: '/pricing' },
            { label: 'FAQ', href: '/faq' },
            { label: 'Docs', href: '/help' },
          ].map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="underline-slide rounded-lg px-3.5 py-1.5 text-sm font-medium text-[var(--text-muted)] transition-all duration-200 hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {user ? (
            <>
              <button
                onClick={() => router.push('/chat')}
                className="hidden items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[var(--accent-text)] transition-all btn-lift btn-glow hover:bg-[var(--accent-hover)] sm:flex"
              >
                Open App
                <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <UserMenu />
            </>
          ) : (
            <>
              <button
                onClick={() => router.push('/login')}
                className="rounded-lg px-3.5 py-1.5 text-sm font-medium text-[var(--text-muted)] transition-colors hover:text-[var(--text)]"
              >
                Sign in
              </button>
              <button
                onClick={() => router.push('/chat')}
                className="flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[var(--accent-text)] transition-all btn-lift btn-glow hover:bg-[var(--accent-hover)]"
              >
                Get started
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
