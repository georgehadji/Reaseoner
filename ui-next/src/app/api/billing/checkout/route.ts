import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
} from '@/lib/security-server';

export async function POST(req: NextRequest) {
  try {
    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    const { searchParams } = new URL(req.url);
    
    // Extract tier and provider from query params
    let tier = searchParams.get('tier');
    let provider = searchParams.get('provider');

    // If not in query params, try to read from JSON body (for UpgradeModal)
    if (!tier) {
      try {
        const body = await req.json();
        tier = body.tier;
        if (!provider) provider = body.provider;
      } catch {
        // Body might be empty or not JSON, ignore
      }
    }

    if (!tier) {
      return NextResponse.json({ detail: 'Missing tier parameter' }, { status: 400 });
    }

    const upstreamUrl = new URL(`${apiBase}/api/billing/checkout`);
    upstreamUrl.searchParams.set('tier', tier);
    if (provider) upstreamUrl.searchParams.set('provider', provider);

    const headers = sanitizeRequestHeaders(req.headers);
    const upstream = await fetch(upstreamUrl.toString(), {
      method: 'POST',
      headers,
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: sanitizeResponseHeaders(upstream),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Proxy error';
    return NextResponse.json({ detail: msg }, { status: 502 });
  }
}
