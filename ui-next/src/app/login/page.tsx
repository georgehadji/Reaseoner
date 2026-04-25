'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signInWithEmail } from '@/lib/auth';
import type { AuthError } from '@/lib/auth';

function LoginMessage() {
  const searchParams = useSearchParams();
  const message = searchParams.get('message');
  if (message !== 'check-email') return null;
  return (
    <div className="rounded-lg bg-green-500/10 p-3 text-sm text-green-600" role="status" aria-live="polite">
      Check your email to confirm your account.
    </div>
  );
}

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signInWithEmail(email, password);
      router.push('/');
    } catch (err) {
      const authErr = err as AuthError;
      setError(authErr.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md p-8 space-y-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
        <h1 className="text-2xl font-bold text-[var(--text)]">Sign In</h1>
        <Suspense fallback={null}>
          <LoginMessage />
        </Suspense>
        {error && (
          <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600" role="alert" aria-live="assertive">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-[var(--text-2)]">
              Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-2.5 text-[var(--text)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
              required
              disabled={loading}
              aria-invalid={!!error}
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-[var(--text-2)]">
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-2.5 text-[var(--text)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
              required
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full rounded-lg bg-[var(--accent)] p-2.5 text-[var(--accent-text)] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
            aria-busy={loading}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <div className="flex items-center justify-between text-sm text-[var(--text-muted)]">
          <a href="/forgot-password" className="text-[var(--accent)] hover:underline">
            Forgot password?
          </a>
          <span>
            No account?{' '}
            <a href="/signup" className="text-[var(--accent)] hover:underline">
              Sign up
            </a>
          </span>
        </div>
      </div>
    </div>
  );
}
