import json
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.models.schemas import (
    UserProfile,
    CreateSubscriptionOrderRequest,
    CreateSubscriptionOrderResponse,
    VerifyPaymentRequest,
)
from app.services.razorpay_service import razorpay_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-subscription", response_model=CreateSubscriptionOrderResponse)
async def create_subscription(
    sub_req: CreateSubscriptionOrderRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Creates a Razorpay subscription order for Pro membership (e.g. ₹499/mo).
    """
    try:
        sub_data = razorpay_service.create_subscription(
            user_id=current_user.id,
            user_email=current_user.email,
            billing_cycle=sub_req.billing_cycle,
        )
        return CreateSubscriptionOrderResponse(**sub_data)
    except Exception as e:
        logger.error(f"Failed to create subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subscription initialization failed: {str(e)}",
        )


@router.post("/verify")
async def verify_payment(
    verify_req: VerifyPaymentRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Verifies checkout payment signature returned by the client-side Razorpay modal.
    """
    is_valid = razorpay_service.verify_payment_signature(
        payment_id=verify_req.razorpay_payment_id,
        subscription_id=verify_req.razorpay_subscription_id,
        signature=verify_req.razorpay_signature,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature. Authentication failed.",
        )

    period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    # Immediately reflect verified status in DB
    supabase = get_supabase_admin()
    supabase.table("profiles").update(
        {
            "tier": "pro",
            "subscription_id": verify_req.razorpay_subscription_id,
            "subscription_status": "active",
            "current_period_end": period_end,
        }
    ).eq("id", current_user.id).execute()

    return {"status": "success", "message": "Payment verified and Pro tier activated!"}


@router.post("/webhook")
async def razorpay_webhook_listener(
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
):
    """
    Receives automated asynchronous events from Razorpay (subscription charged, renewal, cancellation).
    Verifies HMAC-SHA256 signature to guarantee authentic bank settlements.
    """
    raw_body = await request.body()

    is_verified = razorpay_service.verify_webhook_signature(raw_body, x_razorpay_signature)
    if not is_verified:
        logger.warning("Rejected unverified Razorpay webhook signature attempt.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature.",
        )

    try:
        event_payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload.")

    result = razorpay_service.handle_webhook_event(event_payload)
    return result
