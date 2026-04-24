import type { NextConfig } from "next";
import withBundleAnalyzer from "@next/bundle-analyzer";

const HSTS_VALUE = 'max-age=31536000; includeSubDomains; preload';

// Build CSP connect-src from environment: include the WebSocket URL if set
function buildCsp(): string {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8001/ws';

  // Collect all WebSocket origins that should be allowed
  const wsOrigins = new Set<string>();

  // 1. Always include common dev ports — both localhost and 127.0.0.1 since
  //    browsers treat them as different origins. Handles cases where next.config
  //    doesn't reliably read .env.local at startup.
  const DEV_PORTS = ['8000', '8001'];
  for (const port of DEV_PORTS) {
    wsOrigins.add(`ws://localhost:${port}`);
    wsOrigins.add(`ws://127.0.0.1:${port}`);
  }

  // 2. Add the origin derived from NEXT_PUBLIC_WS_URL (may overlap with dev defaults)
  try {
    const u = new URL(wsUrl);
    const host = u.hostname;
    const port = u.port || '8000';
    wsOrigins.add(`ws://${host}:${port}`);
    // If the host is a non-local domain, also add it
    if (host !== 'localhost' && host !== '127.0.0.1') {
      wsOrigins.add(`wss://${host}:${port}`);
    }
  } catch {
    // Fallback already covered by dev ports above
  }

  return [
    "default-src 'self'",
    `connect-src 'self' ${[...wsOrigins].join(' ')}`,
    "img-src 'self' data: blob:",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
  ].join('; ');
}

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Content-Security-Policy', value: buildCsp() },
          ...(process.env.NODE_ENV === 'production'
            ? [{ key: 'Strict-Transport-Security', value: HSTS_VALUE }]
            : []),
        ],
      },
    ];
  },
};

export default withBundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
})(nextConfig);
