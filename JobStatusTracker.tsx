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
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    setJob(null);

    // Sequential polling (next request is scheduled only after the previous one finished), so slow responses
    // can never pile up or deliver "completed" twice.
    const poll = async () => {
      let finished = false;
      try {
        const { data: sessionData } = await supabase.auth.getSession();
        const token = sessionData.session?.access_token;

        if (token) {
          const res = await fetch(`${getBackendUrl()}/api/v1/jobs/${jobId}`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (cancelled) return;

          if (res.ok) {
            const data: VideoJob = await res.json();
            if (cancelled) return;
            setJob(data);

            if (data.status === 'completed') {
              finished = true;
              onCompletedRef.current();
            } else if (data.status === 'failed') {
              finished = true;
            }
          } else if (res.status === 404) {
            // The job does not exist (or is not ours): polling it forever would be pointless.
            finished = true;
          }
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
      }

      if (!cancelled && !finished) {
        timer = setTimeout(poll, 3000);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
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
        return 'Surgically cutting 15-30s sections from the stream...';
      case 'transcribing':
        return 'Transcribing speech & writing viral hooks...';
      case 'rendering':
        return 'Cropping to 9:16 vertical & burning karaoke subtitles...';
      case 'completed':
        return job.error_message ? `Reels ready! (${job.error_message})` : 'Reels ready! Uploaded to storage.';
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
