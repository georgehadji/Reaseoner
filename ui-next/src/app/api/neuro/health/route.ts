import { NextResponse } from 'next/server';
import { REASONER_API_BASE } from '@/lib/server-config';

export async function GET(request: Request) {
  try {
    const upstream = new URL(`${REASONER_API_BASE}/neuro/health`);

    const resp = await fetch(upstream.toString(), {
      headers: {
        cookie: request.headers.get('cookie') || '',
      },
    });

    if (resp.status === 404) {
      // Neuro router not mounted in running backend — return graceful fallback
      return NextResponse.json({
        status: 'unavailable',
        version: 'unknown',
        timestamp: new Date().toISOString(),
        reasoning: { healthy: false },
        embedding: { healthy: false },
        agents_configured: [],
        default_persona: 'default',
        sessions: { hot: 0, warm: 0, cold: 0 },
      });
    }

    return new Response(resp.body, {
      status: resp.status,
      headers: resp.headers,
    });
  } catch {
    return NextResponse.json({
      status: 'unavailable',
      version: 'unknown',
      timestamp: new Date().toISOString(),
      reasoning: { healthy: false },
      embedding: { healthy: false },
      agents_configured: [],
      default_persona: 'default',
      sessions: { hot: 0, warm: 0, cold: 0 },
    }, { status: 503 });
  }
}
