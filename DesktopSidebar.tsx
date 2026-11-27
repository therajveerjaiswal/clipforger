'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Film, CreditCard, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export const DesktopSidebar: React.FC = () => {
  const pathname = usePathname();

  const links = [
    { label: 'Create Reels', href: '/dashboard', icon: LayoutDashboard },
    { label: 'My Highlight Library', href: '/dashboard#clips', icon: Film },
    { label: 'Pro Membership', href: '/pricing', icon: CreditCard },
  ];

  return (
    <aside className="hidden lg:flex w-64 flex-col border-r border-surfaceBorder bg-surface/50 p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-gray-500">
          Studio Navigation
        </p>
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.label}
              href={link.href}
              className={cn(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all',
                isActive
                  ? 'bg-brand-600/15 text-brand-400 border border-brand-500/20 shadow-sm'
                  : 'text-gray-400 hover:bg-surface hover:text-white'
              )}
            >
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
      </div>

      <div className="mt-auto rounded-2xl border border-surfaceBorder bg-surface p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
          <ShieldCheck className="h-4 w-4" /> Anti-Abuse Protected
        </div>
        <p className="mt-1 text-[11px] text-gray-400">
          Hardware &amp; IP rate limiting is active. 3 long streams &amp; 10 reels/day on Free tier.
        </p>
      </div>
    </aside>
  );
};
