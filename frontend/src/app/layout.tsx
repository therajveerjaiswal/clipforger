import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';
import { Header } from '@/components/layout/Header';
import { MobileNavBar } from '@/components/layout/MobileNavBar';

export const metadata: Metadata = {
  title: 'ClipForge AI - Gaming Stream Highlight & Reel Clipper',
  description: 'Convert massive 20 to 30-hour gaming livestreams into viral 9:16 vertical reels with styled karaoke subtitles.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-background text-foreground antialiased selection:bg-brand-500 selection:text-white">
        {/* Razorpay standard checkout script */}
        <Script
          src="https://checkout.razorpay.com/v1/checkout.js"
          strategy="afterInteractive"
        />
        <Header />
        <main className="flex-1 pb-20 lg:pb-8">{children}</main>
        <MobileNavBar />
      </body>
    </html>
  );
}
