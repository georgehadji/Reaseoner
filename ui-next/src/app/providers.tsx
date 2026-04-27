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
      setAuthLoading(false);
      return;
    }

    // Register listener BEFORE any async calls so we don't miss the INITIAL_SESSION
    // event that fires after Supabase finishes processing the URL (including OAuth code exchange).
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
      if (event === 'INITIAL_SESSION') {
        setAuthLoading(false);
      }
    });

    return () => listener.subscription.unsubscribe();
  }, [setUser, setAuthLoading]);

  return <>{children}</>;
}
