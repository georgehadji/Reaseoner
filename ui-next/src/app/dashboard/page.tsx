'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api-client';
import { useQuota } from '@/hooks/useQuota';

export default function DashboardPage() {
  const { quota } = useQuota();
  const [subscription, setSubscription] = useState<any>(null);

  useEffect(() => {
    apiFetch('/api/billing/subscription').then(r => r.json()).then(setSubscription);
  }, []);

  const openPortal = async () => {
    const res = await apiFetch('/api/billing/portal', { method: 'POST' });
    const data = await res.json();
    window.location.href = data.portal_url;
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border rounded-lg p-6">
          <h2 className="font-semibold mb-2">Current Plan</h2>
          <p className="text-lg capitalize">{subscription?.tier || 'Free'}</p>
          <button onClick={openPortal} className="mt-4 text-blue-600 underline">
            Manage Billing
          </button>
        </div>
        <div className="border rounded-lg p-6">
          <h2 className="font-semibold mb-2">Usage</h2>
          {quota && (
            <>
              <p>{quota.used} / {quota.max} queries</p>
              <div className="w-full bg-gray-200 rounded h-2 mt-2">
                <div
                  className="bg-blue-600 h-2 rounded"
                  style={{ width: `${(quota.used / quota.max) * 100}%` }}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
