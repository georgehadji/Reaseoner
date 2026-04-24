import { NextRequest, NextResponse } from 'next/server';
import {
  getApiBaseUrl,
  validateUpstreamUrl,
  sanitizeRequestHeaders,
  sanitizeResponseHeaders,
} from '@/lib/security-server';

export async function GET(req: NextRequest) {
  try {
    const location = req.nextUrl.searchParams.get('location');
    if (!location || location.length > 100 || !/[\p{L}\p{N}\s,.\-]+/u.test(location)) {
      return NextResponse.json({ error: 'Invalid location parameter' }, { status: 400 });
    }

    const apiBase = validateUpstreamUrl(getApiBaseUrl());
    const headers = sanitizeRequestHeaders(req.headers);
    const upstream = await fetch(
      `${apiBase}/api/weather?location=${encodeURIComponent(location)}`,
      { headers }
    );

    return new Response(upstream.body, {
      status: upstream.status,
      headers: sanitizeResponseHeaders(upstream),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Proxy error';
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
