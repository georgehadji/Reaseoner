'use client';

import { useAppStore } from '@/stores/app-store';
import { useRouter } from 'next/navigation';
import { Brain, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { UserMenu } from './UserMenu';

export function SiteHeader() {
  const user = useAppStore((s) => s.user);
  const router = useRouter();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between px-6 lg:px-12 border-b border-[var(--border)] bg-[var(--bg)]">
      <Link href="/" className="flex items-center gap-2 font-bold text-xl hover:opacity-80 transition-opacity">
        <Brain className="h-6 w-6 text-[var(--accent)]" />
        <span>ARA</span>
      </Link>
      <nav className="hidden md:flex gap-6 text-sm font-medium text-[var(--text-muted)]">
        <Link href="/about" className="hover:text-[var(--text)] transition-colors">About</Link>
        <Link href="/pricing" className="hover:text-[var(--text)] transition-colors">Pricing</Link>
        <Link href="/faq" className="hover:text-[var(--text)] transition-colors">FAQ</Link>
        <Link href="/help" className="hover:text-[var(--text)] transition-colors">Docs</Link>
      </nav>
      <div className="flex items-center gap-3">
        {user ? (
          <>
            <button
              onClick={() => router.push('/chat')}
              className="hidden sm:flex rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-text)] transition-opacity hover:opacity-90 items-center gap-2"
            >
              Go to App <ArrowRight className="h-4 w-4" />
            </button>
            <UserMenu />
          </>
        ) : (
          <>
            <button
              onClick={() => router.push('/login')}
              className="text-sm font-medium hover:text-[var(--text)] transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={() => router.push('/signup')}
              className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-text)] transition-opacity hover:opacity-90"
            >
              Get Started
            </button>
          </>
        )}
      </div>
    </header>
  );
}
