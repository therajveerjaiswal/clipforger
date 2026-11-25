-- ==============================================================================
-- Schema: Gaming Reel & Highlight Clipper SaaS
-- Target: Supabase (PostgreSQL 15+)
-- Features: Auth Sync, Multi-Account Anti-Abuse (IP + Device Hash), Quota Limits,
--           20-30h Stream Job Tracking, R2 Storage Life Cycle, Razorpay Subscriptions
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- 1. Profiles Table (Synced automatically with Supabase auth.users)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    subscription_id TEXT,
    subscription_status TEXT DEFAULT 'inactive' CHECK (subscription_status IN ('inactive', 'active', 'past_due', 'cancelled')),
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_profiles_tier ON public.profiles(tier);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_id ON public.profiles(subscription_id);

-- ------------------------------------------------------------------------------
-- 2. Anti-Abuse: Device Fingerprinting & IP Tracking Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.device_fingerprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id TEXT NOT NULL,                  -- Browser FingerprintJS hash
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    ip_address INET NOT NULL,                 -- Real client IP (X-Forwarded-For / CF-Connecting-IP)
    user_agent TEXT,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_device_visitor_id ON public.device_fingerprints(visitor_id);
CREATE INDEX IF NOT EXISTS idx_device_ip_address ON public.device_fingerprints(ip_address);
CREATE INDEX IF NOT EXISTS idx_device_user_id ON public.device_fingerprints(user_id);

-- ------------------------------------------------------------------------------
-- 3. Daily Usage Quota Aggregations (Enforcing Free-tier 10 reels / 3 long videos)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.daily_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    visitor_id TEXT NOT NULL,
    ip_address INET NOT NULL,
    videos_processed INT NOT NULL DEFAULT 0,
    reels_generated INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_usage_unique_record
ON public.daily_usage_logs (usage_date, visitor_id, ip_address, user_id);

CREATE INDEX IF NOT EXISTS idx_daily_usage_date_user ON public.daily_usage_logs(usage_date, user_id);
CREATE INDEX IF NOT EXISTS idx_daily_usage_date_visitor ON public.daily_usage_logs(usage_date, visitor_id);
CREATE INDEX IF NOT EXISTS idx_daily_usage_date_ip ON public.daily_usage_logs(usage_date, ip_address);

-- ------------------------------------------------------------------------------
-- 4. Video Processing Jobs Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.video_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    youtube_url TEXT NOT NULL,
    video_id TEXT NOT NULL,
    title TEXT,
    channel_name TEXT,
    thumbnail_url TEXT,
    duration_seconds NUMERIC NOT NULL DEFAULT 0,
    is_livestream BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (
        status IN ('queued', 'fetching_metadata', 'downloading_audio', 'detecting_spikes', 'cutting_clips', 'transcribing', 'rendering', 'completed', 'failed')
    ),
    progress_percentage INT NOT NULL DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_video_jobs_user_id ON public.video_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON public.video_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_jobs_created_at ON public.video_jobs(created_at DESC);

-- ------------------------------------------------------------------------------
-- 5. Generated Highlight Clips (Reels) Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reel_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.video_jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    start_time NUMERIC NOT NULL,
    end_time NUMERIC NOT NULL,
    duration_seconds NUMERIC NOT NULL,
    highlight_score NUMERIC(5,2) DEFAULT 0.0,
    hook_text TEXT,
    transcript_text TEXT,
    subtitle_style JSONB DEFAULT '{
        "font_family": "Montserrat",
        "font_size": 24,
        "primary_color": "#FFFFFF",
        "highlight_color": "#FFD700",
        "outline_color": "#000000",
        "outline_width": 3,
        "position": "middle-bottom",
        "karaoke_effect": true
    }'::jsonb,
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    resolution TEXT NOT NULL DEFAULT '720p' CHECK (resolution IN ('480p', '720p', '1080p')),
    fps INT NOT NULL DEFAULT 30 CHECK (fps IN (30, 60)),
    storage_key TEXT NOT NULL,
    public_url TEXT,
    thumbnail_url TEXT,
    file_size_bytes BIGINT DEFAULT 0,
    download_count INT NOT NULL DEFAULT 0,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (TIMEZONE('utc'::text, NOW()) + INTERVAL '48 HOURS'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_reel_clips_job_id ON public.reel_clips(job_id);
CREATE INDEX IF NOT EXISTS idx_reel_clips_user_id ON public.reel_clips(user_id);
CREATE INDEX IF NOT EXISTS idx_reel_clips_expires_at ON public.reel_clips(expires_at);

-- ------------------------------------------------------------------------------
-- 6. Subscriptions & Payments Table (Razorpay Integration)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    razorpay_order_id TEXT,
    razorpay_payment_id TEXT,
    razorpay_subscription_id TEXT UNIQUE,
    razorpay_signature TEXT,
    plan_tier TEXT NOT NULL DEFAULT 'pro' CHECK (plan_tier IN ('pro', 'enterprise')),
    billing_cycle TEXT NOT NULL DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
    amount_in_paise INT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('created', 'pending', 'active', 'paused', 'cancelled', 'expired', 'failed')
    ),
    raw_webhook_payload JSONB DEFAULT '{}'::jsonb,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_razorpay_sub_id ON public.subscriptions(razorpay_subscription_id);

