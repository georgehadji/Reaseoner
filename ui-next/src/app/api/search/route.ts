import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
  readJsonBody,
  validateSearchRequest,
  requireCsrfToken,
  rateLimit,
  ValidationError,
} from '@/lib/security-server';
import { API } from '@/lib/config';

export async function POST(req: NextRequest) {
  try {
    const limit = rateLimit(req, 'search');
    if (!limit.allowed) {
      return new NextResponse('Too Many Requests', {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfter) },
      });
    }

    await requireCsrfToken(req);
    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    const body = await readJsonBody(req);
    const payload = validateSearchRequest(body);

    const headers = new Headers(sanitizeRequestHeaders(req.headers));
    headers.set('Content-Type', 'application/json');
    const upstream = await fetch(`${apiBase}${API.SEARCH}`, {
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
    console.error('Search proxy error:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
