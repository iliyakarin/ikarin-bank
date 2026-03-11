from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
import os
import stripe

from auth_utils import get_db, get_current_user
from services.stripe_service import handle_topup

router = APIRouter(prefix="/stripe", tags=["Stripe"])

stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe.api_base = os.getenv("STRIPE_MOCK_URL", stripe.api_base)
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import os
import uuid
import datetime

from auth_utils import get_db, get_current_user
from database import Account, PaymentMethod, IdempotencyKey, Outbox, User
from account_service import encrypt_account_number

from schemas.stripe_mock import (
    PaymentIntentCreate, PaymentMethodCreate, PaymentIntentConfirm,
    PaymentMethodResponse, PaymentIntentResponse, StripeCard
)

router = APIRouter(prefix="/v1/stripe", tags=["Stripe Mock"])

@router.post("/payment_intents", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payload: PaymentIntentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    intent_id = f"pi_{uuid.uuid4().hex}"
    client_secret = f"{intent_id}_secret_{uuid.uuid4().hex}"
    
    return PaymentIntentResponse(
        id=intent_id,
        amount=payload.amount,
        currency=payload.currency,
        status="requires_payment_method",
        client_secret=client_secret
    )

@router.post("/payment_methods", response_model=PaymentMethodResponse)
async def create_payment_method(
    payload: PaymentMethodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find main account
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id, Account.is_main == True))
    main_account = result.scalars().first()
    if not main_account:
        raise HTTPException(status_code=400, detail="User has no main account")

    pm_id = f"pm_{uuid.uuid4().hex}"
    last4 = payload.card_number[-4:] if len(payload.card_number) >= 4 else "0000"
    brand = "Visa" if payload.card_number.startswith("4") else "MasterCard"
    
    # Store payment method encrypted
    pm = PaymentMethod(
        stripe_pm_id=pm_id,
        account_id=main_account.id,
        card_number_encrypted=encrypt_account_number(payload.card_number),
        expiry_date_encrypted=encrypt_account_number(f"{payload.exp_month}/{payload.exp_year}"),
        cvc_encrypted=encrypt_account_number(payload.cvc),
        cardholder_name_encrypted=encrypt_account_number(payload.name),
        card_last_4=last4,
        card_brand=brand
    )
    db.add(pm)
    await db.commit()
    await db.refresh(pm)

    return PaymentMethodResponse(
        id=pm_id,
        card=StripeCard(last4=last4, brand=brand)
    )

@router.post("/payment_intents/{intent_id}/confirm", response_model=PaymentIntentResponse)
async def confirm_payment_intent(
    intent_id: str,
    payload: PaymentIntentConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    idem_key = request.headers.get("Idempotency-Key")
    if idem_key:
        result = await db.execute(select(IdempotencyKey).filter(IdempotencyKey.key == idem_key))
        existing_key = result.scalars().first()
        if existing_key:
            return PaymentIntentResponse(**existing_key.response_body)

    # Note: A real API would look up the amount by intent_id. 
    # Since this is a mock, we'll extract or use a default amount.
    intent_amount = Decimal("1500")

    response_data = {
        "id": intent_id,
        "object": "payment_intent",
        "amount": int(intent_amount),
        "currency": "usd",
        "status": "succeeded",
        "client_secret": f"{intent_id}_secret"
    }

    # Record kafka event in outbox
    from activity import emit_transaction_status_update
    from activity import emit_activity
    # Or create our own payload format
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Needs transaction_id, stripe_intent_id, account_id, amount_cents, currency, timestamp
    tx_id = str(uuid.uuid4())
    
    # We must find the account ID for the user
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id, Account.is_main == True))
    main_account = result.scalars().first()
    
    mock_payload = {
        "transaction_id": tx_id,
        "stripe_intent_id": intent_id,
        "account_id": main_account.id if main_account else None,
        "amount_cents": float(intent_amount),
        "currency": "usd",
        "timestamp": now
    }

    outbox_entry = Outbox(
        event_type="transaction.stripe.success",
        payload=mock_payload,
    )
    db.add(outbox_entry)
    
    if main_account:
        main_account.balance += intent_amount / Decimal("100") # increase balance

    if idem_key:
        idem = IdempotencyKey(key=idem_key, user_id=current_user.id, response_code=200, response_body=response_data)
        db.add(idem)
        
    await db.commit()

    return PaymentIntentResponse(**response_data)
