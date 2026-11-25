import os
import logging
from typing import List
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("clipforge")

os.makedirs(settings.TEMP_DIR, exist_ok=True)


def _normalize_origin(raw: str) -> str:
    origin = raw.strip().rstrip("/")
    if not origin:
        return ""
    if not origin.startswith(("http://", "https://")):
        scheme = "http" if origin.startswith(("localhost", "127.0.0.1")) else "https"
        origin = f"{scheme}://{origin}"
    return origin


def _build_cors_origins() -> List[str]:
    candidates = [
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if settings.ALLOWED_ORIGINS:
        candidates.extend(settings.ALLOWED_ORIGINS.split(","))

    seen = set()
    normalized: List[str] = []
    for item in candidates:
        clean = _normalize_origin(item)
        if clean and clean not in seen:
            seen.add(clean)
            normalized.append(clean)
    return normalized


app = FastAPI(
    title=settings.APP_NAME,
    description="High-Action AI Gaming Reel & Highlight Clipper SaaS Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = _build_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for browser and platform checks."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


# Include API Routers
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error processing {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )
