'use client';

import React, { useEffect, useRef, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { VideoJob } from '@/types';
import { getBackendUrl } from '@/lib/utils';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface JobStatusTrackerProps {
  jobId: string;
  onCompleted: () => void;
}

export const JobStatusTracker: React.FC<JobStatusTrackerProps> = ({ jobId, onCompleted }) => {
  const [job, setJob] = useState<VideoJob | null>(null);
  const onCompletedRef = useRef(onCompleted);

  useEffect(() => {
    onCompletedRef.current = onCompleted;
  }, [onCompleted]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;

    const fetchStatus = async () => {
      try {
        const { data: sessionData } = await supabase.auth.getSession();
        const token = sessionData.session?.access_token;
        if (!token) return;

        const backendUrl = getBackendUrl();
        const res = await fetch(`${backendUrl}/api/v1/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data: VideoJob = await res.json();
          setJob(data);

          if (data.status === 'completed') {
            if (interval) clearInterval(interval);
            onCompletedRef.current();
          } else if (data.status === 'failed') {
            if (interval) clearInterval(interval);
          }
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
      }
    };

    fetchStatus();
    interval = setInterval(fetchStatus, 3000);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId]);

  if (!job) return null;

  const getStageMessage = (status: string) => {
    switch (status) {
      case 'queued':
        return 'Queueing job in background worker...';
      case 'fetching_metadata':
        return 'Extracting stream chapters, duration & chat logs...';
      case 'downloading_audio':
        return 'Extracting lightweight audio track for energy detection...';
      case 'detecting_spikes':
        return 'Analyzing audio RMS & gaming excitement spikes...';
      case 'cutting_clips':
        return 'Surgically cutting 15-30s sections & transcribing...';
      case 'rendering':
        return 'Cropping to 9:16 vertical & burning karaoke subtitles...';
      case 'completed':
        return 'Reels ready! Uploaded to storage.';
      case 'failed':
        return `Pipeline failed: ${job.error_message || 'Unknown error'}`;
      default:
        return 'Processing long-stream highlights...';
    }
  };

  const isFinished = job.status === 'completed';
  const isFailed = job.status === 'failed';

  return (
    <div className="rounded-2xl border border-surfaceBorder bg-surface p-4 shadow-lg backdrop-blur-md">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isFinished ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          ) : isFailed ? (
            <XCircle className="h-5 w-5 text-rose-400" />
          ) : (
            <Loader2 className="h-5 w-5 text-brand-400 animate-spin" />
          )}
          <span className="text-sm font-semibold text-white">
            {job.title ? `Processing: ${job.title.substring(0, 40)}...` : 'Processing Stream...'}
          </span>
        </div>
        <span className="text-xs font-bold text-brand-400">
          {job.progress_percentage}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-background">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-cyan transition-all duration-500"
          style={{ width: `${job.progress_percentage}%` }}
        />
      </div>

      <p className="mt-2 text-xs text-gray-400">
        {getStageMessage(job.status)}
      </p>
    </div>
  );
};
