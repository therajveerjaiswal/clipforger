'use client';

import React from 'react';
import Link from 'next/link';
import { Crown, Sparkles } from 'lucide-react';
import { useQuota } from '@/hooks/useQuota';

interface AdSlotProps {
  slotType: 'banner' | 'card' | 'modal';
  className?: string;
}

export const AdSlot: React.FC<AdSlotProps> = ({ slotType, className = '' }) => {
  const { quota } = useQuota();

  // If user is Pro, completely suppress all advertising
  if (quota?.tier === 'pro') {
    return null;
  }

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-surfaceBorder bg-gradient-to-r from-surface to-surface/80 p-4 text-center ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-left">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                Sponsor / Upgrade
              </span>
              <span className="rounded bg-brand-500/20 px-1.5 py-0.2 text-[9px] font-semibold text-brand-300">
                Ad
              </span>
            </div>
            <p className="text-sm font-semibold text-white">
              Want 1080p60 Exports & Priority Queue with Zero Ads?
            </p>
          </div>
        </div>

        <Link
          href="/pricing"
          className="flex items-center gap-1.5 rounded-xl bg-amber-500 px-4 py-2 text-xs font-bold text-black shadow-md shadow-amber-500/20 hover:bg-amber-400 transition-all shrink-0"
        >
          <Crown className="h-3.5 w-3.5" /> Remove Ads (₹499/mo)
        </Link>
      </div>
    </div>
  );
};
