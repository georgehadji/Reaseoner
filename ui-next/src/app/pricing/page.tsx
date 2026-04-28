'use client';

import { useState } from 'react';
import { apiFetch } from '@/lib/api-client';
import { Check, X, Shield, CreditCard, Clock } from 'lucide-react';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

const plans = [
  {
    name: 'Free',
    tier: 'free',
    price: '$0',
    period: 'forever',
    queries: '20 queries / month',
    features: [
      'Budget routing presets',
      'Basic web search',
      'Community support',
    ],
    notIncluded: [
      'Premium & Enterprise models',
      'Advanced analytics',
      'Priority support',
    ],
  },
  {
    name: 'Pro',
    tier: 'pro',
    price: '$12',
    period: '/ month',
    queries: '500 queries / month',
    features: [
      'All routing presets (Budget + Premium)',
      'Advanced multi-model consensus',
      'Deep research & iterative RAG',
      'Neuro memory & embedding search',
      'Priority email support',
    ],
    notIncluded: [
      'Custom model deployments',
      'Dedicated infrastructure',
    ],
    highlighted: true,
  },
  {
    name: 'Enterprise',
    tier: 'enterprise',
    price: '$49',
    period: '/ month',
    queries: 'Unlimited queries',
    features: [
      'Everything in Pro',
      'Custom model integrations',
      'Self-hosted deployment option',
      'Audit trails & compliance exports',
      '99.9% uptime SLA',
      'Dedicated support channel',
    ],
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
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-[var(--text)]">Simple, Transparent Pricing</h1>
          <p className="mt-2 text-[var(--text-muted)]">Start free. Scale with confidence. No hidden fees.</p>
        </div>

        {error && (
          <div className="mx-auto mb-6 max-w-lg rounded-lg bg-red-500/10 p-3 text-sm text-red-400" role="alert">
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
              className={`relative flex flex-col rounded-2xl border bg-[var(--surface)] p-6 transition-all ${
                plan.highlighted
                  ? 'border-[var(--border-strong)] shadow-[var(--shadow-lg)] ring-1 ring-blue-500/20'
                  : 'border-[var(--border)] hover:shadow-[var(--shadow-lg)]'
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[var(--accent)] px-3 py-0.5 text-xs font-semibold text-[var(--accent-text)]">
                  Recommended
                </div>
              )}

              <div className="mb-4">
                <h2 className="text-lg font-semibold text-[var(--text)]">{plan.name}</h2>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-[var(--text)]">{plan.price}</span>
                  <span className="text-sm text-[var(--text-muted)]">{plan.period}</span>
                </div>
                <p className="mt-1 text-sm text-[var(--text-muted)]">{plan.queries}</p>
              </div>

              <ul className="mb-4 flex-1 space-y-2.5 text-left text-sm text-[var(--text-2)]">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />
                    <span>{f}</span>
                  </li>
                ))}
                {plan.notIncluded?.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-[var(--text-subtle)]">
                    <X className="mt-0.5 h-4 w-4 shrink-0" />
                    <span className="line-through opacity-60">{f}</span>
                  </li>
                ))}
              </ul>

              {plan.tier !== 'free' && (
                <button
                  onClick={() => handleUpgrade(plan.tier)}
                  disabled={!!loadingTier}
                  className={`w-full rounded-xl py-2.5 font-medium transition-all disabled:opacity-40 ${
                    plan.highlighted
                      ? 'bg-[var(--accent)] text-[var(--accent-text)] hover:opacity-90'
                      : 'border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text)] hover:bg-[var(--surface-3)]'
                  }`}
                  aria-busy={loadingTier === plan.tier}
                >
                  {loadingTier === plan.tier ? 'Loading…' : plan.tier === 'enterprise' ? 'Contact Sales' : 'Upgrade'}
                </button>
              )}
              {plan.tier === 'free' && (
                <button
                  disabled
                  className="w-full cursor-default rounded-xl border border-[var(--border)] bg-[var(--surface-2)] py-2.5 font-medium text-[var(--text-muted)]"
                >
                  Current Plan
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Trust badges */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-[var(--text-subtle)]">
          <div className="flex items-center gap-1.5">
            <Shield className="h-4 w-4" />
            <span>Secure Stripe checkout</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CreditCard className="h-4 w-4" />
            <span>Cancel anytime</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            <span>14-day money-back guarantee</span>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
