'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { ReelClip } from '@/types';
import { ReelPreviewer } from '@/components/editor/ReelPreviewer';
import { SubtitleCustomizer } from '@/components/editor/SubtitleCustomizer';
import { AdSlot } from '@/components/dashboard/AdSlot';
import { getBackendUrl } from '@/lib/utils';
import { ArrowLeft, Download, Share2, Clock, Check } from 'lucide-react';

export default function ClipEditorPage() {
  const params = useParams();
  const router = useRouter();
  const clipId = params?.id as string;

  const [clip, setClip] = useState<ReelClip | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!clipId) return;

    const fetchClip = async () => {
      try {
        const { data: sessionData } = await supabase.auth.getSession();
        const token = sessionData.session?.access_token;
        if (!token) {
          setLoading(false);
          return;
        }

        const backendUrl = getBackendUrl();
        const res = await fetch(`${backendUrl}/api/v1/clips/${clipId}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });

        if (res.ok) {
          const data = await res.json();
          setClip(data);
        }
      } catch (err) {
        console.error('Failed to load clip:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchClip();
  }, [clipId]);

  const handleDownload = async () => {
    if (!clip) return;
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      const backendUrl = getBackendUrl();

      if (token) {
        await fetch(`${backendUrl}/api/v1/clips/${clip.id}/download`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        });
      }
      if (clip.public_url) {
        window.open(clip.public_url, '_blank');
      }
    } catch {
      if (clip.public_url) window.open(clip.public_url, '_blank');
    }
  };

  const handleShare = () => {
    if (typeof window !== 'undefined') {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-xs text-gray-500">
        Loading clip player and subtitle studio...
      </div>
    );
  }

  if (!clip) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400">Clip not found or unauthorized.</p>
        <button
          onClick={() => router.push('/dashboard')}
          className="mt-4 text-xs font-semibold text-brand-400 underline"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-5xl mx-auto space-y-6">
      {/* Back Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Studio
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 rounded-xl border border-surfaceBorder bg-surface px-3 py-1.5 text-xs font-medium text-gray-300 hover:text-white transition-all"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Share2 className="h-3.5 w-3.5" />}
            {copied ? 'Copied Link!' : 'Share'}
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-1.5 text-xs font-bold text-white shadow-md hover:bg-brand-500 transition-all"
          >
            <Download className="h-3.5 w-3.5" /> Download 9:16 Video
          </button>
        </div>
      </div>

      {/* Main Studio Grid: Video Player on Left / Settings on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: 9:16 Vertical Video Player */}
        <div className="lg:col-span-5 flex justify-center">
          <ReelPreviewer videoUrl={clip.public_url} title={clip.title} />
        </div>

        {/* Right Column: Metadata & Subtitle Studio */}
        <div className="lg:col-span-7 space-y-6">
          <div className="rounded-3xl border border-surfaceBorder bg-surface p-6 shadow-xl">
            <div className="flex items-center gap-2 mb-2">
              <span className="rounded-full bg-black/60 px-2.5 py-0.5 text-[11px] font-bold text-amber-400">
                🔥 {clip.highlight_score} Excitation Score
              </span>
              <span className="flex items-center gap-1 text-[11px] text-gray-400">
                <Clock className="h-3.5 w-3.5" /> {Math.round(clip.duration_seconds)}s duration
              </span>
            </div>

            <h1 className="text-xl font-bold text-white tracking-tight">
              {clip.title}
            </h1>

            {clip.hook_text && (
              <div className="mt-3 rounded-2xl bg-brand-950/40 border border-brand-500/20 p-3 text-xs text-brand-300">
                <strong>Curiosity Hook Headline:</strong> &ldquo;{clip.hook_text}&rdquo;
              </div>
            )}

            {clip.transcript_text && (
              <div className="mt-3">
                <span className="text-[11px] font-semibold text-gray-400 uppercase">
                  Spoken Dialogue:
                </span>
                <p className="mt-1 text-xs text-gray-300 leading-relaxed bg-background/60 p-3 rounded-xl border border-surfaceBorder">
                  &ldquo;{clip.transcript_text}&rdquo;
                </p>
              </div>
            )}
          </div>

          {/* Subtitle Customizer Controls */}
          <SubtitleCustomizer
            clipId={clip.id}
            initialStyle={clip.subtitle_style}
            onStyleUpdated={(newStyle) => setClip({ ...clip, subtitle_style: newStyle })}
          />

          {/* Ad Slot for Free Users */}
          <AdSlot slotType="card" />
        </div>
      </div>
    </div>
  );
}
