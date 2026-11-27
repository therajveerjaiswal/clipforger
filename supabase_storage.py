import os
import logging
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


class SupabaseStorageService:
    """
    Native Supabase Storage integration (Free Tier compatible, zero Cloudflare R2 / S3 dependency).
    Uploads rendered 9:16 vertical reels and cover thumbnails to a public Supabase Storage bucket.
    """

    def __init__(self):
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET or "clips"
        self._bucket_checked = False

    def _ensure_bucket(self, supabase, bucket: str) -> None:
        if self._bucket_checked:
            return
        try:
            supabase.storage.create_bucket(bucket, options={"public": True})
        except Exception as exc:
            # Bucket most likely exists already; any real auth/network problem will surface during upload.
            logger.debug(f"create_bucket('{bucket}') skipped: {exc}")
        self._bucket_checked = True

    def upload_file(self, local_path: str, object_key: str, content_type: str = "video/mp4") -> str:
        """
        Uploads a local file to Supabase Storage and returns its public URL.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        bucket = settings.SUPABASE_STORAGE_BUCKET or self.bucket_name or "clips"
        supabase = get_supabase_admin()
        self._ensure_bucket(supabase, bucket)

        try:
            logger.info(f"Uploading {local_path} to Supabase Storage bucket '{bucket}' key '{object_key}'")
            with open(local_path, "rb") as f:
                file_bytes = f.read()

            supabase.storage.from_(bucket).upload(
                path=object_key,
                file=file_bytes,
                file_options={"content-type": content_type, "x-upsert": "true"},
            )
            public_url = supabase.storage.from_(bucket).get_public_url(object_key)
            return str(public_url).rstrip("?")
        except Exception as e:
            logger.error(f"Supabase Storage upload failed for '{object_key}': {e}")
            raise RuntimeError(f"Supabase Storage upload error: {str(e)}") from e

    def delete_file(self, object_key: str) -> bool:
        """Deletes an object from Supabase Storage."""
        try:
            bucket = settings.SUPABASE_STORAGE_BUCKET or self.bucket_name or "clips"
            supabase = get_supabase_admin()
            supabase.storage.from_(bucket).remove([object_key])
            return True
        except Exception as e:
            logger.warning(f"Could not delete Supabase Storage object {object_key}: {e}")
            return False


storage_service = SupabaseStorageService()
