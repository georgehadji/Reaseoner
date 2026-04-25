'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signUpWithEmail } from '@/lib/auth';
import type { AuthError } from '@/lib/auth';

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!isValidEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      await signUpWithEmail(email, password);
      router.push('/login?message=check-email');
    } catch (err) {
      const authErr = err as AuthError;
      setError(authErr.message || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md p-8 space-y-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
        <h1 className="text-2xl font-bold text-[var(--text)]">Create Account</h1>
        {error && (
          <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600" role="alert" aria-live="assertive">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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
              aria-describedby="password-hint"
            />
            <p id="password-hint" className="mt-1 text-xs text-[var(--text-muted)]">
              Must be at least 6 characters
            </p>
          </div>
          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full rounded-lg bg-[var(--accent)] p-2.5 text-[var(--accent-text)] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
            aria-busy={loading}
          >
            {loading ? 'Creating account…' : 'Sign Up'}
          </button>
        </form>
        <p className="text-center text-sm text-[var(--text-muted)]">
          Already have an account?{' '}
          <a href="/login" className="text-[var(--accent)] hover:underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