-- ------------------------------------------------------------------------------
-- 7. Functions & Stored Procedures: Multi-Account Anti-Abuse & Quota Verification
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.check_and_enforce_daily_quota(
    p_user_id UUID,
    p_visitor_id TEXT,
    p_ip_address INET,
    p_videos_to_add INT DEFAULT 0,
    p_reels_to_add INT DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_tier TEXT;
    v_today DATE := CURRENT_DATE;
    v_user_videos INT := 0;
    v_user_reels INT := 0;
    v_device_videos INT := 0;
    v_device_reels INT := 0;
    v_ip_videos INT := 0;
    v_ip_reels INT := 0;
    v_max_videos CONSTANT INT := 3;
    v_max_reels CONSTANT INT := 10;
BEGIN
    -- 1. Check user tier
    SELECT tier INTO v_tier FROM public.profiles WHERE id = p_user_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User profile not found.';
    END IF;

    -- Pro and Enterprise users bypass daily limits
    IF v_tier IN ('pro', 'enterprise') THEN
        RETURN jsonb_build_object(
            'allowed', true,
            'tier', v_tier,
            'remaining_videos', 999,
            'remaining_reels', 999,
            'reason', 'Paid tier active'
        );
    END IF;

    -- 2. Aggregate today's usage by User ID
    SELECT COALESCE(SUM(videos_processed), 0), COALESCE(SUM(reels_generated), 0)
    INTO v_user_videos, v_user_reels
    FROM public.daily_usage_logs
    WHERE usage_date = v_today AND user_id = p_user_id;

    -- 3. Aggregate today's usage by Device Fingerprint (across all accounts)
    SELECT COALESCE(SUM(videos_processed), 0), COALESCE(SUM(reels_generated), 0)
    INTO v_device_videos, v_device_reels
    FROM public.daily_usage_logs
    WHERE usage_date = v_today AND visitor_id = p_visitor_id;

    -- 4. Aggregate today's usage by IP Address (across all accounts & devices on same IP)
    SELECT COALESCE(SUM(videos_processed), 0), COALESCE(SUM(reels_generated), 0)
    INTO v_ip_videos, v_ip_reels
    FROM public.daily_usage_logs
    WHERE usage_date = v_today AND ip_address = p_ip_address;

    -- 5. Enforce Video Quotas
    IF (v_user_videos + p_videos_to_add > v_max_videos) THEN
        RETURN jsonb_build_object(
            'allowed', false,
            'code', 'USER_VIDEO_LIMIT_REACHED',
            'remaining_videos', 0,
            'remaining_reels', GREATEST(0, v_max_reels - v_user_reels),
            'message', 'Daily limit reached: Maximum 3 long streams per day for Free accounts. Upgrade to Pro for unlimited.'
        );
    END IF;

    IF (v_device_videos + p_videos_to_add > v_max_videos) THEN
        RETURN jsonb_build_object(
            'allowed', false,
            'code', 'DEVICE_VIDEO_LIMIT_REACHED',
            'remaining_videos', 0,
            'remaining_reels', GREATEST(0, v_max_reels - v_device_reels),
            'message', 'Device daily quota reached: 3 streams already processed today from this browser/device.'
        );
    END IF;

    IF (v_ip_videos + p_videos_to_add > (v_max_videos * 2)) THEN
        RETURN jsonb_build_object(
            'allowed', false,
            'code', 'IP_VIDEO_LIMIT_REACHED',
            'remaining_videos', 0,
            'remaining_reels', GREATEST(0, v_max_reels - v_user_reels),
            'message', 'Network quota exceeded: Too many requests from this IP today. Please try tomorrow or upgrade to Pro.'
        );
    END IF;

    -- 6. Enforce Reel Quotas
    IF (v_user_reels + p_reels_to_add > v_max_reels) THEN
        RETURN jsonb_build_object(
            'allowed', false,
            'code', 'USER_REEL_LIMIT_REACHED',
            'remaining_videos', GREATEST(0, v_max_videos - v_user_videos),
            'remaining_reels', GREATEST(0, v_max_reels - v_user_reels),
            'message', 'Daily limit reached: Maximum 10 generated reels per day for Free accounts. Upgrade to Pro for unlimited.'
        );
    END IF;

    IF (v_device_reels + p_reels_to_add > v_max_reels) THEN
        RETURN jsonb_build_object(
            'allowed', false,
            'code', 'DEVICE_REEL_LIMIT_REACHED',
            'remaining_videos', GREATEST(0, v_max_videos - v_device_videos),
            'remaining_reels', GREATEST(0, v_max_reels - v_device_reels),
            'message', 'Device daily quota reached: 10 reels already created on this device today.'
        );
    END IF;

    -- 7. Record usage only when consuming quota (skip writes on read-only checks)
    IF (p_videos_to_add > 0 OR p_reels_to_add > 0) THEN
        INSERT INTO public.daily_usage_logs (usage_date, user_id, visitor_id, ip_address, videos_processed, reels_generated)
        VALUES (v_today, p_user_id, p_visitor_id, p_ip_address, p_videos_to_add, p_reels_to_add)
        ON CONFLICT (usage_date, visitor_id, ip_address, user_id)
        DO UPDATE SET
            videos_processed = public.daily_usage_logs.videos_processed + EXCLUDED.videos_processed,
            reels_generated = public.daily_usage_logs.reels_generated + EXCLUDED.reels_generated,
            updated_at = TIMEZONE('utc'::text, NOW());

        INSERT INTO public.device_fingerprints (visitor_id, user_id, ip_address, last_seen_at)
        VALUES (p_visitor_id, p_user_id, p_ip_address, TIMEZONE('utc'::text, NOW()));
    END IF;

    RETURN jsonb_build_object(
        'allowed', true,
        'remaining_videos', GREATEST(0, LEAST(v_max_videos - v_user_videos, v_max_videos - v_device_videos) - p_videos_to_add),
        'remaining_reels', GREATEST(0, LEAST(v_max_reels - v_user_reels, v_max_reels - v_device_reels) - p_reels_to_add)
    );
END;
$$;

-- ------------------------------------------------------------------------------
-- 8. Triggers for Automatic Profile Creation on Google OAuth Sign-Up
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url, tier)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', ''),
        COALESCE(NEW.raw_user_meta_data->>'avatar_url', NEW.raw_user_meta_data->>'picture', ''),
        'free'
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        full_name = EXCLUDED.full_name,
        avatar_url = EXCLUDED.avatar_url,
        updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger for auto updating timestamp
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_profiles_updated_at ON public.profiles;
CREATE TRIGGER trigger_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trigger_video_jobs_updated_at ON public.video_jobs;
CREATE TRIGGER trigger_video_jobs_updated_at BEFORE UPDATE ON public.video_jobs FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trigger_reel_clips_updated_at ON public.reel_clips;
CREATE TRIGGER trigger_reel_clips_updated_at BEFORE UPDATE ON public.reel_clips FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trigger_subscriptions_updated_at ON public.subscriptions;
CREATE TRIGGER trigger_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ------------------------------------------------------------------------------
-- 9. Row Level Security (RLS) Policies (Idempotent)
-- ------------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.video_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reel_clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can view own video jobs" ON public.video_jobs;
CREATE POLICY "Users can view own video jobs" ON public.video_jobs FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create video jobs" ON public.video_jobs;
CREATE POLICY "Users can create video jobs" ON public.video_jobs FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own video jobs" ON public.video_jobs;
CREATE POLICY "Users can update own video jobs" ON public.video_jobs FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own clips" ON public.reel_clips;
CREATE POLICY "Users can view own clips" ON public.reel_clips FOR SELECT USING (auth.uid() = user_id OR is_public = TRUE);

DROP POLICY IF EXISTS "Users can update own clips" ON public.reel_clips;
CREATE POLICY "Users can update own clips" ON public.reel_clips FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own clips" ON public.reel_clips;
CREATE POLICY "Users can delete own clips" ON public.reel_clips FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own subscriptions" ON public.subscriptions;
CREATE POLICY "Users can view own subscriptions" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);

GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;
