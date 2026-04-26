'use client';

import { useState } from 'react';
import { apiFetch } from '@/lib/api-client';
import { Check, X } from 'lucide-react';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

const plans = [
  {
    name: 'Free',
    tier: 'free',
    price: '$0',
    queries: '20 / month',
    features: ['Budget presets only', 'Basic support'],
  },
  {
    name: 'Pro',
    tier: 'pro',
    price: '$12/mo',
    queries: '500 / month',
    features: ['All presets', 'Priority support', 'Advanced analytics'],
  },
  {
    name: 'Enterprise',
    tier: 'enterprise',
    price: '$49/mo',
    queries: 'Unlimited',
    features: ['Custom models', 'SLA', 'Dedicated support'],
  },
];

function isValidCheckoutUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' && u.hostname.endsWith('.stripe.com');
  } catch {
    return false;
  }
}

export default function PricingPage() {
  const [loadingTier, setLoadingTier] = useState<string | null>(null);
  const [error, setError] = useState('');

  const handleUpgrade = async (tier: string) => {
    setError('');
    setLoadingTier(tier);
    try {
      const res = await apiFetch(`/api/billing/checkout?tier=${encodeURIComponent(tier)}`, {
        method: 'POST',
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Checkout failed (HTTP ${res.status})`);
      }
      const data = await res.json();
      const url = data.checkout_url;
      if (!url || typeof url !== 'string' || !isValidCheckoutUrl(url)) {
        throw new Error('Invalid checkout URL received');
      }
      window.location.href = url;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Checkout failed';
      setError(msg);
      setLoadingTier(null);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-4 py-12 flex-1 w-full">
        <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-[var(--text)]">Choose Your Plan</h1>
        <p className="mt-2 text-[var(--text-muted)]">Upgrade to unlock more queries and premium features</p>
      </div>

      {error && (
        <div className="mx-auto mb-6 max-w-lg rounded-lg bg-red-500/10 p-3 text-sm text-red-600" role="alert">
          <div className="flex items-center gap-2">
            <X className="h-4 w-4 shrink-0" />
            {error}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center transition-shadow hover:shadow-[var(--shadow-lg)]"
          >
            <h2 className="text-xl font-semibold text-[var(--text)]">{plan.name}</h2>
            <p className="my-2 text-3xl font-bold text-[var(--text)]">{plan.price}</p>
            <p className="mb-4 text-sm text-[var(--text-muted)]">{plan.queries}</p>
            <ul className="mb-6 flex-1 space-y-2 text-left text-sm text-[var(--text-2)]">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                  {f}
                </li>
              ))}
            </ul>
            {plan.tier !== 'free' && (
              <button
                onClick={() => handleUpgrade(plan.tier)}
                disabled={!!loadingTier}
                className="w-full rounded-lg bg-[var(--accent)] py-2.5 text-[var(--accent-text)] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
                aria-busy={loadingTier === plan.tier}
              >
                {loadingTier === plan.tier ? 'Loading…' : 'Upgrade'}
              </button>
            )}
            {plan.tier === 'free' && (
              <button
                disabled
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] py-2.5 text-[var(--text-muted)] font-medium cursor-default"
              >
                Current Plan
              </button>
            )}
          </div>
        ))}
      </div>
      </main>
      <SiteFooter />
    </div>
  );
}
