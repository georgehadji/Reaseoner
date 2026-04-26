'use client';

import { useEffect } from 'react';
import { ThemeProvider } from 'next-themes';
import { supabase } from '@/lib/supabase';
import { useAppStore } from '@/stores/app-store';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <AuthProvider>{children}</AuthProvider>
    </ThemeProvider>
  );
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const setUser = useAppStore((s) => s.setUser);
  const setAuthLoading = useAppStore((s) => s.setAuthLoading);

  useEffect(() => {
    if (!supabase) {
      // Supabase not configured — skip auth initialization
      setAuthLoading(false);
      return;
    }

    // Initial auth check — use getUser() to validate JWT with Supabase server
    // (getSession() only reads from localStorage and does not verify the token)
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user ?? null);
      setAuthLoading(false);
    });

    // Listen for auth state changes
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => listener.subscription.unsubscribe();
  }, [setUser, setAuthLoading]);

  return <>{children}</>;
}
