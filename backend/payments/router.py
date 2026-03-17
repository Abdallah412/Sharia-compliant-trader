"""Stripe payment integration: checkout, webhook, customer portal."""

import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
    STRIPE_PRO_MONTHLY_PRICE_ID, STRIPE_PRO_ANNUAL_PRICE_ID,
    STRIPE_MANAGED_MONTHLY_PRICE_ID, STRIPE_MANAGED_ANNUAL_PRICE_ID,
    FRONTEND_URL,
)
from database import get_db
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger("payments")

stripe.api_key = STRIPE_SECRET_KEY

PRICE_MAP = {
    "pro_monthly": STRIPE_PRO_MONTHLY_PRICE_ID,
    "pro_annual": STRIPE_PRO_ANNUAL_PRICE_ID,
    "managed_monthly": STRIPE_MANAGED_MONTHLY_PRICE_ID,
    "managed_annual": STRIPE_MANAGED_ANNUAL_PRICE_ID,
}

PRICE_TO_TIER = {}
if STRIPE_PRO_MONTHLY_PRICE_ID:
    PRICE_TO_TIER[STRIPE_PRO_MONTHLY_PRICE_ID] = "pro"
if STRIPE_PRO_ANNUAL_PRICE_ID:
    PRICE_TO_TIER[STRIPE_PRO_ANNUAL_PRICE_ID] = "pro"
if STRIPE_MANAGED_MONTHLY_PRICE_ID:
    PRICE_TO_TIER[STRIPE_MANAGED_MONTHLY_PRICE_ID] = "managed"
if STRIPE_MANAGED_ANNUAL_PRICE_ID:
    PRICE_TO_TIER[STRIPE_MANAGED_ANNUAL_PRICE_ID] = "managed"


class CheckoutRequest(BaseModel):
    plan: str  # pro_monthly, pro_annual, managed_monthly, managed_annual


@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    price_id = PRICE_MAP.get(body.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Create or reuse Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        user.stripe_customer_id = customer.id
        await db.commit()

    is_managed = body.plan.startswith("managed")

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/settings?payment=success",
        cancel_url=f"{FRONTEND_URL}/pricing?payment=cancelled",
        subscription_data={
            "trial_period_days": 30 if is_managed else 0,
            "metadata": {"user_id": user.id},
        },
    )

    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Process Stripe webhook events. MUST verify signature."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    if not sig or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        await _handle_subscription_change(data, db)

    return {"status": "ok"}


async def _handle_checkout_completed(session: dict, db: AsyncSession):
    """Activate subscription after successful checkout."""
    from sqlalchemy import select

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("No user found for Stripe customer %s", customer_id)
        return

    # Fetch subscription to get price ID
    sub = stripe.Subscription.retrieve(subscription_id)
    price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
    tier = PRICE_TO_TIER.get(price_id, "pro")

    user.tier = tier
    user.stripe_subscription_id = subscription_id
    user.subscription_status = sub.get("status", "active")

    if sub.get("trial_end"):
        user.trial_end_date = datetime.fromtimestamp(sub["trial_end"], tz=timezone.utc)

    await db.commit()
    logger.info("User %s upgraded to %s tier", user.id, tier)


async def _handle_subscription_change(sub: dict, db: AsyncSession):
    """Handle subscription updates (upgrade/downgrade/cancel)."""
    from sqlalchemy import select

    customer_id = sub.get("customer")
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    status = sub.get("status")
    user.subscription_status = status

    if status in ("canceled", "unpaid", "incomplete_expired"):
        user.tier = "free"
        logger.info("User %s downgraded to free (status: %s)", user.id, status)
    else:
        price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
        tier = PRICE_TO_TIER.get(price_id, user.tier)
        user.tier = tier

    if sub.get("current_period_end"):
        user.subscription_end_date = datetime.fromtimestamp(
            sub["current_period_end"], tz=timezone.utc
        )

    await db.commit()


@router.post("/create-portal-session")
async def create_portal_session(user: User = Depends(get_current_user)):
    """Redirect user to Stripe Customer Portal to manage subscription."""
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/settings",
    )
    return {"portal_url": session.url}


@router.get("/status")
async def payment_status(user: User = Depends(get_current_user)):
    return {
        "tier": user.tier,
        "subscription_status": user.subscription_status,
        "subscription_end_date": user.subscription_end_date,
        "trial_end_date": user.trial_end_date,
    }
