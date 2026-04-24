import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { CSRF_COOKIE, CSRF_HEADER } from '@/lib/security-constants';
import { generateSignedCsrfToken, verifyCsrfToken } from '@/lib/security-server';

const HSTS_VALUE = 'max-age=31536000; includeSubDomains; preload';

function buildConnectSrc(): string {
  const wsOrigins = new Set<string>();
  for (const port of ['8000', '8001']) {
    wsOrigins.add(`ws://localhost:${port}`);
    wsOrigins.add(`ws://127.0.0.1:${port}`);
  }
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || '';
  if (wsUrl) {
    try {
      const u = new URL(wsUrl);
      const port = u.port || '8000';
      wsOrigins.add(`ws://${u.hostname}:${port}`);
      if (u.hostname !== 'localhost' && u.hostname !== '127.0.0.1') {
        wsOrigins.add(`wss://${u.hostname}:${port}`);
      }
    } catch { /* fall back to dev defaults */ }
  }
  return `connect-src 'self' ${[...wsOrigins].join(' ')}`;
}

export async function proxy(request: NextRequest) {
  const response = NextResponse.next();

  const scriptSrc = process.env.NODE_ENV === 'production'
    ? "script-src 'self'"
    : "script-src 'self' 'unsafe-inline' 'unsafe-eval'";
  const csp = [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    buildConnectSrc(),
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');

  response.headers.set('Content-Security-Policy', csp);
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

  if (process.env.NODE_ENV === 'production') {
    response.headers.set('Strict-Transport-Security', HSTS_VALUE);
  }

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method)) {
    const header = request.headers.get(CSRF_HEADER) || '';
    const cookie = request.cookies.get(CSRF_COOKIE)?.value || '';
    if (!header || !cookie) {
      return new NextResponse(JSON.stringify({ error: 'Invalid or missing CSRF token' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    const headerValid = await verifyCsrfToken(header);
    const cookieValid = await verifyCsrfToken(cookie);
    if (!headerValid || !cookieValid || header !== cookie) {
      return new NextResponse(JSON.stringify({ error: 'Invalid or missing CSRF token' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  if (!request.cookies.get(CSRF_COOKIE)) {
    const token = await generateSignedCsrfToken();
    response.cookies.set(CSRF_COOKIE, token, {
      httpOnly: false,
      sameSite: 'strict',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: 60 * 60 * 24,
    });
  }

  return response;
}

export const config = {
  matcher: ['/api/:path*', '/((?!_next/|__webpack|favicon.ico|.*\\.).*)'],
};
