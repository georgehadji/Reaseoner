'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api-client';

const plans = [
  { name: 'Free', price: '$0', queries: '20 / month', features: ['Budget presets only', 'Basic support'] },
  { name: 'Pro', price: '$12/mo', queries: '500 / month', features: ['All presets', 'Priority support', 'Advanced analytics'] },
  { name: 'Enterprise', price: '$49/mo', queries: 'Unlimited', features: ['Custom models', 'SLA', 'Dedicated support'] },
];

export default function PricingPage() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleUpgrade = async (tier: string) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/billing/checkout?tier=${encodeURIComponent(tier)}`, {
        method: 'POST',
      });
      const data = await res.json();
      window.location.href = data.checkout_url;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold text-center mb-8">Choose Your Plan</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => (
          <div key={plan.name} className="border rounded-lg p-6 text-center">
            <h2 className="text-xl font-semibold">{plan.name}</h2>
            <p className="text-2xl font-bold my-2">{plan.price}</p>
            <p className="text-gray-600 mb-4">{plan.queries}</p>
            <ul className="text-sm text-left space-y-2 mb-6">
              {plan.features.map((f) => (
                <li key={f}>✓ {f}</li>
              ))}
            </ul>
            {plan.name !== 'Free' && (
              <button
                onClick={() => handleUpgrade(plan.name.toLowerCase())}
                disabled={loading}
                className="w-full py-2 bg-blue-600 text-white rounded disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Upgrade'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
