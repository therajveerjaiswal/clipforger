import os
import tempfile
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


def _default_temp_dir() -> str:
    return os.getenv("TEMP_DIR") or os.path.join(tempfile.gettempdir(), "clipforge")


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

    # Supabase (defaults prevent boot crashes during setup)
    NEXT_PUBLIC_SUPABASE_URL: str = "https://placeholder.supabase.co"
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL: str = ""
    SUPABASE_STORAGE_BUCKET: str = "clips"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    USE_IN_PROCESS_WORKER: bool = False

    # Cloudflare R2 (Optional: falls back to Supabase Storage if empty)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "gaming-reel-clips"
    R2_PUBLIC_DOMAIN: str = ""
    R2_ENDPOINT_URL: str = ""

    # Razorpay
    NEXT_PUBLIC_RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_PRO_PLAN_ID: str = ""

    # AI & Speech
    GEMINI_API_KEY: str = ""
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Security
    JWT_SECRET: str = "default_fallback_jwt_secret_change_in_production"
    TRUSTED_PROXY_IPS: str = "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Scratch / Temp Directory for Video Processing
    TEMP_DIR: str = _default_temp_dir()

    @field_validator("R2_ENDPOINT_URL", mode="before")
    @classmethod
    def construct_r2_endpoint(cls, v, info):
        if not v and info.data.get("R2_ACCOUNT_ID"):
            return f"https://{info.data['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
        return v or ""

    @model_validator(mode="after")
    def sync_redis_urls(self):
        # If Render/Upstash provides REDIS_URL without separate Celery URLs, derive them automatically
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self


settings = Settings()
