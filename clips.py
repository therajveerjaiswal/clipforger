import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.models.schemas import UserProfile, ReelClipResponse, UpdateSubtitleStyleRequest

router = APIRouter()


def _to_clip_response(row: dict) -> ReelClipResponse:
    return ReelClipResponse(
        id=row["id"],
        job_id=row["job_id"],
        user_id=row["user_id"],
        title=row["title"],
        start_time=float(row["start_time"]),
        end_time=float(row["end_time"]),
        duration_seconds=float(row["duration_seconds"]),
        highlight_score=float(row.get("highlight_score") or 0.0),
        hook_text=row.get("hook_text"),
        transcript_text=row.get("transcript_text"),
        subtitle_style=row.get("subtitle_style"),
        aspect_ratio=row.get("aspect_ratio") or "9:16",
        resolution=row.get("resolution") or "720p",
        public_url=row.get("public_url"),
        thumbnail_url=row.get("thumbnail_url"),
        download_count=row.get("download_count") or 0,
        expires_at=str(row["expires_at"]),
        created_at=str(row["created_at"]),
    )


def _uuid_or_404(value: str, detail: str = "Reel clip not found.") -> str:
    """PostgREST rejects malformed UUIDs with a database error (HTTP 500); report them as 'not found'."""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from None


# Handlers are plain `def` so FastAPI runs the synchronous Supabase calls in its threadpool.
@router.get("/", response_model=List[ReelClipResponse])
def list_user_clips(
    job_id: Optional[str] = Query(None, description="Filter clips by specific video job ID"),
    current_user: UserProfile = Depends(get_current_user),
):
    """Lists all non-expired vertical reels generated for the authenticated user."""
    supabase = get_supabase_admin()
    now_iso = datetime.now(timezone.utc).isoformat()
    query = (
        supabase.table("reel_clips")
        .select("*")
        .eq("user_id", current_user.id)
        # Clips (and their presigned URLs) expire after 48h; listing them would only show dead links.
        .gt("expires_at", now_iso)
    )

    if job_id:
        query = query.eq("job_id", _uuid_or_404(job_id, "Job not found."))

    res = query.order("created_at", desc=True).limit(50).execute()
    return [_to_clip_response(row) for row in (res.data or [])]


@router.get("/{clip_id}", response_model=ReelClipResponse)
def get_clip_details(
    clip_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieves single clip details for preview and player playback."""
    clip_id = _uuid_or_404(clip_id)
    supabase = get_supabase_admin()
    res = supabase.table("reel_clips").select("*").eq("id", clip_id).limit(1).execute()

    if not res or not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel clip not found.")

    row = res.data[0]
    if row["user_id"] != current_user.id and not row.get("is_public", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _to_clip_response(row)


@router.post("/{clip_id}/download")
def track_clip_download(
    clip_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Increments the download counter for analytics."""
    clip_id = _uuid_or_404(clip_id, "Clip not found.")
    supabase = get_supabase_admin()
    res = (
        supabase.table("reel_clips")
        .select("id, user_id, is_public, download_count, public_url")
        .eq("id", clip_id)
        .limit(1)
        .execute()
    )

    if not res or not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")

    row = res.data[0]
    if row["user_id"] != current_user.id and not row.get("is_public", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    current_count = row.get("download_count") or 0
    supabase.table("reel_clips").update({"download_count": current_count + 1}).eq("id", clip_id).execute()

    return {"status": "success", "download_url": row.get("public_url")}


@router.put("/{clip_id}/subtitles", response_model=ReelClipResponse)
def update_clip_subtitles(
    clip_id: str,
    update_req: UpdateSubtitleStyleRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """Updates subtitle style preferences for the clip."""
    clip_id = _uuid_or_404(clip_id, "Clip not found or unauthorized.")
    supabase = get_supabase_admin()
    update_data = {"subtitle_style": update_req.subtitle_style.model_dump()}
    res = (
        supabase.table("reel_clips")
        .update(update_data)
        .eq("id", clip_id)
        .eq("user_id", current_user.id)
        .execute()
    )

    if not res or not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found or unauthorized.")

    return _to_clip_response(res.data[0])
