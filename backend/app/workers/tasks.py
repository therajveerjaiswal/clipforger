import os
import shutil
import uuid
import logging
from typing import Dict, Any
from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin
from app.services.yt_stream_service import YouTubeStreamService
from app.services.spike_detector import AudioSpikeDetector
from app.services.ai_analyzer import AIAnalyzer
from app.services.video_editor import VideoEditor
from app.services.r2_storage import r2_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_video_stream")
def process_video_stream(
    self,
    job_id: str,
    youtube_url: str,
    user_id: str,
    target_clips: int = 3,
    target_resolution: str = "720p",
    render_mode: str = "blur_split",
) -> Dict[str, Any]:
    """
    Asynchronous Celery pipeline that converts 20-30h streams into 9:16 vertical reels.
    Never downloads the entire video at once.
    """
    supabase = get_supabase_admin()
    job_dir = os.path.join(settings.TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        # Step 1: Fetch Video Metadata (0% -> 20%)
        logger.info(f"[{job_id}] Step 1: Extracting stream metadata for {youtube_url}")
        supabase.table("video_jobs").update(
            {
                "status": "fetching_metadata",
                "progress_percentage": 10,
            }
        ).eq("id", job_id).execute()

        metadata = YouTubeStreamService.extract_metadata(youtube_url)
        video_id = metadata["id"]
        duration = metadata["duration"]

        supabase.table("video_jobs").update(
            {
                "title": metadata.get("title"),
                "channel_name": metadata.get("channel"),
                "thumbnail_url": metadata.get("thumbnail"),
                "duration_seconds": duration,
                "is_livestream": metadata.get("is_live", False) or metadata.get("was_live", False),
                "metadata": metadata,
                "progress_percentage": 20,
            }
        ).eq("id", job_id).execute()

        # Step 2: Download Lightweight Mono Audio (20% -> 35%)
        logger.info(f"[{job_id}] Step 2: Downloading lightweight mono audio stream")
        supabase.table("video_jobs").update(
            {
                "status": "downloading_audio",
                "progress_percentage": 25,
            }
        ).eq("id", job_id).execute()

        audio_path = os.path.join(job_dir, f"{video_id}_audio.mp3")
        resolved_audio_path = YouTubeStreamService.download_lightweight_audio(youtube_url, audio_path)

        # Step 3: Audio RMS Energy Spike Detection (35% -> 50%)
        logger.info(f"[{job_id}] Step 3: Analyzing audio energy spikes")
        supabase.table("video_jobs").update(
            {
                "status": "detecting_spikes",
                "progress_percentage": 40,
            }
        ).eq("id", job_id).execute()

        candidate_moments = AudioSpikeDetector.detect_high_action_moments(
            audio_file_path=resolved_audio_path,
            total_duration=duration,
            target_clips=target_clips,
            min_clip_duration=15.0,
            max_clip_duration=30.0,
        )

        # Free audio file immediately once spike timestamps are extracted
        if os.path.exists(resolved_audio_path):
            try:
                os.remove(resolved_audio_path)
            except Exception:
                pass

        logger.info(f"[{job_id}] Detected {len(candidate_moments)} high-action moments")

        # Step 4: Surgical Video Cutting, Transcription, Subtitle Burning & Storage Upload (50% -> 95%)
        supabase.table("video_jobs").update(
            {
                "status": "cutting_clips",
                "progress_percentage": 50,
            }
        ).eq("id", job_id).execute()

        generated_clips = []
        clip_progress_step = 45 / max(1, len(candidate_moments))

        for idx, moment in enumerate(candidate_moments):
            clip_id = str(uuid.uuid4())
            logger.info(
                f"[{job_id}] Processing clip {idx + 1}/{len(candidate_moments)}: "
                f"{moment['start']}s to {moment['end']}s"
            )

            # 4a: Download ONLY the 15-30s video section
            raw_section_path = os.path.join(job_dir, f"section_{idx}_{clip_id}.mp4")
            cut_video = YouTubeStreamService.download_exact_video_section(
                url=youtube_url,
                start_seconds=moment["start"],
                end_seconds=moment["end"],
                output_filepath=raw_section_path,
                target_resolution=target_resolution,
            )

            # 4b: Transcribe this specific section with faster-whisper
            transcription = AIAnalyzer.transcribe_segment(cut_video)

            # 4c: Call Gemini Flash for Hook and Viral Score
            ai_data = AIAnalyzer.generate_hook_and_caption(
                transcript=transcription["text"],
                game_title=metadata.get("title", "Gaming Stream"),
            )

            # 4d: Generate .ass Karaoke Subtitle Script
            ass_path = os.path.join(job_dir, f"subtitles_{clip_id}.ass")
            VideoEditor.generate_ass_subtitles(
                words_data=transcription["words"],
                output_ass_path=ass_path,
                hook_headline=ai_data["hook"],
            )

            # 4e: Render 9:16 Vertical Reel with Subtitles via FFmpeg
            rendered_reel_path = os.path.join(job_dir, f"reel_{clip_id}.mp4")
            VideoEditor.render_vertical_reel(
                input_video_path=cut_video,
                output_video_path=rendered_reel_path,
                ass_subtitles_path=ass_path,
                resolution=target_resolution,
                mode=render_mode,
            )

            # 4f: Generate Thumbnail (best effort)
            thumbnail_local_path = os.path.join(job_dir, f"thumb_{clip_id}.jpg")
            generated_thumb = VideoEditor.generate_thumbnail(rendered_reel_path, thumbnail_local_path)

            # 4g: Upload to Cloudflare R2 (or Supabase Storage fallback)
            r2_reel_key = f"clips/{user_id}/{clip_id}.mp4"
            r2_thumb_key = f"thumbnails/{user_id}/{clip_id}.jpg"

            reel_public_url = r2_service.upload_file(rendered_reel_path, r2_reel_key, "video/mp4")
            thumb_public_url = (
                r2_service.upload_file(generated_thumb, r2_thumb_key, "image/jpeg")
                if generated_thumb and os.path.exists(generated_thumb)
                else metadata.get("thumbnail")
            )

            file_size = os.path.getsize(rendered_reel_path) if os.path.exists(rendered_reel_path) else 0

            # 4h: Save to Supabase reel_clips
            clip_record = {
                "id": clip_id,
                "job_id": job_id,
                "user_id": user_id,
                "title": ai_data.get("title", f"Highlight #{idx + 1}"),
                "start_time": moment["start"],
                "end_time": moment["end"],
                "duration_seconds": moment["duration"],
                "highlight_score": ai_data.get("viral_score", moment["score"]),
                "hook_text": ai_data.get("hook"),
                "transcript_text": transcription["text"],
                "storage_key": r2_reel_key,
                "public_url": reel_public_url,
                "thumbnail_url": thumb_public_url,
                "resolution": target_resolution,
                "file_size_bytes": file_size,
            }
            supabase.table("reel_clips").insert(clip_record).execute()
            generated_clips.append(clip_record)

            # Clean up intermediate cut files immediately to conserve disk
            for p in {raw_section_path, cut_video, rendered_reel_path, thumbnail_local_path, ass_path}:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

            current_progress = int(50 + ((idx + 1) * clip_progress_step))
            supabase.table("video_jobs").update(
                {
                    "progress_percentage": min(95, current_progress),
                }
            ).eq("id", job_id).execute()

        # Step 5: Completion (100%)
        logger.info(f"[{job_id}] Successfully generated {len(generated_clips)} reels.")
        supabase.table("video_jobs").update(
            {
                "status": "completed",
                "progress_percentage": 100,
            }
        ).eq("id", job_id).execute()

        return {
            "status": "success",
            "job_id": job_id,
            "clips_count": len(generated_clips),
        }

    except Exception as exc:
        logger.exception(f"[{job_id}] Video stream processing pipeline failed: {exc}")
        try:
            supabase.table("video_jobs").update(
                {
                    "status": "failed",
                    "error_message": str(exc)[:500],
                }
            ).eq("id", job_id).execute()
        except Exception as db_exc:
            logger.error(f"[{job_id}] Failed to record error status in DB: {db_exc}")
        raise

    finally:
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
            except Exception as e:
                logger.warning(f"Could not remove temp job dir {job_dir}: {e}")
