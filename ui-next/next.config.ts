import type { NextConfig } from "next";

const HSTS_VALUE = 'max-age=31536000; includeSubDomains; preload';

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          ...(process.env.NODE_ENV === 'production'
            ? [{ key: 'Strict-Transport-Security', value: HSTS_VALUE }]
            : []),
        ],
      },
    ];
  },
};

export default nextConfig;
