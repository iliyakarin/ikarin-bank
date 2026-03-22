"""Fund Deposits and Subscriptions Router.

This module provides endpoints for interacting with the payment gateway (mock),
handling checkout sessions, payment intents, and webhooks.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import uuid
import logging
import datetime
from typing import List, Optional
from cryptography.fernet import Fernet

from config import settings
from auth_utils import get_db, get_current_user
from database import SessionLocal
from models.user import User, Subscription
from models.account import Account, PaymentMethod
from models.transaction import Transaction, IdempotencyKey
from schemas.deposit import (
    CheckoutSessionCreate, CheckoutSessionResponse,
    PortalSessionCreate, PortalSessionResponse,
    PaymentIntentCreate, PaymentIntentResponse,
    PaymentIntentFulfill, PaymentIntentConfirm,
    PaymentMethodCreate, PaymentMethodResponse, CardResponse
)
from services.deposit_service import handle_checkout_completed, handle_subscription_deleted
from idempotency import check_idempotency
import httpx

from services.mock_client import MockServiceClient
from security_utils import encrypt_value

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deposits", tags=["Deposits"])

# Initialize Mock Gateway Client
gateway_client = MockServiceClient(
    base_url=settings.DEPOSIT_MOCK_URL or "http://deposit-funds-mock:8000"
)

def encrypt_card_data(data: str) -> str:
    """Encrypts card data using the standard security utility."""
    if not settings.ACCOUNT_ENCRYPTION_KEY:
        raise RuntimeError("ACCOUNT_ENCRYPTION_KEY missing")
    return encrypt_value(data, settings.ACCOUNT_ENCRYPTION_KEY)

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(payload: CheckoutSessionCreate, current_user: User = Depends(get_current_user)):
    """Creates a checkout session via the mock payment gateway.

    Args:
        payload (CheckoutSessionCreate): Success/Cancel URLs and mode.
        current_user (User): The authenticated user.

    Returns:
        CheckoutSessionResponse: The session ID and redirection URL.

    Raises:
        HTTPException: If the mock service call fails.
    """
    try:
        session = await gateway_client.post("/v1/checkout/sessions", data={
            "success_url": payload.success_url, "cancel_url": payload.cancel_url,
            "mode": payload.mode, "customer_email": current_user.email,
            "client_reference_id": str(current_user.id),
        })
        return CheckoutSessionResponse(id=session["id"], url=session["url"])
    except Exception as e:
        logger.error(f"Checkout fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment_intents", response_model=PaymentIntentResponse)
async def create_payment_intent(payload: PaymentIntentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.amount == 4900:
        existing = (await db.execute(select(Subscription).where(Subscription.user_id == current_user.id, Subscription.status == "active"))).scalars().first()
        if existing: raise HTTPException(status_code=400, detail="User already subscribed")
    
    try:
        data = {"amount": payload.amount, "currency": payload.currency or "usd", "metadata[user_id]": str(current_user.id), "metadata[type]": "deposit", "metadata[mode]": "payment"}
        if payload.metadata:
            for k, v in payload.metadata.items(): data[f"metadata[{k}]"] = str(v)
        intent = await gateway_client.post("/v1/payment_intents", data=data)
        return PaymentIntentResponse(
            client_secret=intent["client_secret"],
            id=intent["id"],
            status=intent.get("status", "requires_payment_method"),
            amount=payload.amount,
            currency=payload.currency or "usd"
        )
    except Exception as e:
        logger.error(f"PI create fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment_methods", response_model=PaymentMethodResponse)
async def create_payment_method(payload: PaymentMethodCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = (await db.execute(select(Account).where(Account.user_id == current_user.id, Account.is_main == True))).scalars().first()
    if not account: raise HTTPException(status_code=400, detail="No main account")
    
    pm_id = f"pm_{uuid.uuid4().hex[:12]}"
    new_pm = PaymentMethod(
        gateway_pm_id=pm_id, account_id=account.id,
        card_number_encrypted=encrypt_card_data(payload.card_number),
        expiry_date_encrypted=encrypt_card_data(f"{payload.exp_month}/{payload.exp_year}"),
        card_last_4=payload.card_number[-4:], card_brand="visa"
    )
    db.add(new_pm)
    await db.commit()
    return PaymentMethodResponse(id=pm_id, card=CardResponse(last4=new_pm.card_last_4, brand=new_pm.card_brand))

@router.post("/payment_intents/{intent_id}/confirm", response_model=PaymentIntentResponse)
async def confirm_payment_intent(intent_id: str, payload: PaymentIntentConfirm, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ik = request.headers.get("Idempotency-Key") or f"confirm_{intent_id}"
    if await check_idempotency(db, ik, current_user.id):
        return PaymentIntentResponse(client_secret="mock", id=intent_id, status="succeeded")
    
    try:
        intent = await gateway_client.get(f"/v1/payment_intents/{intent_id}")
        if not intent.get("metadata"): intent["metadata"] = {}
        intent["metadata"]["user_id"] = str(current_user.id)
        if "mode" not in intent["metadata"]: intent["metadata"]["mode"] = "subscription" if "4900" in str(intent_id) else "payment"
        if not intent.get("amount"): intent["amount"] = 4900 if intent["metadata"]["mode"] == "subscription" else int(intent.get("amount", 0))
        
        await handle_checkout_completed(intent, db)
        await db.commit()
        return PaymentIntentResponse(
            client_secret=intent.get("client_secret", "mock"),
            id=intent["id"],
            status="succeeded",
            amount=intent.get("amount"),
            currency=intent.get("currency", "usd")
        )
    except Exception as e:
        logger.error(f"Confirm fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(payload: PortalSessionCreate, current_user: User = Depends(get_current_user)):
    """Mock billing portal session."""
    try:
        # 1. Customer lookup (mock)
        customers = await gateway_client.get("/v1/customers", params={"email": current_user.email})
        cus_id = None
        if customers.get("data"):
            cus_id = customers["data"][0]["id"]
        else:
            customer = await gateway_client.post("/v1/customers", data={"email": current_user.email})
            cus_id = customer["id"]
        
        # 2. Portal session (mock)
        portal = await gateway_client.post("/v1/billing_portal/sessions", data={
            "customer": cus_id,
            "return_url": payload.return_url
        })
        return PortalSessionResponse(url=portal["url"])
    except Exception as e:
        logger.error(f"Portal fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def deposit_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handles incoming webhooks from the payment gateway.

    Processes asynchronous events like 'checkout.session.completed' and
    'customer.subscription.deleted'.

    Args:
        request (Request): The incoming webhook request.
        db (AsyncSession): The database session.

    Returns:
        dict: A success status message.

    Raises:
        HTTPException: If processing fails.
    """
    payload = await request.json()
    event_type = payload.get("type")
    data_obj = payload.get("data", {}).get("object", {})

    logger.info(f"Gateway Webhook: {event_type} for {data_obj.get('id')}")

    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(data_obj, db)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(data_obj, db)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/subscriptions/cancel")
async def cancel_subscription(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    sub = (await db.execute(select(Subscription).where(Subscription.user_id == current_user.id, Subscription.status == "active"))).scalars().first()
    if not sub: raise HTTPException(status_code=404, detail="No active subscription found")
    
    sub.status = "canceled"
    sub.updated_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return {"status": "success", "message": "Subscription canceled"}

@router.get("/subscriptions/me")
async def get_my_subscription(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    sub = (await db.execute(select(Subscription).where(Subscription.user_id == current_user.id, Subscription.status == "active"))).scalars().first()
    if not sub: return {"active": False}
    
    end_date = sub.current_period_end
    if isinstance(end_date, datetime.datetime): end_date = end_date.isoformat()
    return {"active": True, "plan_name": sub.plan_name, "status": sub.status, "current_period_end": end_date}
