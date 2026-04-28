'use client';

import { useState, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import type { AuthError } from '@/lib/auth';

function ResetPasswordForm() {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (!supabase) {
      setError('Authentication is not configured');
      return;
    }

    setLoading(true);
    try {
      const { error: supaError } = await supabase.auth.updateUser({
        password: password,
      });
      if (supaError) throw supaError;
      
      // Password updated successfully, redirect to login
      router.push('/login?message=password-updated');
    } catch (err) {
      const authErr = err as AuthError;
      setError(authErr.message || 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error && (
        <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400" role="alert" aria-live="assertive">
          {error}
        </div>
      )}
      <div>
        <label htmlFor="password" className="mb-1 block text-sm font-medium text-[var(--text-2)]">
          New Password
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
        disabled={loading || !password}
        className="w-full rounded-lg bg-[var(--accent)] p-2.5 text-[var(--accent-text)] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
        aria-busy={loading}
      >
        {loading ? 'Updating…' : 'Update Password'}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md p-8 space-y-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
        <h1 className="text-2xl font-bold text-[var(--text)]">Update Password</h1>
        <Suspense fallback={<div className="animate-pulse h-32 bg-[var(--surface-2)] rounded-lg"></div>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
