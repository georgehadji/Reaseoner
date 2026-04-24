import { NextResponse } from 'next/server';
import { CSRF_COOKIE } from '@/lib/security-constants';
import { generateSignedCsrfToken } from '@/lib/security-server';
import { TIMING } from '@/lib/config';

export async function GET() {
  const token = await generateSignedCsrfToken();
  const response = NextResponse.json({ token });
  response.cookies.set(CSRF_COOKIE, token, {
    httpOnly: false,
    sameSite: 'strict',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: TIMING.csrfMaxAgeSeconds,
  });
  return response;
}
