'use client';

import { CSRF_COOKIE, CSRF_HEADER } from './security-constants';
import { getAuthToken } from './auth';

export function getCsrfToken(): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + CSRF_COOKIE + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

export async function fetchWithCsrf(url: string, options: RequestInit = {}): Promise<Response> {
  async function getToken(forceRefresh = false): Promise<string | null> {
    if (!forceRefresh) {
      const cached = getCsrfToken();
      if (cached) return cached;
    }
    const resp = await fetch('/api/csrf');
    if (resp.ok) {
      const data = await resp.json();
      return data.token as string | null;
    }
    return null;
  }

  const token = await getToken();
  const headers = new Headers(options.headers);
  if (token) {
    headers.set(CSRF_HEADER, token);
  }

  // Inject Supabase auth token if available
  const authToken = await getAuthToken();
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }

  const resp = await fetch(url, { ...options, headers });

  // Redirect to login on auth failure
  if (resp.status === 401) {
    window.location.href = '/login';
    // Return a never-resolving promise to prevent callers from continuing
    // while the browser navigates away
    return new Promise(() => {});
  }

  // If CSRF validation failed (stale/invalid token), fetch a fresh one and retry once
  if (resp.status === 403) {
    const data = await resp.json().catch(() => null);
    const raw = (data && typeof data === 'object')
      ? (typeof data.error === 'string' ? data.error : typeof data.detail === 'string' ? data.detail : '')
      : '';
    const errorMsg = raw.toLowerCase();
    if (errorMsg.includes('csrf')) {
      const freshToken = await getToken(true);
      if (freshToken) {
        headers.set(CSRF_HEADER, freshToken);
        return fetch(url, { ...options, headers });
      }
    }
  }

  return resp;
}
