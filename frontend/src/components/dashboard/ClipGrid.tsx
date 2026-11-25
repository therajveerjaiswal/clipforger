'use client';

import React from 'react';
import Link from 'next/link';
import { ReelClip } from '@/types';
import { Download, Sparkles, Clock, ExternalLink } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { getBackendUrl } from '@/lib/utils';

interface ClipGridProps {
  clips: ReelClip[];
  onDownloadStarted?: (clipId: string) => void;
}

export const ClipGrid: React.FC<ClipGridProps> = ({ clips, onDownloadStarted }) => {
  const handleDownload = async (clip: ReelClip) => {
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

      if (onDownloadStarted) {
        onDownloadStarted(clip.id);
      }

      if (clip.public_url) {
        window.open(clip.public_url, '_blank');
      }
    } catch (err) {
      console.error('Download error:', err);
      if (clip.public_url) {
        window.open(clip.public_url, '_blank');
      }
    }
  };

  if (!clips || clips.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-surfaceBorder p-12 text-center">
        <Sparkles className="mx-auto h-8 w-8 text-gray-500 mb-2" />
        <h3 className="text-sm font-semibold text-white">No reels generated yet</h3>
        <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
          Paste any YouTube gaming stream or tournament link above to extract your first 9:16 vertical reels.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      {clips.map((clip) => (
        <div
          key={clip.id}
          className="group relative flex flex-col rounded-3xl border border-surfaceBorder bg-surface overflow-hidden hover:border-brand-500/40 hover:shadow-2xl transition-all"
        >
          {/* 9:16 Aspect Thumbnail Container */}
          <div className="relative aspect-[9/16] w-full bg-background overflow-hidden">
            {clip.thumbnail_url ? (
              <img
                src={clip.thumbnail_url}
                alt={clip.title}
                className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-xs text-gray-500">
                No preview
              </div>
            )}

            {/* Badges Overlay */}
            <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
              <span className="flex items-center gap-1 rounded-full bg-black/70 backdrop-blur-md px-2.5 py-1 text-[11px] font-bold text-amber-400">
                🔥 {clip.highlight_score} Score
              </span>
              <span className="rounded-full bg-brand-600/80 backdrop-blur-md px-2 py-0.5 text-[10px] font-bold text-white uppercase">
                {clip.resolution}
              </span>
            </div>

            {/* Duration pill */}
            <div className="absolute bottom-3 right-3 flex items-center gap-1 rounded-md bg-black/75 backdrop-blur-sm px-2 py-1 text-[11px] font-medium text-gray-200">
              <Clock className="h-3 w-3" /> {Math.round(clip.duration_seconds)}s
            </div>
          </div>

          {/* Card Body */}
          <div className="p-4 flex-1 flex flex-col justify-between">
            <div>
              <h4 className="text-sm font-bold text-white line-clamp-1">
                {clip.title}
              </h4>
              {clip.hook_text && (
                <p className="text-xs text-brand-300 font-medium mt-1 line-clamp-2">
                  &ldquo;{clip.hook_text}&rdquo;
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="mt-4 pt-3 border-t border-surfaceBorder flex items-center gap-2">
              <button
                onClick={() => handleDownload(clip)}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-xl bg-brand-600 py-2.5 px-3 text-xs font-semibold text-white shadow-md hover:bg-brand-500 transition-all"
              >
                <Download className="h-3.5 w-3.5" /> Download
              </button>

              <Link
                href={`/dashboard/clips/${clip.id}`}
                className="flex items-center justify-center rounded-xl border border-surfaceBorder bg-background/60 p-2.5 text-gray-300 hover:text-white hover:bg-surface transition-all"
                title="Edit Subtitles & Customize"
              >
                <ExternalLink className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
