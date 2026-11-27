import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import razorpay
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


class PaymentConfigError(RuntimeError):
    """Razorpay is not (fully) configured on this deployment."""


class PaymentGatewayError(RuntimeError):
    """Razorpay (or the follow-up database write) failed. Details are logged, never shown to end users."""


class RazorpayService:
    """
    Direct Indian Bank Settlement & Subscription Management via Razorpay API.
    Handles recurring subscription billing, signature validation, and webhooks.
    """

    def __init__(self):
        self.key_id = settings.NEXT_PUBLIC_RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self.pro_plan_id = settings.RAZORPAY_PRO_PLAN_ID

        if self.key_id and self.key_secret:
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
        else:
            self.client = None
            logger.warning("Razorpay credentials not fully configured.")

    def create_subscription(self, user_id: str, user_email: str, billing_cycle: str = "monthly") -> Dict[str, Any]:
        """
        Creates a Razorpay subscription for Pro membership (e.g. ₹499/mo).
        """
        if not self.client:
            raise PaymentConfigError(
                "Razorpay client is not initialized. Set NEXT_PUBLIC_RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
            )

        if not self.pro_plan_id:
            raise PaymentConfigError("RAZORPAY_PRO_PLAN_ID is not configured.")

        if billing_cycle != "monthly":
            # Only a monthly plan id is configured; reusing it for "yearly" would bill ₹499 once and stop.
            raise PaymentGatewayError(f"Unsupported billing cycle: {billing_cycle}")

        plan_id = self.pro_plan_id
        amount_paise = 49900  # ₹499.00 INR

        try:
            sub_payload = {
                "plan_id": plan_id,
                "total_count": 12,
                "quantity": 1,
                "customer_notify": 1,
                "notes": {
                    "user_id": user_id,
                    "email": user_email,
                    "tier": "pro",
                },
            }
            subscription = self.client.subscription.create(sub_payload)

            # Record in Supabase
            supabase = get_supabase_admin()
            supabase.table("subscriptions").insert(
                {
                    "user_id": user_id,
                    "razorpay_subscription_id": subscription["id"],
                    "plan_tier": "pro",
                    "billing_cycle": billing_cycle,
                    "amount_in_paise": amount_paise,
                    "status": subscription.get("status", "created"),
                }
            ).execute()

            return {
                "subscription_id": subscription["id"],
                "key_id": self.key_id,
                "amount_in_paise": amount_paise,
                "currency": "INR",
                "name": settings.APP_NAME,
                "description": "ClipForge Pro Tier - Unlimited 1080p Reels & Priority Queue",
            }
        except Exception as e:
            logger.error(f"Razorpay subscription creation failed: {e}")
            raise PaymentGatewayError(str(e)) from e

    def verify_payment_signature(self, payment_id: str, subscription_id: str, signature: str) -> bool:
        """
        Verifies the signature returned by Razorpay checkout widget on the frontend.
        """
        if not self.key_secret:
            return False

        message = f"{payment_id}|{subscription_id}"
        generated_signature = hmac.new(
            key=self.key_secret.encode(),
            msg=message.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)

    def verify_webhook_signature(self, raw_body: bytes, webhook_signature: str) -> bool:
        """
        Verifies incoming Razorpay webhook signature using HMAC-SHA256.
        """
        if not self.webhook_secret:
            logger.warning("RAZORPAY_WEBHOOK_SECRET is not set.")
            return False

        expected_signature = hmac.new(
            key=self.webhook_secret.encode(),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, webhook_signature)

    @staticmethod
    def _period_end(sub_entity: Dict[str, Any]) -> datetime:
        """Uses Razorpay's own billing period end (epoch seconds) when present, else now + 30 days."""
        current_end: Optional[Any] = sub_entity.get("current_end")
        if isinstance(current_end, (int, float)) and current_end > 0:
            return datetime.fromtimestamp(current_end, tz=timezone.utc)
        return datetime.now(timezone.utc) + timedelta(days=30)

    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes webhook callbacks from Razorpay and upgrades user tier automatically in PostgreSQL.
        """
        event_name = event_data.get("event")
        payload = event_data.get("payload") or {}
        supabase = get_supabase_admin()

        logger.info(f"Processing Razorpay webhook event: {event_name}")

        if event_name in ["subscription.charged", "payment.captured"]:
            sub_entity = (payload.get("subscription") or {}).get("entity") or {}
            payment_entity = (payload.get("payment") or {}).get("entity") or {}

            sub_id = sub_entity.get("id") or payment_entity.get("subscription_id")
            # Only subscription payments may upgrade an account; stray one-off payments are ignored.
            if not sub_id:
                return {"status": "ignored", "event": event_name}

            notes = sub_entity.get("notes") or payment_entity.get("notes") or {}
            user_id = notes.get("user_id")

            # Find user by subscription_id if not in notes
            if not user_id:
                sub_row = (
                    supabase.table("subscriptions")
                    .select("user_id")
                    .eq("razorpay_subscription_id", sub_id)
                    .limit(1)
                    .execute()
                )
                if sub_row and sub_row.data:
                    user_id = sub_row.data[0].get("user_id")

            if user_id:
                period_end = self._period_end(sub_entity)

                # Upgrade user profile to Pro
                supabase.table("profiles").update(
                    {
                        "tier": "pro",
                        "subscription_id": sub_id,
                        "subscription_status": "active",
                        "current_period_end": period_end.isoformat(),
                    }
                ).eq("id", user_id).execute()

                # Update subscription record
                supabase.table("subscriptions").update(
                    {
                        "status": "active",
                        "razorpay_payment_id": payment_entity.get("id"),
                        "current_period_end": period_end.isoformat(),
                        "raw_webhook_payload": event_data,
                    }
                ).eq("razorpay_subscription_id", sub_id).execute()

                logger.info(f"User {user_id} successfully upgraded to PRO.")
                return {"status": "upgraded", "user_id": user_id, "tier": "pro"}

        elif event_name in ["subscription.cancelled", "subscription.halted", "subscription.completed"]:
            sub_entity = (payload.get("subscription") or {}).get("entity") or {}
            sub_id = sub_entity.get("id")

            if sub_id:
                ended_normally = event_name == "subscription.completed"
                supabase.table("profiles").update(
                    {
                        "tier": "free",
                        "subscription_status": "inactive" if ended_normally else "cancelled",
                    }
                ).eq("subscription_id", sub_id).execute()

                supabase.table("subscriptions").update(
                    {
                        "status": "expired" if ended_normally else "cancelled",
                        "raw_webhook_payload": event_data,
                    }
                ).eq("razorpay_subscription_id", sub_id).execute()

                return {"status": "downgraded", "sub_id": sub_id}

        return {"status": "ignored", "event": event_name}


razorpay_service = RazorpayService()
