import { REASONER_API_BASE } from '@/lib/server-config';

export async function GET(request: Request) {
  const upstream = new URL(`${REASONER_API_BASE}/neuro/health`);

  const resp = await fetch(upstream.toString(), {
    headers: {
      cookie: request.headers.get('cookie') || '',
    },
  });

  return new Response(resp.body, {
    status: resp.status,
    headers: resp.headers,
  });
}
