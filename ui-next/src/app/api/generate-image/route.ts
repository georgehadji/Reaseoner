import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
  readJsonBody,
  requireCsrfToken,
  rateLimit,
  ValidationError,
} from '@/lib/security-server';

export async function POST(req: NextRequest) {
  try {
    const limit = rateLimit(req, 'generate-image');
    if (!limit.allowed) {
      return new NextResponse('Too Many Requests', {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfter) },
      });
    }

    await requireCsrfToken(req);
    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    const body = await readJsonBody(req);

    const headers = new Headers(sanitizeRequestHeaders(req.headers));
    headers.set('Content-Type', 'application/json');
    const upstream = await fetch(`${apiBase}/api/generate-image`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: sanitizeResponseHeaders(upstream),
    });
  } catch (err) {
    if (err instanceof ValidationError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    console.error('Generate image proxy error:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
