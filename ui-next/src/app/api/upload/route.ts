import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
  requireCsrfToken,
  rateLimit,
  ValidationError,
  SECURITY_SERVER_HASH,
} from '@/lib/security-server';

// Touch SECURITY_SERVER_HASH so Turbopack recompiles this route when it changes.
void SECURITY_SERVER_HASH;

export async function POST(req: NextRequest) {
  let upstreamUrl: string | undefined;
  try {
    const limit = rateLimit(req, 'upload');
    if (!limit.allowed) {
      return new NextResponse('Too Many Requests', {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfter) },
      });
    }

    await requireCsrfToken(req);
    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    upstreamUrl = `${apiBase}/api/upload`;

    // Forward the multipart body directly — do NOT parse it in Next.js
    const headers = sanitizeRequestHeaders(req.headers);
    const upstream = await fetch(upstreamUrl, {
      method: 'POST',
      headers,
      body: req.body,
      // @ts-expect-error — duplex is required for streaming request bodies in Node 18+
      duplex: 'half',
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
    const errName = err instanceof Error ? err.constructor.name : 'Unknown';

    // eslint-disable-next-line no-console
    console.error(`Upload proxy error [${errName}] upstream=${upstreamUrl || 'N/A'}:`, msg);

    const isConnectionError =
      err instanceof TypeError ||
      msg.toLowerCase().includes('fetch failed') ||
      msg.toLowerCase().includes('network') ||
      msg.toLowerCase().includes('econnrefused') ||
      msg.toLowerCase().includes('etimedout');

    if (isConnectionError) {
      return NextResponse.json(
        { error: 'Backend unreachable', detail: msg },
        { status: 504 }
      );
    }

    return NextResponse.json({ error: msg }, { status: 400 });
  }
}
