from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


# User & Auth
class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    tier: str = "free"
    subscription_status: Optional[str] = "inactive"
    current_period_end: Optional[datetime] = None


# Quota Verification
class QuotaCheckResponse(BaseModel):
    allowed: bool
    tier: str
    remaining_videos_today: int
    remaining_reels_today: int
    message: Optional[str] = None


# Job Request & Response
class CreateJobRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube video or completed livestream URL")
    target_clips: int = Field(default=3, ge=1, le=10, description="Number of highlight reels to extract")
    render_mode: Literal["blur_split", "smart_crop"] = Field(default="blur_split", description="'blur_split' or 'smart_crop'")


class JobResponse(BaseModel):
    id: str
    user_id: str
    youtube_url: str
    video_id: str
    title: Optional[str] = None
    channel_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: float = 0.0
    status: str
    progress_percentage: int
    error_message: Optional[str] = None
    created_at: str


# Reel Clips
HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class SubtitleStyle(BaseModel):
    # Values end up inside generated .ass subtitle files, so they are strictly validated.
    font_family: str = Field(default="Montserrat", pattern=r"^[A-Za-z0-9 _-]{1,64}$")
    font_size: int = Field(default=24, ge=8, le=200)
    primary_color: str = Field(default="#FFFFFF", pattern=HEX_COLOR_PATTERN)
    highlight_color: str = Field(default="#FFD700", pattern=HEX_COLOR_PATTERN)
    outline_color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    outline_width: int = Field(default=3, ge=0, le=12)
    position: str = Field(default="middle-bottom", pattern=r"^[a-z-]{1,32}$")
    karaoke_effect: bool = True


class ReelClipResponse(BaseModel):
    id: str
    job_id: str
    user_id: str
    title: str
    start_time: float
    end_time: float
    duration_seconds: float
    highlight_score: float
    hook_text: Optional[str] = None
    transcript_text: Optional[str] = None
    subtitle_style: Optional[Dict[str, Any]] = None
    aspect_ratio: str = "9:16"
    resolution: str
    public_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    download_count: int = 0
    expires_at: str
    created_at: str


class UpdateSubtitleStyleRequest(BaseModel):
    subtitle_style: SubtitleStyle


# Payments & Razorpay
class CreateSubscriptionOrderRequest(BaseModel):
    # Only the monthly Pro plan exists today; accepting other values used to silently create a Pro/monthly plan.
    plan_tier: Literal["pro"] = Field(default="pro", description="Only 'pro' is currently available")
    billing_cycle: Literal["monthly"] = Field(default="monthly", description="Only 'monthly' is currently available")


class CreateSubscriptionOrderResponse(BaseModel):
    subscription_id: str
    key_id: str
    amount_in_paise: int
    currency: str
    name: str
    description: str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str
