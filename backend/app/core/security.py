import hashlib
import ipaddress
import logging
from typing import Optional
from fastapi import Request, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase_client import get_supabase_admin
from app.models.schemas import UserProfile

logger = logging.getLogger(__name__)
security_bearer = HTTPBearer(auto_error=False)


def _valid_ip(candidate: Optional[str]) -> Optional[str]:
    if not candidate:
        return None
    cleaned = candidate.split(",")[0].strip()
    try:
        ipaddress.ip_address(cleaned)
        return cleaned
    except ValueError:
        return None


def get_client_ip(request: Request) -> str:
    """
    Safely resolves real client IP behind Cloudflare and reverse proxies.
    Prioritizes CF-Connecting-IP, then True-Client-IP, then leftmost X-Forwarded-For.
    Always returns a valid IP string compatible with PostgreSQL INET.
    """
    for header in ("CF-Connecting-IP", "True-Client-IP", "X-Forwarded-For"):
        valid = _valid_ip(request.headers.get(header))
        if valid:
            return valid

    if request.client and request.client.host:
        valid = _valid_ip(request.client.host)
        if valid:
            return valid

    return "127.0.0.1"


def get_device_fingerprint(request: Request) -> str:
    """
    Extracts the unique hardware/browser visitor ID from request headers.
    Provided by the frontend FingerprintJS library.
    """
    visitor_id = (
        request.headers.get("X-Device-Fingerprint")
        or request.headers.get("X-Visitor-Id")
        or request.headers.get("x-visitor-id")
    )
    if not visitor_id or len(visitor_id.strip()) < 8:
        # If client blocked JS or sent empty, synthesize fingerprint based on IP + User-Agent
        user_agent = request.headers.get("User-Agent", "Unknown-Browser")
        ip = get_client_ip(request)
        synth_hash = hashlib.sha256(f"{ip}_{user_agent}".encode()).hexdigest()[:24]
        return f"synth_{synth_hash}"

    return visitor_id.strip()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> UserProfile:
    """
    Validates Supabase JWT session token passed in Authorization header.
    Returns user details and profile tier. Auto-creates missing profiles safely.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in with Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    supabase = get_supabase_admin()

    try:
        # Verify token with Supabase Auth service
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token.",
            )

        user_id = user_res.user.id
        email = user_res.user.email or f"{user_id}@users.clipforge.local"
        user_meta = user_res.user.user_metadata or {}

        # Fetch profile for tier and subscription status without throwing on 0 rows
        profile_res = supabase.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        profile_data = profile_res.data[0] if (profile_res and profile_res.data) else None

        if profile_data is None:
            # Ensure profile row exists if user signed up before schema trigger was created
            default_profile = {
                "id": user_id,
                "email": email,
                "full_name": user_meta.get("full_name") or user_meta.get("name") or "",
                "avatar_url": user_meta.get("avatar_url") or user_meta.get("picture") or "",
                "tier": "free",
            }
            upsert_res = supabase.table("profiles").upsert(default_profile, on_conflict="id").execute()
            profile_data = upsert_res.data[0] if (upsert_res and upsert_res.data) else default_profile

        return UserProfile(
            id=user_id,
            email=email,
            full_name=profile_data.get("full_name") or user_meta.get("full_name"),
            avatar_url=profile_data.get("avatar_url") or user_meta.get("avatar_url"),
            tier=profile_data.get("tier", "free"),
            subscription_status=profile_data.get("subscription_status", "inactive"),
            current_period_end=profile_data.get("current_period_end"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )
