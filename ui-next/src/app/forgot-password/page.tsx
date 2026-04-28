'use client';

import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import type { AuthError } from '@/lib/auth';

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!isValidEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    if (!supabase) {
      setError('Authentication is not configured');
      return;
    }

    setLoading(true);
    try {
      const { error: supaError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (supaError) throw supaError;
      setSent(true);
    } catch (err) {
      const authErr = err as AuthError;
      setError(authErr.message || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md p-8 space-y-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
        <h1 className="text-2xl font-bold text-[var(--text)]">Reset Password</h1>
        {sent ? (
          <div className="rounded-lg bg-[#808080]/10 p-4 text-[#A0A0A0]" role="status" aria-live="polite">
            Check your email for a reset link.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {error && (
              <div className="rounded-lg bg-[#606060]/10 p-3 text-sm text-[#A0A0A0]" role="alert" aria-live="assertive">
                {error}
              </div>
            )}
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
                aria-invalid={!!error}
                aria-describedby={error ? 'email-error' : undefined}
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !email}
              className="w-full rounded-lg bg-[var(--accent)] p-2.5 text-[var(--accent-text)] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
              aria-busy={loading}
            >
              {loading ? 'Sending…' : 'Send Reset Link'}
            </button>
            <p className="text-center text-sm text-[var(--text-muted)]">
              Remember your password?{' '}
              <a href="/login" className="text-[var(--accent)] hover:underline">
                Sign in
              </a>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
