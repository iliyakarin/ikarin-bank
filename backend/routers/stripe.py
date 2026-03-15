from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import stripe
import logging
import json

from auth_utils import get_db, get_current_user
from database import User, Subscription
from schemas.stripe import (
    CheckoutSessionCreate, CheckoutSessionResponse,
    PortalSessionCreate, PortalSessionResponse,
    PaymentIntentCreate, PaymentIntentResponse
)
from services.stripe_service import handle_checkout_completed, handle_subscription_deleted

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["Stripe"])

from config import settings

# Initialize Stripe
stripe.api_key = settings.STRIPE_API_KEY
WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET
# Optional: Use stripe-mock if STRIPE_MOCK_URL is provided for tests
if settings.STRIPE_MOCK_URL:
    stripe.api_base = settings.STRIPE_MOCK_URL

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    payload: CheckoutSessionCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Creates a Stripe Checkout Session for one-time payments or subscriptions.
    """
    try:
        # Standardize metadata
        metadata = {
            "user_id": current_user.id,
            "user_email": current_user.email,
            "mode": payload.mode
        }

        checkout_params = {
            "payment_method_types": ["card"],
            "line_items": [{
                "price_data": {
                    "currency": payload.currency,
                    "unit_amount": payload.amount,
                    "product_data": {
                        "name": "Karin Bank Deposit" if payload.mode == "payment" else "Karin Black Subscription",
                    },
                },
                "quantity": 1,
            }],
            "mode": payload.mode,
            "success_url": payload.success_url,
            "cancel_url": payload.cancel_url,
            "client_reference_id": str(current_user.id),
            "metadata": metadata,
            "customer_email": current_user.email,
        }

        # Automatic Tax
        # checkout_params["automatic_tax"] = {"enabled": True}

        session = stripe.checkout.Session.create(**checkout_params)
        return CheckoutSessionResponse(id=session.id, url=session.url)
    except Exception as e:
        logger.error(f"Stripe Checkout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/payment_intents", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payload: PaymentIntentCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Creates a Stripe PaymentIntent for use with Payment Element.
    """
    try:
        # Standardize metadata
        metadata = payload.metadata or {}
        metadata.update({
            "user_id": current_user.id,
            "user_email": current_user.email,
            "type": "deposit"
        })

        intent = stripe.PaymentIntent.create(
            amount=payload.amount,
            currency=payload.currency,
            automatic_payment_methods={"enabled": True},
            metadata=metadata,
        )

        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            id=intent.id
        )
    except Exception as e:
        logger.error(f"PaymentIntent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    payload: PortalSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a Stripe Customer Portal Session for subscription management.
    """
    # In a real app, we'd store stripe_customer_id on the User model
    # For now, we'll search by email or use the client_id
    try:
        customers = stripe.Customer.list(email=current_user.email, limit=1).data
        if not customers:
            raise HTTPException(status_code=404, detail="Stripe customer not found")
        
        customer_id = customers[0].id
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=payload.return_url,
        )
        return PortalSessionResponse(url=session.url)
    except Exception as e:
        logger.error(f"Stripe Portal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handles Stripe Webhook events.
    """
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    logger.info(f"Webhook received: {event['type']}")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_checkout_completed(session, db)
    
    elif event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        # Only fulfill if it's not from a checkout session (which has its own handler)
        # We check metadata for 'type': 'deposit' which we set in create_payment_intent
        if intent.get("metadata", {}).get("type") == "deposit":
            await handle_checkout_completed(intent, db)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await handle_subscription_deleted(subscription, db)
    
    elif event['type'] == 'payment_intent.payment_failed':
        intent = event['data']['object']
        logger.warning(f"Payment failed for intent {intent['id']}: {intent.get('last_payment_error', {}).get('message')}")

    return {"status": "success"}

@router.get("/subscriptions/me")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        ).order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()
    if not sub:
        return {"active": False}
    
    return {
        "active": True,
        "plan_name": sub.plan_name,
        "amount": float(sub.amount / 100),
        "current_period_end": sub.current_period_end.isoformat(),
        "status": sub.status
    }
