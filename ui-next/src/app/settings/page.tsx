'use client';

import { useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useSubscription } from '@/hooks/useSubscription';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { User, ShieldAlert } from 'lucide-react';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function SettingsPage() {
  const user = useAppStore((s) => s.user);
  const logout = useAppStore((s) => s.logout);
  const router = useRouter();
  const { subscription } = useSubscription();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  if (!user) {
    if (typeof window !== 'undefined') router.push('/login');
    return null;
  }

  const handleResetPassword = async () => {
    setLoading(true);
    setMessage({ type: '', text: '' });
    if (!supabase) return;
    
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(user.email!, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (error) throw error;
      setMessage({ type: 'success', text: 'Password reset email sent!' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to send reset email' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm("Are you sure? This action cannot be undone and will delete all your data.");
    if (!confirmed) return;

    setLoading(true);
    // Note: True account deletion usually requires edge functions or admin privileges in Supabase.
    // For this UI, we'll log them out and show a message if the direct API fails.
    try {
      if (supabase) {
         // Attempt RPC or just sign out for safety if RPC isn't configured
         await supabase.auth.signOut();
      }
      logout();
      router.push('/?deleted=true');
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to delete account. Please contact support.' });
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-4 py-12 flex-1 w-full">
      <h1 className="mb-8 text-3xl font-bold text-[var(--text)]">Account Settings</h1>

      {message.text && (
        <div className={`mb-6 rounded-lg p-4 text-sm ${message.type === 'error' ? 'bg-red-500/10 text-red-600' : 'bg-green-500/10 text-green-600'}`}>
          {message.text}
        </div>
      )}

      <div className="space-y-8">
        {/* Profile Section */}
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
          <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
            <User className="h-5 w-5 text-[var(--accent)]" /> Profile
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-[var(--text-muted)]">Email Address</label>
              <div className="rounded-lg bg-[var(--surface-2)] p-3 text-[var(--text)]">{user.email}</div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-[var(--text-muted)]">Current Plan</label>
              <div className="flex items-center justify-between rounded-lg bg-[var(--surface-2)] p-3 text-[var(--text)] capitalize">
                {subscription?.tier || 'Free'}
                <button onClick={() => router.push('/dashboard')} className="text-sm text-[var(--accent)] hover:underline">Manage</button>
              </div>
            </div>
          </div>
        </section>

        {/* Security Section */}
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
          <h2 className="mb-4 text-xl font-semibold">Security</h2>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="font-medium text-[var(--text)]">Password</p>
              <p className="text-sm text-[var(--text-muted)]">Receive an email to reset your password.</p>
            </div>
            <button
              onClick={handleResetPassword}
              disabled={loading}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-2 text-sm font-medium hover:bg-[var(--surface-3)] transition-colors disabled:opacity-50"
            >
              Reset Password
            </button>
          </div>
        </section>

        {/* Danger Zone */}
        <section className="rounded-xl border border-red-500/30 bg-red-500/5 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold text-red-600">
            <ShieldAlert className="h-5 w-5" /> Danger Zone
          </h2>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="font-medium text-[var(--text)]">Delete Account</p>
              <p className="text-sm text-[var(--text-muted)]">Permanently delete your account and all associated data.</p>
            </div>
            <button
              onClick={handleDeleteAccount}
              disabled={loading}
              className="rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 transition-colors disabled:opacity-50 whitespace-nowrap"
            >
              Delete Account
            </button>
          </div>
        </section>
      </div>
      </main>
      <SiteFooter />
    </div>
  );
}
