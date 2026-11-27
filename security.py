import hashlib
import ipaddress
import logging
from functools import lru_cache
from typing import List, Optional, Tuple, Union

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.supabase_client import get_supabase_admin
from app.models.schemas import UserProfile

logger = logging.getLogger(__name__)
security_bearer = HTTPBearer(auto_error=False)

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
MAX_FINGERPRINT_LENGTH = 128


def _valid_ip(candidate: Optional[str]) -> Optional[str]:
    """Returns the first valid IP in a (possibly comma separated) header value, else None."""
    if not candidate:
        return None
    cleaned = candidate.split(",")[0].strip()
    try:
        ipaddress.ip_address(cleaned)
        return cleaned
    except ValueError:
        return None


@lru_cache(maxsize=8)
def _parse_trusted_proxies(raw: str) -> Tuple[IPNetwork, ...]:
    networks: List[IPNetwork] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            logger.warning(f"Ignoring invalid TRUSTED_PROXY_IPS entry: {item!r}")
    return tuple(networks)


def _is_trusted_proxy(ip: Optional[str]) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _parse_trusted_proxies(settings.TRUSTED_PROXY_IPS) if addr.version == net.version)


def _client_ip_from_forwarded_for(header_value: Optional[str]) -> Optional[str]:
    """
    Walks X-Forwarded-For from right to left and returns the first hop that is not a trusted proxy.
    The left-most entries are client-controlled and therefore must never be trusted on their own.
    """
    if not header_value:
        return None
    hops = [h.strip() for h in header_value.split(",") if h.strip()]
    for hop in reversed(hops):
        valid = _valid_ip(hop)
        if valid is None:
            return None
        if not _is_trusted_proxy(valid):
            return valid
    # Every hop was a trusted proxy: fall back to the left-most one.
    return _valid_ip(hops[0]) if hops else None


def get_client_ip(request: Request) -> str:
    """
    Resolves the real client IP.

    Forwarded headers (CF-Connecting-IP, True-Client-IP, X-Forwarded-For) are only honoured when the direct
    TCP peer is a trusted proxy (see TRUSTED_PROXY_IPS). Otherwise any client could spoof them and sidestep
    the per-IP anti-abuse quota. Always returns a valid IP string compatible with PostgreSQL INET.
    """
    peer = _valid_ip(request.client.host) if request.client and request.client.host else None

    if peer is None or _is_trusted_proxy(peer):
        for header in ("CF-Connecting-IP", "True-Client-IP"):
            valid = _valid_ip(request.headers.get(header))
            if valid:
                return valid
        forwarded = _client_ip_from_forwarded_for(request.headers.get("X-Forwarded-For"))
        if forwarded:
            return forwarded

    return peer or "127.0.0.1"


def get_device_fingerprint(request: Request) -> str:
    """
    Extracts the unique hardware/browser visitor ID from request headers.
    Provided by the frontend FingerprintJS library.
    """
    visitor_id = request.headers.get("X-Device-Fingerprint") or request.headers.get("X-Visitor-Id")
    visitor_id = (visitor_id or "").strip()
    if len(visitor_id) < 8:
        # If client blocked JS or sent empty, synthesize fingerprint based on IP + User-Agent
        user_agent = request.headers.get("User-Agent", "Unknown-Browser")
        ip = get_client_ip(request)
        synth_hash = hashlib.sha256(f"{ip}_{user_agent}".encode()).hexdigest()[:24]
        return f"synth_{synth_hash}"

    # Bound the size of a client supplied value before it is stored in the database.
    return visitor_id[:MAX_FINGERPRINT_LENGTH]


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> UserProfile:
    """
    Validates Supabase JWT session token passed in Authorization header.
    Returns user details and profile tier. Auto-creates missing profiles safely.

    Deliberately a plain `def`: the Supabase client is synchronous, so FastAPI runs this dependency in
    its threadpool instead of blocking the event loop.
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
                headers={"WWW-Authenticate": "Bearer"},
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
            tier=profile_data.get("tier") or "free",
            subscription_status=profile_data.get("subscription_status") or "inactive",
            current_period_end=profile_data.get("current_period_end"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
