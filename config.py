import os
import tempfile
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_temp_dir() -> str:
    return os.getenv("TEMP_DIR") or os.path.join(tempfile.gettempdir(), "clipforge")


def _ensure_rediss_ssl_param(url: str, cert_reqs: str) -> str:
    """
    Celery 5.3's Redis backend requires `ssl_cert_reqs` in the query string of `rediss://` URLs
    (such as Upstash Redis). Automatically append it if omitted so raw Upstash URLs work out of the box.
    """
    if not url or not url.startswith("rediss://"):
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "ssl_cert_reqs" not in query:
        mapping = {
            "required": "CERT_REQUIRED",
            "optional": "CERT_OPTIONAL",
            "none": "CERT_NONE",
        }
        query["ssl_cert_reqs"] = mapping.get(cert_reqs.strip().lower(), "CERT_REQUIRED")
        parsed = parsed._replace(query=urlencode(query))
        return urlunparse(parsed)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "production"
    APP_NAME: str = "ClipForge AI"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_API_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: str = ""

    # Supabase (Database, Auth, and Object Storage)
    NEXT_PUBLIC_SUPABASE_URL: str = "https://placeholder.supabase.co"
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL: str = ""
    SUPABASE_STORAGE_BUCKET: str = "clips"

    # Redis & Celery (Upstash Redis free tier or local Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    # True on Render Free tier (runs background jobs inside the web service without a paid worker)
    USE_IN_PROCESS_WORKER: bool = False
    # TLS certificate verification for rediss:// URLs: "required" (default), "optional" or "none".
    REDIS_SSL_CERT_REQS: str = "required"

    # Razorpay
    NEXT_PUBLIC_RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_PRO_PLAN_ID: str = ""

    # AI & Speech
    GEMINI_API_KEY: str = ""
    # Comma-separated, tried in order. Google retires Gemini models regularly, so keep this configurable.
    GEMINI_MODELS: str = "gemini-3.6-flash,gemini-3.5-flash-lite"
    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Security: forwarded-IP headers (CF-Connecting-IP, X-Forwarded-For, ...) are only honoured when the
    # direct TCP peer is inside one of these addresses / CIDR ranges.
    TRUSTED_PROXY_IPS: str = "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Scratch / Temp Directory for Video Processing
    TEMP_DIR: str = _default_temp_dir()

    @model_validator(mode="after")
    def sync_redis_urls(self):
        # If Upstash/Render provides REDIS_URL without separate Celery URLs, derive them automatically
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        self.CELERY_BROKER_URL = _ensure_rediss_ssl_param(self.CELERY_BROKER_URL, self.REDIS_SSL_CERT_REQS)
        self.CELERY_RESULT_BACKEND = _ensure_rediss_ssl_param(self.CELERY_RESULT_BACKEND, self.REDIS_SSL_CERT_REQS)
        return self

    @property
    def gemini_model_list(self) -> List[str]:
        return [m.strip() for m in self.GEMINI_MODELS.split(",") if m.strip()]


settings = Settings()
