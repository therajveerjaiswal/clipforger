'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Film, Crown, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

export const MobileNavBar: React.FC = () => {
  const pathname = usePathname();

  const navItems = [
    { label: 'Home', href: '/', icon: Home },
    { label: 'Studio', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Clips', href: '/dashboard#clips', icon: Film },
    { label: 'Pro', href: '/pricing', icon: Crown },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-surfaceBorder bg-background/95 backdrop-blur-lg lg:hidden px-2">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.label}
            href={item.href}
            className={cn(
              'flex flex-col items-center justify-center gap-1 px-3 py-1 text-[11px] font-medium transition-all',
              isActive ? 'text-brand-400 font-bold' : 'text-gray-400 hover:text-white'
            )}
          >
            <Icon className={cn('h-5 w-5', isActive && 'text-brand-400')} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
};
