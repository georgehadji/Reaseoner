import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
  readJsonBody,
  validateRunFollowupRequest,
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
    const limit = rateLimit(req, 'run');
    if (!limit.allowed) {
      return new NextResponse('Too Many Requests', {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfter) },
      });
    }

    await requireCsrfToken(req);
    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    upstreamUrl = `${apiBase}/api/run-followup`;
    const body = await readJsonBody(req);
    const payload = validateRunFollowupRequest(body);

    const headers = sanitizeRequestHeaders(req.headers);
    const upstream = await fetch(upstreamUrl, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
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
    if (err instanceof ValidationError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }

    const msg = err instanceof Error ? err.message : 'Proxy error';
    const errName = err instanceof Error ? err.constructor.name : 'Unknown';

    // Log connection details for debugging
    // eslint-disable-next-line no-console
    console.error(`Proxy error [${errName}] upstream=${upstreamUrl || 'N/A'}:`, msg);

    // Connection-level errors (network, DNS, timeout) → 504 Gateway Timeout
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
