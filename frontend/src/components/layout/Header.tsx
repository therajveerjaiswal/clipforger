'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabaseClient';
import { useQuota } from '@/hooks/useQuota';
import { Flame, Crown, LogIn, LogOut } from 'lucide-react';

export const Header: React.FC = () => {
  const [user, setUser] = useState<any>(null);
  const { quota } = useQuota();

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      listener.subscription.unsubscribe();
    };
  }, []);

  const handleGoogleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.href = '/';
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-surfaceBorder bg-background/80 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-4 sm:px-8 max-w-7xl mx-auto">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-accent-cyan shadow-lg shadow-brand-500/20">
            <Flame className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white">
            Clip<span className="text-brand-400">Forge</span>
          </span>
        </Link>

        {/* Right Section: Quotas & Auth */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              {/* Daily Quota Badge */}
              {quota && (
                <div className="hidden sm:flex items-center gap-2 rounded-full border border-surfaceBorder bg-surface px-3 py-1 text-xs">
                  {quota.tier === 'pro' ? (
                    <span className="flex items-center gap-1 font-semibold text-amber-400">
                      <Crown className="h-3.5 w-3.5" /> PRO ACTIVE
                    </span>
                  ) : (
                    <span className="text-gray-400">
                      Reels Today: <strong className="text-white">{quota.remaining_reels_today}/10</strong>
                    </span>
                  )}
                </div>
              )}

              {/* Upgrade CTA */}
              {quota?.tier !== 'pro' && (
                <Link
                  href="/pricing"
                  className="hidden sm:flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 px-3.5 py-1.5 text-xs font-semibold text-black shadow-md shadow-amber-500/20 hover:brightness-110 transition-all"
                >
                  <Crown className="h-3.5 w-3.5" /> Upgrade Pro
                </Link>
              )}

              {/* User Menu */}
              <div className="flex items-center gap-2">
                {user.user_metadata?.avatar_url ? (
                  <img
                    src={user.user_metadata.avatar_url}
                    alt={user.email || 'User'}
                    className="h-8 w-8 rounded-full border border-surfaceBorder"
                  />
                ) : (
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface text-xs font-bold text-gray-300">
                    {user.email?.charAt(0).toUpperCase()}
                  </div>
                )}

                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="rounded-lg p-1.5 text-gray-400 hover:bg-surface hover:text-white transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </>
          ) : (
            <button
              onClick={handleGoogleLogin}
              className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-brand-500/25 hover:bg-brand-500 transition-all"
            >
              <LogIn className="h-4 w-4" /> Sign In with Google
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
