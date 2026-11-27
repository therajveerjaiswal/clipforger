'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { Loader2 } from 'lucide-react';

function resolveSafeNextPath(): string {
  if (typeof window === 'undefined') return '/dashboard';
  const params = new URLSearchParams(window.location.search);
  const next = params.get('next') || '/dashboard';
  // Only allow safe same-origin relative paths
  return next.startsWith('/') && !next.startsWith('//') ? next : '/dashboard';
}

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    let active = true;
    const targetPath = resolveSafeNextPath();

    const completeAuth = async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        if (code) {
          await supabase.auth.exchangeCodeForSession(code);
        } else {
          // Wait briefly for implicit hash-fragment session detection if present
          await supabase.auth.getSession();
        }
      } catch (err) {
        console.error('Auth callback error:', err);
      } finally {
        if (active) {
          router.replace(targetPath);
        }
      }
    };

    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN' && active) {
        router.replace(targetPath);
      }
    });

    completeAuth();

    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, [router]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-xs text-gray-400">
      <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      <span>Completing sign-in...</span>
    </div>
  );
}
