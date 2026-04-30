import { supabase } from './supabase';

export interface AuthError {
  message: string;
  status?: number;
  code?: string;
}

function toAuthError(err: unknown): AuthError {
  if (err && typeof err === 'object') {
    const e = err as Record<string, unknown>;
    return {
      message: typeof e.message === 'string' ? e.message : 'An unexpected error occurred',
      status: typeof e.status === 'number' ? e.status : undefined,
      code: typeof e.code === 'string' ? e.code : undefined,
    };
  }
  return { message: 'An unexpected error occurred' };
}

function guardSupabase() {
  if (!supabase) {
    throw new Error('Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.');
  }
  return supabase;
}

export async function getSession() {
  const client = guardSupabase();
  const { data, error } = await client.auth.getSession();
  if (error) throw toAuthError(error);
  return data.session;
}

export async function getCurrentUser() {
  const client = guardSupabase();
  const { data, error } = await client.auth.getUser();
  if (error) throw toAuthError(error);
  return data.user;
}

export async function signInWithEmail(email: string, password: string) {
  const client = guardSupabase();
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw toAuthError(error);
  return data;
}

export async function signInWithOAuth(provider: 'google' | 'github') {
  const client = guardSupabase();
  const { data, error } = await client.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${window.location.origin}/chat`,
    },
  });
  if (error) throw toAuthError(error);
  return data;
}

export async function signUpWithEmail(email: string, password: string) {
  const client = guardSupabase();
  const { data, error } = await client.auth.signUp({ email, password });
  if (error) throw toAuthError(error);
  return data;
}

export async function signOut() {
  const client = guardSupabase();
  const { error } = await client.auth.signOut();
  if (error) throw toAuthError(error);
}

export async function getAuthToken(): Promise<string | null> {
  if (!supabase) return null;
  const session = await getSession();
  return session?.access_token ?? null;
}
