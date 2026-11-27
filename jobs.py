import re
import uuid
import logging
from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qs
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from app.core.config import settings
from app.core.security import get_current_user, get_client_ip, get_device_fingerprint
from app.core.supabase_client import get_supabase_admin
from app.models.schemas import UserProfile, CreateJobRequest, JobResponse
from app.workers.tasks import process_video_stream

logger = logging.getLogger(__name__)
router = APIRouter()

YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
YOUTUBE_DOMAINS = ("youtube.com", "youtube-nocookie.com")


def _is_youtube_host(host: str) -> bool:
    """True only for youtube.com / youtube-nocookie.com and their real subdomains (not look-alikes)."""
    return any(host == domain or host.endswith(f".{domain}") for domain in YOUTUBE_DOMAINS)


def extract_youtube_id(url: str) -> str:
    """Extracts an 11-character YouTube video ID from standard, shorts, live, or youtu.be URLs."""
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid YouTube stream or video URL. Please provide a valid YouTube link.",
    )

    candidate = (url or "").strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"

    try:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
    except ValueError:
        raise invalid from None

    video_id = ""
    if host in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif _is_youtube_host(host):
        if parsed.path.rstrip("/") == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("live", "shorts", "embed", "v"):
                video_id = parts[1]

    if not YOUTUBE_ID_RE.match(video_id):
        raise invalid
    return video_id


def canonical_youtube_url(video_id: str) -> str:
    """The only URL ever handed to yt-dlp: rebuilt from the validated ID, never the raw user input."""
    return f"https://www.youtube.com/watch?v={video_id}"


def _run_in_process_job(**kwargs) -> None:
    try:
        process_video_stream.run(**kwargs)
    except Exception as exc:
        logger.error(f"In-process background job failed: {exc}")


def _refund_quota(user_id: str, visitor_id: str, client_ip: str, videos: int, reels: int) -> None:
    """Best-effort refund of quota consumed for a job that could never be started."""
    try:
        get_supabase_admin().rpc(
            "refund_daily_quota",
            {
                "p_user_id": user_id,
                "p_visitor_id": visitor_id,
                "p_ip_address": client_ip,
                "p_videos_to_remove": videos,
                "p_reels_to_remove": reels,
            },
        ).execute()
    except Exception as exc:
        logger.warning(f"Could not refund quota for user {user_id}: {exc}")


def _job_to_response(row: Dict[str, Any]) -> JobResponse:
    return JobResponse(
        id=row["id"],
        user_id=row["user_id"],
        youtube_url=row["youtube_url"],
        video_id=row["video_id"],
        title=row.get("title"),
        channel_name=row.get("channel_name"),
        thumbnail_url=row.get("thumbnail_url"),
        duration_seconds=float(row.get("duration_seconds") or 0.0),
        status=row["status"],
        progress_percentage=row.get("progress_percentage") or 0,
        error_message=row.get("error_message"),
        created_at=str(row["created_at"]),
    )


# NOTE: the handlers below are plain `def` on purpose. The Supabase client is synchronous, and FastAPI runs
# sync handlers in a threadpool, whereas `async def` would block the whole event loop on every DB call.
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_stream_clipping_job(
    request: Request,
    job_req: CreateJobRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Submits a YouTube stream URL for AI reel extraction.
    Enforces multi-account anti-abuse quota (IP + Browser Fingerprint + User ID).
    """
    video_id = extract_youtube_id(job_req.youtube_url)
    youtube_url = canonical_youtube_url(video_id)
    client_ip = get_client_ip(request)
    visitor_id = get_device_fingerprint(request)
    supabase = get_supabase_admin()

    # Determine resolution tier
    resolution = "1080p" if current_user.tier in ["pro", "enterprise"] else "720p"

    # Enforce daily quota via atomic PostgreSQL stored procedure
    quota_res = supabase.rpc(
        "check_and_enforce_daily_quota",
        {
            "p_user_id": current_user.id,
            "p_visitor_id": visitor_id,
            "p_ip_address": client_ip,
            "p_videos_to_add": 1,
            "p_reels_to_add": job_req.target_clips,
        },
    ).execute()

    raw_quota = quota_res.data
    quota_data = raw_quota[0] if isinstance(raw_quota, list) and raw_quota else (raw_quota or {})
    if not quota_data.get("allowed", False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=quota_data.get("message", "Daily free limit reached. Please upgrade to Pro."),
        )

    # Pro/Enterprise users are not metered by the stored procedure, so there is nothing to refund for them.
    quota_consumed = current_user.tier not in ["pro", "enterprise"]

    job_id = str(uuid.uuid4())
    job_record = {
        "id": job_id,
        "user_id": current_user.id,
        "youtube_url": youtube_url,
        "video_id": video_id,
        "status": "queued",
        "progress_percentage": 0,
    }

    try:
        insert_res = supabase.table("video_jobs").insert(job_record).execute()
        created_job = insert_res.data[0]
    except Exception as exc:
        logger.exception(f"Failed to create job row {job_id}: {exc}")
        if quota_consumed:
            _refund_quota(current_user.id, visitor_id, client_ip, 1, job_req.target_clips)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create the job right now. Please try again shortly.",
        ) from exc

    task_kwargs = {
        "job_id": job_id,
        "youtube_url": youtube_url,
        "user_id": current_user.id,
        "target_clips": job_req.target_clips,
        "target_resolution": resolution,
        "render_mode": job_req.render_mode,
    }

    if settings.USE_IN_PROCESS_WORKER:
        background_tasks.add_task(_run_in_process_job, **task_kwargs)
        logger.info(f"Scheduled in-process clipping job {job_id} for user {current_user.id}")
    else:
        try:
            process_video_stream.delay(**task_kwargs)
            logger.info(f"Enqueued clipping job {job_id} for user {current_user.id}")
        except Exception as exc:
            logger.exception(f"Failed to enqueue Celery task for job {job_id}: {exc}")
            try:
                supabase.table("video_jobs").update(
                    {
                        "status": "failed",
                        "error_message": "Background worker queue is unavailable. Check Redis/Celery service.",
                    }
                ).eq("id", job_id).execute()
            except Exception as db_exc:
                logger.warning(f"Could not mark job {job_id} as failed: {db_exc}")
            if quota_consumed:
                _refund_quota(current_user.id, visitor_id, client_ip, 1, job_req.target_clips)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Background processing queue is temporarily unavailable. Please try again shortly.",
            ) from exc

    return _job_to_response(created_job)


def _parse_uuid_or_404(value: str, detail: str) -> str:
    """PostgREST answers malformed UUIDs with a 500-style error; treat them as plain 'not found'."""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from None


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Fetches real-time status and progress percentage for a video job."""
    job_id = _parse_uuid_or_404(job_id, "Job not found.")
    supabase = get_supabase_admin()
    res = (
        supabase.table("video_jobs")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", current_user.id)
        .limit(1)
        .execute()
    )

    if not res or not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    return _job_to_response(res.data[0])


@router.get("/", response_model=List[JobResponse])
def list_recent_jobs(
    current_user: UserProfile = Depends(get_current_user),
):
    """Lists recent jobs processed by the user."""
    supabase = get_supabase_admin()
    res = (
        supabase.table("video_jobs")
        .select("*")
        .eq("user_id", current_user.id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )

    return [_job_to_response(row) for row in (res.data or [])]
