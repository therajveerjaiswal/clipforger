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
    # The soft limit raises SoftTimeLimitExceeded inside the task so the job can be marked "failed";
    # the hard limit (SIGKILL) is only a last resort and would leave the job stuck in a processing state.
    "task_soft_time_limit": 3300,
    "task_time_limit": 3600,          # 1 hour maximum per stream analysis job
    "worker_prefetch_multiplier": 1,  # Fair distribution among CPU workers
    "worker_max_tasks_per_child": 50, # Prevent memory leaks over time
    "broker_connection_retry_on_startup": True,
    "task_ignore_result": settings.USE_IN_PROCESS_WORKER,
}

_SSL_CERT_REQS = {
    "required": ssl.CERT_REQUIRED,
    "optional": ssl.CERT_OPTIONAL,
    "none": ssl.CERT_NONE,
}
_cert_reqs = _SSL_CERT_REQS.get(settings.REDIS_SSL_CERT_REQS.strip().lower(), ssl.CERT_REQUIRED)

# Support TLS Redis (rediss://) used by Render Key Value / Upstash.
# Certificates are verified by default; set REDIS_SSL_CERT_REQS=none only for self-signed providers.
if settings.CELERY_BROKER_URL.startswith("rediss://"):
    conf_updates["broker_use_ssl"] = {"ssl_cert_reqs": _cert_reqs}
if settings.CELERY_RESULT_BACKEND.startswith("rediss://"):
    conf_updates["redis_backend_use_ssl"] = {"ssl_cert_reqs": _cert_reqs}

celery_app.conf.update(**conf_updates)
