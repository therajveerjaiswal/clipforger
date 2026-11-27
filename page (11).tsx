'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { DesktopSidebar } from '@/components/layout/DesktopSidebar';
import { StreamInputForm } from '@/components/dashboard/StreamInputForm';
import { JobStatusTracker } from '@/components/dashboard/JobStatusTracker';
import { ClipGrid } from '@/components/dashboard/ClipGrid';
import { AdSlot } from '@/components/dashboard/AdSlot';
import { ReelClip, VideoJob } from '@/types';
import { getBackendUrl } from '@/lib/utils';
import { Film } from 'lucide-react';

export default function DashboardPage() {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [clips, setClips] = useState<ReelClip[]>([]);
  const [loadingClips, setLoadingClips] = useState<boolean>(true);

  const fetchClips = useCallback(async () => {
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) {
        setClips([]);
        setLoadingClips(false);
        return;
      }

      const backendUrl = getBackendUrl();
      const res = await fetch(`${backendUrl}/api/v1/clips/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setClips(data);
      }
    } catch (err) {
      console.error('Failed to load reels:', err);
    } finally {
      setLoadingClips(false);
    }
  }, []);

  // After a page reload the tracker would otherwise be lost although the job is still running on the worker.
  const resumeRunningJob = useCallback(async () => {
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) return;

      const res = await fetch(`${getBackendUrl()}/api/v1/jobs/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;

      const jobs: VideoJob[] = await res.json();
      const running = jobs.find((job) => job.status !== 'completed' && job.status !== 'failed');
      if (running) {
        setActiveJobId((current) => current ?? running.id);
      }
    } catch (err) {
      console.error('Failed to look up running jobs:', err);
    }
  }, []);

  useEffect(() => {
    fetchClips();
    resumeRunningJob();

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        setClips([]);
        setActiveJobId(null);
      } else if (event === 'SIGNED_IN') {
        fetchClips();
        resumeRunningJob();
      }
    });

    return () => {
      listener.subscription.unsubscribe();
    };
  }, [fetchClips, resumeRunningJob]);

  const handleJobCreated = useCallback((jobId: string) => {
    setActiveJobId(jobId);
  }, []);

  const handleJobCompleted = useCallback(() => {
    fetchClips();
  }, [fetchClips]);

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      {/* Desktop Sidebar (Hidden on Mobile) */}
      <DesktopSidebar />

      {/* Main Workspace Area */}
      <div className="flex-1 p-4 sm:p-8 max-w-5xl mx-auto space-y-6">
        {/* AdSlot Banner Top (Free Tier Only) */}
        <AdSlot slotType="banner" />

        {/* Stream URL Input & Clipper Launcher */}
        <StreamInputForm onJobCreated={handleJobCreated} />

        {/* Live Job Progress Tracker */}
        {activeJobId && (
          <JobStatusTracker jobId={activeJobId} onCompleted={handleJobCompleted} />
        )}

        {/* Highlight Clips Library Section */}
        <div id="clips" className="pt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Film className="h-5 w-5 text-brand-400" />
              Generated Highlight Reels ({clips.length})
            </h3>
            <button
              onClick={fetchClips}
              className="text-xs text-brand-400 hover:underline"
            >
              Refresh Library
            </button>
          </div>

          {loadingClips ? (
            <div className="text-center py-12 text-xs text-gray-500">
              Loading your reels...
            </div>
          ) : (
            <ClipGrid clips={clips} />
          )}
        </div>

        {/* Download Screen Ad Slot */}
        <AdSlot slotType="card" className="mt-8" />
      </div>
    </div>
  );
}
