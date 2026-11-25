'use client';

import React, { useRef, useState } from 'react';
import { Play, Pause, Volume2, VolumeX, RotateCcw } from 'lucide-react';

interface ReelPreviewerProps {
  videoUrl?: string;
  title: string;
}

export const ReelPreviewer: React.FC<ReelPreviewerProps> = ({ videoUrl, title }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  // Start muted so modern browsers allow autoplay reliably
  const [isMuted, setIsMuted] = useState(true);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
    } else {
      videoRef.current.pause();
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !isMuted;
    videoRef.current.muted = nextMuted;
    setIsMuted(nextMuted);
  };

  const handleRestart = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play().catch(() => {});
  };

  return (
    <div className="flex flex-col items-center">
      {/* 9:16 Smartphone Frame */}
      <div className="relative aspect-[9/16] w-full max-w-[340px] sm:max-w-[380px] rounded-[36px] border-4 border-surfaceBorder bg-black overflow-hidden shadow-2xl">
        {videoUrl ? (
          <video
            ref={videoRef}
            src={videoUrl}
            title={title}
            autoPlay
            loop
            playsInline
            muted={isMuted}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            className="h-full w-full object-cover cursor-pointer"
            onClick={togglePlay}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-gray-500">
            Video loading...
          </div>
        )}

        {/* Center Play/Pause indicator on tap */}
        {videoUrl && !isPlaying && (
          <div
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[2px] cursor-pointer"
          >
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-600/90 text-white shadow-xl">
              <Play className="h-8 w-8 ml-1" />
            </div>
          </div>
        )}

        {/* Controls Overlay */}
        <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-2xl bg-black/60 backdrop-blur-md px-4 py-2 text-white">
          <button type="button" onClick={togglePlay} aria-label={isPlaying ? 'Pause' : 'Play'} className="p-1 hover:text-brand-400">
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button type="button" onClick={handleRestart} aria-label="Restart" className="p-1 hover:text-brand-400">
            <RotateCcw className="h-4 w-4" />
          </button>
          <button type="button" onClick={toggleMute} aria-label={isMuted ? 'Unmute' : 'Mute'} className="p-1 hover:text-brand-400">
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};
