export type UserTier = 'free' | 'pro' | 'enterprise';

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  tier: UserTier;
  subscription_status?: string;
  current_period_end?: string;
}

export interface QuotaStatus {
  allowed: boolean;
  tier: UserTier;
  remaining_videos_today: number;
  remaining_reels_today: number;
  message?: string;
}

export interface VideoJob {
  id: string;
  user_id: string;
  youtube_url: string;
  video_id: string;
  title?: string;
  channel_name?: string;
  thumbnail_url?: string;
  duration_seconds: number;
  status: 'queued' | 'fetching_metadata' | 'downloading_audio' | 'detecting_spikes' | 'cutting_clips' | 'transcribing' | 'rendering' | 'completed' | 'failed';
  progress_percentage: number;
  error_message?: string;
  created_at: string;
}

export interface SubtitleStyleConfig {
  font_family: string;
  font_size: number;
  primary_color: string;
  highlight_color: string;
  outline_color: string;
  outline_width: number;
  position: string;
  karaoke_effect: boolean;
}

export interface ReelClip {
  id: string;
  job_id: string;
  user_id: string;
  title: string;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  highlight_score: number;
  hook_text?: string;
  transcript_text?: string;
  subtitle_style?: SubtitleStyleConfig;
  aspect_ratio: string;
  resolution: string;
  public_url?: string;
  thumbnail_url?: string;
  download_count: number;
  expires_at: string;
  created_at: string;
}
