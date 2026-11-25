import ssl
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "clipforge_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

conf_updates = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "task_time_limit": 3600,          # 1 hour maximum per stream analysis job
    "worker_prefetch_multiplier": 1,  # Fair distribution among CPU workers
    "worker_max_tasks_per_child": 50, # Prevent memory leaks over time
    "broker_connection_retry_on_startup": True,
}

# Support TLS Redis (rediss://) used by Render Key Value / Upstash
if settings.CELERY_BROKER_URL.startswith("rediss://"):
    conf_updates["broker_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_NONE}
if settings.CELERY_RESULT_BACKEND.startswith("rediss://"):
    conf_updates["redis_backend_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app.conf.update(**conf_updates)
