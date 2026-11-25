from fastapi import APIRouter
from app.api.v1.endpoints import jobs, clips, quota, payments

api_router = APIRouter()

api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs & Streams"])
api_router.include_router(clips.router, prefix="/clips", tags=["Reel Clips"])
api_router.include_router(quota.router, prefix="/quota", tags=["Daily Quota & Anti-Abuse"])
api_router.include_router(payments.router, prefix="/payments", tags=["Razorpay Subscriptions"])
