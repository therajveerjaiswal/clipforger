'use client';

import React from 'react';
import Link from 'next/link';
import { Flame, Sparkles, Zap, Shield, Crown, ArrowRight, Check } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center px-4 sm:px-8 py-12 max-w-6xl mx-auto">
      {/* Hero Badge */}
      <div className="inline-flex items-center gap-2 rounded-full border border-brand-500/30 bg-brand-500/10 px-4 py-1.5 text-xs font-semibold text-brand-300 mb-6">
        <Sparkles className="h-4 w-4" /> Built for Gaming Streamers & Reel Makers
      </div>

      {/* Hero Headline */}
      <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-center text-white max-w-4xl leading-tight">
        Turn Massive <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-accent-cyan">20–30hr Gaming Streams</span> into Viral Vertical Reels in Seconds.
      </h1>

      <p className="mt-4 text-sm sm:text-lg text-gray-400 text-center max-w-2xl">
        Stop downloading 60GB stream files. ClipForge uses surgical stream cutting and audio excitation analysis to find clutches, screams, and teamfights, then exports 9:16 reels with burning karaoke subtitles.
      </p>

      {/* CTA Buttons */}
      <div className="mt-8 flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
        <Link
          href="/dashboard"
          className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-600 to-accent-cyan px-8 py-4 text-sm font-bold text-white shadow-xl shadow-brand-500/25 hover:brightness-110 transition-all"
        >
          <Flame className="h-5 w-5" /> Start Clipping Free <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          href="/pricing"
          className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-2xl border border-surfaceBorder bg-surface px-8 py-4 text-sm font-semibold text-gray-200 hover:bg-surfaceBorder transition-all"
        >
          <Crown className="h-4 w-4 text-amber-400" /> View Pro Plans (₹499/mo)
        </Link>
      </div>

      {/* Value Proposition Cards */}
      <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
        <div className="rounded-3xl border border-surfaceBorder bg-surface p-6 shadow-xl">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-500/10 text-brand-400 mb-4">
            <Zap className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-white">Zero Full-Download Overhead</h3>
          <p className="text-xs text-gray-400 mt-2 leading-relaxed">
            Never wait 45 minutes for a 50GB file to download. We extract audio metadata first and fetch only the exact 20-second high-action video segment directly from YouTube HLS/DASH.
          </p>
        </div>

        <div className="rounded-3xl border border-surfaceBorder bg-surface p-6 shadow-xl">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400 mb-4">
            <Flame className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-white">Audio Spike & Hype Detector</h3>
          <p className="text-xs text-gray-400 mt-2 leading-relaxed">
            Our algorithmic RMS audio energy detector detects screaming, clutches, and teamfights, paired with Gemini Flash to write viral curiosity hooks for TikTok & Shorts.
          </p>
        </div>

        <div className="rounded-3xl border border-surfaceBorder bg-surface p-6 shadow-xl">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 mb-4">
            <Shield className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-white">Karaoke Subtitles Burned In</h3>
          <p className="text-xs text-gray-400 mt-2 leading-relaxed">
            Word-by-word animated highlights powered by Faster-Whisper and FFmpeg. Choose font styles, highlight colors, and export in 9:16 vertical reels ready to upload.
          </p>
        </div>
      </div>

      {/* Free vs Pro Comparison */}
      <div className="mt-20 w-full rounded-3xl border border-surfaceBorder bg-surface/70 p-8">
        <h2 className="text-2xl font-bold text-center text-white mb-8">
          Simple, Creator-Friendly Pricing
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Free Tier */}
          <div className="rounded-2xl border border-surfaceBorder bg-background p-6">
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-lg font-bold text-white">Free Creator</h4>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-800 text-gray-300">
                ₹0 / forever
              </span>
            </div>
            <ul className="space-y-3 text-xs text-gray-300">
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> 10 reels generated per day</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> Max 3 long streams per day</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> 720p export quality</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> Non-intrusive ad-supported</li>
            </ul>
          </div>

          {/* Pro Tier */}
          <div className="rounded-2xl border border-brand-500/40 bg-brand-950/20 p-6 relative">
            <div className="absolute -top-3 right-4 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 px-3 py-0.5 text-[10px] font-bold text-black uppercase">
              Popular
            </div>
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-lg font-bold text-white flex items-center gap-1.5">
                <Crown className="h-4 w-4 text-amber-400" /> Pro Streamer
              </h4>
              <span className="text-lg font-extrabold text-white">
                ₹499 <span className="text-xs font-normal text-gray-400">/ month</span>
              </span>
            </div>
            <ul className="space-y-3 text-xs text-gray-300">
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> Unlimited reels & long streams</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> Crisp 1080p 60fps export quality</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> Priority Celery worker queue</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-400" /> 100% Ad-free experience</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
