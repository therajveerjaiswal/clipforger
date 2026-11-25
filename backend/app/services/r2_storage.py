import os
import logging
from typing import Optional
import boto3
from botocore.config import Config
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


class R2StorageService:
    """
    Cloudflare R2 Object Storage integration (S3-compatible) with lazy client
    initialization and automatic Supabase Storage fallback when R2 is not configured.
    """

    def __init__(self):
        self.bucket_name = settings.R2_BUCKET_NAME
        self.public_domain = settings.R2_PUBLIC_DOMAIN
        self._s3_client = None

    @property
    def endpoint_url(self) -> str:
        if settings.R2_ENDPOINT_URL:
            return settings.R2_ENDPOINT_URL
        if settings.R2_ACCOUNT_ID:
            return f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        return ""

    @property
    def is_r2_configured(self) -> bool:
        return bool(
            self.endpoint_url
            and settings.R2_ACCESS_KEY_ID
            and settings.R2_SECRET_ACCESS_KEY
            and self.bucket_name
        )

    def _get_s3_client(self):
        if self._s3_client is None:
            if not self.is_r2_configured:
                raise RuntimeError("Cloudflare R2 credentials are not configured.")
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        return self._s3_client

    def _upload_to_supabase_storage(self, local_path: str, object_key: str, content_type: str) -> str:
        """Fallback upload to Supabase Storage bucket when R2 is not configured."""
        supabase = get_supabase_admin()
        bucket = settings.SUPABASE_STORAGE_BUCKET or "clips"

        try:
            supabase.storage.create_bucket(bucket, options={"public": True})
        except Exception:
            # Bucket likely already exists
            pass

        with open(local_path, "rb") as f:
            file_bytes = f.read()

        supabase.storage.from_(bucket).upload(
            path=object_key,
            file=file_bytes,
            file_options={"content-type": content_type, "x-upsert": "true"},
        )
        public_url = supabase.storage.from_(bucket).get_public_url(object_key)
        return str(public_url).rstrip("?")

    def upload_file(self, local_path: str, object_key: str, content_type: str = "video/mp4") -> str:
        """
        Uploads a local file to Cloudflare R2 (or Supabase Storage if R2 is not configured).
        Returns the public CDN URL or presigned URL.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        if not self.is_r2_configured:
            logger.info(
                f"R2 not configured; falling back to Supabase Storage for '{object_key}'"
            )
            try:
                return self._upload_to_supabase_storage(local_path, object_key, content_type)
            except Exception as e:
                logger.error(f"Supabase Storage fallback upload failed: {e}")
                raise RuntimeError(
                    "Neither Cloudflare R2 nor Supabase Storage is available for upload."
                )

        try:
            extra_args = {"ContentType": content_type}
            logger.info(
                f"Uploading {local_path} to R2 bucket '{self.bucket_name}' key '{object_key}'"
            )
            client = self._get_s3_client()
            client.upload_file(
                Filename=local_path,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args,
            )

            # If a custom public domain or R2 public bucket URL is set
            if self.public_domain:
                clean_domain = self.public_domain.rstrip("/")
                if not clean_domain.startswith(("http://", "https://")):
                    clean_domain = f"https://{clean_domain}"
                return f"{clean_domain}/{object_key}"

            # Otherwise generate a long-lived presigned URL (48 hours = 172800 seconds)
            return self.generate_presigned_url(object_key, expiration_seconds=172800)

        except Exception as e:
            logger.error(f"Failed to upload to Cloudflare R2: {e}")
            raise RuntimeError(f"R2 Storage upload error: {str(e)}")

    def generate_presigned_url(self, object_key: str, expiration_seconds: int = 172800) -> str:
        """Generates a secure presigned GET URL for downloading or playing the reel."""
        try:
            client = self._get_s3_client()
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration_seconds,
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return f"https://{self.bucket_name}.r2.cloudflarestorage.com/{object_key}"

    def delete_file(self, object_key: str) -> bool:
        """Deletes an object from R2 or Supabase Storage."""
        try:
            if self.is_r2_configured:
                client = self._get_s3_client()
                client.delete_object(Bucket=self.bucket_name, Key=object_key)
                return True
            supabase = get_supabase_admin()
            bucket = settings.SUPABASE_STORAGE_BUCKET or "clips"
            supabase.storage.from_(bucket).remove([object_key])
            return True
        except Exception as e:
            logger.warning(f"Could not delete storage object {object_key}: {e}")
            return False


r2_service = R2StorageService()
