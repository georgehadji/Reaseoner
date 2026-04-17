import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
  readJsonBody,
  rateLimit,
} from '@/lib/security-server';

export async function POST(req: NextRequest) {
  try {
    const limit = rateLimit(req, 'run');
    if (!limit.allowed) {
      return new NextResponse('Too Many Requests', {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfter) },
      });
    }

    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    const body = await readJsonBody(req);

    const headers = sanitizeRequestHeaders(req.headers);
    const upstream = await fetch(`${apiBase}/api/run-followup`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (upstream.status === 422) {
      const clone = upstream.clone();
      const text = await clone.text().catch(() => '');
      // eslint-disable-next-line no-console
      console.error('Upstream 422 response body:', text);
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers: sanitizeResponseHeaders(upstream),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Proxy error';
    return NextResponse.json({ error: msg }, { status: 400 });
  }
}
