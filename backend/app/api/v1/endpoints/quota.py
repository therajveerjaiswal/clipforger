from fastapi import APIRouter, Depends, Request
from app.core.security import get_current_user, get_client_ip, get_device_fingerprint
from app.core.supabase_client import get_supabase_admin
from app.models.schemas import UserProfile, QuotaCheckResponse

router = APIRouter()


@router.get("/status", response_model=QuotaCheckResponse)
async def check_user_quota(
    request: Request,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Checks today's remaining quota for the authenticated user, client IP, and device fingerprint.
    """
    if current_user.tier in ["pro", "enterprise"]:
        return QuotaCheckResponse(
            allowed=True,
            tier=current_user.tier,
            remaining_videos_today=999,
            remaining_reels_today=999,
            message="Pro account: Unlimited high-priority generation."
        )

    ip_address = get_client_ip(request)
    visitor_id = get_device_fingerprint(request)
    supabase = get_supabase_admin()

    # Call the anti-abuse stored procedure with 0 increments to query balance
    res = supabase.rpc("check_and_enforce_daily_quota", {
        "p_user_id": current_user.id,
        "p_visitor_id": visitor_id,
        "p_ip_address": ip_address,
        "p_videos_to_add": 0,
        "p_reels_to_add": 0
    }).execute()

    raw_data = res.data
    data = raw_data[0] if isinstance(raw_data, list) and raw_data else (raw_data or {})
    allowed = data.get("allowed", True)

    return QuotaCheckResponse(
        allowed=allowed,
        tier=current_user.tier,
        remaining_videos_today=data.get("remaining_videos", 3),
        remaining_reels_today=data.get("remaining_reels", 10),
        message=data.get("message")
    )
