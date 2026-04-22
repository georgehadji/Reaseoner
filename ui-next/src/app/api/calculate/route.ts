import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
  readJsonBody,
  validateCalculateRequest,
  rateLimit,
  ValidationError,
} from '@/lib/security-server';

export async function POST(req: NextRequest) {
  try {
    const limit = rateLimit(req, 'calculate');
    if (!limit.allowed) {
      return new NextResponse('Too Many Requests', {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfter) },
      });
    }

    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    const body = await readJsonBody(req);
    const payload = validateCalculateRequest(body);

    const headers = new Headers(sanitizeRequestHeaders(req.headers));
    headers.set('Content-Type', 'application/json');
    const upstream = await fetch(`${apiBase}/api/calculate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: sanitizeResponseHeaders(upstream),
    });
  } catch (err) {
    if (err instanceof ValidationError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    const msg = err instanceof Error ? err.message : 'Proxy error';
    return NextResponse.json({ error: msg }, { status: 400 });
  }
}
