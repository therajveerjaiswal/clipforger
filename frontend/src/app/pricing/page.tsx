'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { getBackendUrl } from '@/lib/utils';
import { Crown, Check, Loader2, ArrowRight } from 'lucide-react';

declare global {
  interface Window {
    Razorpay: any;
  }
}

export default function PricingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubscribePro = async () => {
    setLoading(true);
    setErrorMsg(null);

    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const session = sessionData?.session;

      if (!session) {
        await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: { redirectTo: `${window.location.origin}/pricing` },
        });
        return;
      }

      const backendUrl = getBackendUrl();

      // 1. Create subscription order on backend
      const res = await fetch(`${backendUrl}/api/v1/payments/create-subscription`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          plan_tier: 'pro',
          billing_cycle: 'monthly',
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to initiate payment.');
      }

      const subOrder = await res.json();

      // 2. Open Razorpay Checkout Modal
      const options = {
        key: subOrder.key_id,
        subscription_id: subOrder.subscription_id,
        name: 'ClipForge AI',
        description: 'Pro Streamer Subscription (₹499/month)',
        handler: async function (response: any) {
          try {
            const verifyRes = await fetch(`${backendUrl}/api/v1/payments/verify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.access_token}`,
              },
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_subscription_id: response.razorpay_subscription_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });

            if (verifyRes.ok) {
              router.push('/dashboard?upgraded=true');
            } else {
              setErrorMsg('Payment verification failed. Please contact support.');
            }
          } catch (err: any) {
            setErrorMsg(err.message || 'Error verifying payment.');
          }
        },
        prefill: {
          email: session.user.email,
          name: session.user.user_metadata?.full_name || '',
        },
        theme: {
          color: '#6366F1',
        },
      };

      if (window.Razorpay) {
        const rzp = new window.Razorpay(options);
        rzp.open();
      } else {
        throw new Error('Razorpay SDK failed to load. Please refresh the page.');
      }
    } catch (err: any) {
      console.error('Subscription error:', err);
      setErrorMsg(err.message || 'Payment could not be started.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-12 px-4 sm:px-8 max-w-5xl mx-auto">
      <div className="text-center max-w-2xl mx-auto mb-12">
        <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 px-3 py-1 text-xs font-semibold text-amber-400 mb-3">
          <Crown className="h-3.5 w-3.5" /> High-Performance Gaming Studio
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Level Up Your Gaming Content
        </h1>
        <p className="text-xs sm:text-sm text-gray-400 mt-2">
          Export higher resolution 1080p 60fps clips, jump to the front of the worker queue, and remove all advertisements.
        </p>
      </div>

      {errorMsg && (
        <div className="mb-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 p-4 text-xs text-rose-400 text-center max-w-lg mx-auto">
          {errorMsg}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch max-w-4xl mx-auto">
        {/* Free Plan */}
        <div className="rounded-3xl border border-surfaceBorder bg-surface p-8 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-gray-400">
              Starter
            </span>
            <h3 className="text-2xl font-bold text-white mt-1">Free Creator</h3>
            <div className="mt-4 flex items-baseline">
              <span className="text-3xl font-extrabold text-white">₹0</span>
              <span className="text-xs text-gray-400 ml-1">/ forever</span>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              For casual gaming creators making a few reels per week.
            </p>

            <ul className="mt-6 space-y-3 text-xs text-gray-300">
              <li className="flex items-center gap-2.5">
                <Check className="h-4 w-4 text-emerald-400" /> Max 10 reels generated per day
              </li>
              <li className="flex items-center gap-2.5">
                <Check className="h-4 w-4 text-emerald-400" /> Max 3 long streams per day
              </li>
              <li className="flex items-center gap-2.5">
                <Check className="h-4 w-4 text-emerald-400" /> 720p vertical video exports
              </li>
              <li className="flex items-center gap-2.5">
                <Check className="h-4 w-4 text-emerald-400" /> Automated karaoke subtitles
              </li>
              <li className="flex items-center gap-2.5 text-gray-500">
                • Non-intrusive dashboard ad banners
              </li>
            </ul>
          </div>

          <button
            onClick={() => router.push('/dashboard')}
            className="mt-8 w-full rounded-2xl border border-surfaceBorder bg-background py-3 text-xs font-bold text-white hover:bg-surfaceBorder transition-all"
          >
            Continue with Free Tier
          </button>
        </div>

        {/* Pro Plan */}
        <div className="relative rounded-3xl border-2 border-brand-500 bg-gradient-to-b from-brand-950/40 to-surface p-8 flex flex-col justify-between shadow-2xl shadow-brand-500/10">
          <div className="absolute -top-3.5 right-6 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 px-3.5 py-1 text-[11px] font-bold text-black uppercase tracking-wider">
            Most Popular
          </div>

          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
              <Crown className="h-3.5 w-3.5" /> Professional
            </span>
            <h3 className="text-2xl font-bold text-white mt-1">Pro Streamer</h3>
            <div className="mt-4 flex items-baseline">
              <span className="text-4xl font-extrabold text-white">₹499</span>
              <span className="text-xs text-gray-400 ml-1">/ month</span>
            </div>
            <p className="text-xs text-gray-300 mt-2">
              Direct Indian bank settlement via Razorpay. Cancel anytime.
            </p>

            <ul className="mt-6 space-y-3 text-xs text-gray-200">
              <li className="flex items-center gap-2.5 font-medium">
                <Check className="h-4 w-4 text-amber-400" /> Unlimited daily reels & long streams
              </li>
              <li className="flex items-center gap-2.5 font-medium">
                <Check className="h-4 w-4 text-amber-400" /> 1080p 60fps high bitrate exports
              </li>
              <li className="flex items-center gap-2.5 font-medium">
                <Check className="h-4 w-4 text-amber-400" /> Dedicated priority worker queue
              </li>
              <li className="flex items-center gap-2.5 font-medium">
                <Check className="h-4 w-4 text-amber-400" /> 100% Ad-free experience
              </li>
              <li className="flex items-center gap-2.5 font-medium">
                <Check className="h-4 w-4 text-amber-400" /> Custom subtitle typography & branding
              </li>
            </ul>
          </div>

          <button
            onClick={handleSubscribePro}
            disabled={loading}
            className="mt-8 w-full flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 py-3.5 text-xs font-bold text-black shadow-lg shadow-amber-500/25 hover:brightness-110 active:scale-[0.99] disabled:opacity-50 transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Connecting Razorpay...
              </>
            ) : (
              <>
                Upgrade to Pro (₹499/mo) <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
