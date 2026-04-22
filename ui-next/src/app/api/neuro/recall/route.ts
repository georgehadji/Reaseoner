import { NextRequest, NextResponse } from 'next/server';
import { REASONER_API_BASE } from '@/lib/server-config';

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${REASONER_API_BASE}/neuro/recall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return NextResponse.json(await res.json());
}
