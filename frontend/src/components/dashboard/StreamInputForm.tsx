'use client';

import React, { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useDeviceFingerprint } from '@/hooks/useDeviceFingerprint';
import { useQuota } from '@/hooks/useQuota';
import { getBackendUrl } from '@/lib/utils';
import { Sparkles, Video, AlertCircle, Loader2, ArrowRight } from 'lucide-react';

interface StreamInputFormProps {
  onJobCreated: (jobId: string) => void;
}

export const StreamInputForm: React.FC<StreamInputFormProps> = ({ onJobCreated }) => {
  const [url, setUrl] = useState('');
  const [targetClips, setTargetClips] = useState(3);
  const [renderMode, setRenderMode] = useState('blur_split');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { visitorId } = useDeviceFingerprint();
  const { refetchQuota } = useQuota();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!url.trim()) {
      setErrorMsg('Please paste a YouTube stream or video link.');
      return;
    }

    setSubmitting(true);

    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;

      if (!token) {
        setErrorMsg('Please sign in with Google to create reels.');
        setSubmitting(false);
        return;
      }

      const backendUrl = getBackendUrl();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };
      if (visitorId) {
        headers['X-Device-Fingerprint'] = visitorId;
      }

      const res = await fetch(`${backendUrl}/api/v1/jobs/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          youtube_url: url.trim(),
          target_clips: Number(targetClips),
          render_mode: renderMode,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        if (res.status === 429) {
          setErrorMsg(data.detail || 'Daily free limit reached: 3 streams or 10 reels. Upgrade to Pro.');
        } else {
          setErrorMsg(data.detail || 'Failed to submit stream for clipping.');
        }
        setSubmitting(false);
        return;
      }

      setUrl('');
      refetchQuota();
      onJobCreated(data.id);
    } catch (err: any) {
      console.error('Job submission failed:', err);
      setErrorMsg(err.message || 'Network error occurred. Please check your connection.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-3xl border border-surfaceBorder bg-surface/90 p-5 sm:p-7 shadow-2xl backdrop-blur-xl">
      <div className="mb-5">
        <div className="flex items-center gap-2 text-brand-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <Sparkles className="h-4 w-4" /> AI Long-Stream Clipper Engine
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
          Turn Any 20–30hr Gaming Stream into Viral Reels
        </h2>
        <p className="text-xs sm:text-sm text-gray-400 mt-1">
          Zero full-download overhead. Analyzes excitement spikes and extracts vertical 9:16 reels with auto-burned karaoke subtitles.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Stream URL Input */}
        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
            <Video className="h-5 w-5" />
          </div>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste YouTube stream or video URL (e.g., https://youtube.com/watch?v=...)"
            required
            className="w-full rounded-2xl border border-surfaceBorder bg-background py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 transition-all"
          />
        </div>

        {/* Configuration Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div>
            <label className="block text-gray-400 font-medium mb-1.5">
              Highlight Reels to Extract:
            </label>
            <select
              value={targetClips}
              onChange={(e) => setTargetClips(Number(e.target.value))}
              className="w-full rounded-xl border border-surfaceBorder bg-background px-3 py-2.5 text-white focus:border-brand-500 focus:outline-none"
            >
              <option value={1}>1 Best Highlight (Fastest)</option>
              <option value={3}>3 Viral Clips (Recommended)</option>
              <option value={5}>5 Action Moments</option>
            </select>
          </div>

          <div>
            <label className="block text-gray-400 font-medium mb-1.5">
              9:16 Vertical Video Framing:
            </label>
            <select
              value={renderMode}
              onChange={(e) => setRenderMode(e.target.value)}
              className="w-full rounded-xl border border-surfaceBorder bg-background px-3 py-2.5 text-white focus:border-brand-500 focus:outline-none"
            >
              <option value="blur_split">Blurred Background + Centered Gameplay (Recommended)</option>
              <option value="smart_crop">Action Center Crop (No blur)</option>
            </select>
          </div>
        </div>

        {/* Error Notification */}
        {errorMsg && (
          <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-600 to-accent-cyan py-3.5 px-6 text-sm font-bold text-white shadow-lg shadow-brand-500/25 hover:brightness-110 active:scale-[0.99] disabled:opacity-50 transition-all"
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Analyzing 20-30hr Stream Spikes...
            </>
          ) : (
            <>
              Generate Viral Reels <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
