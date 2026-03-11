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
    PaymentMethodResponse, PaymentIntentResponse, StripeCard,
    SubscriptionResponse
)
from database import Subscription

router = APIRouter(prefix="/v1/stripe", tags=["Stripe Mock"])

@router.post("/payment_intents", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payload: PaymentIntentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    intent_id = f"pi_{uuid.uuid4().hex}_{payload.amount}"
    client_secret = f"{intent_id}_secret_{uuid.uuid4().hex}"
    
    # If Karin Black upgrade ($49.00), check if already subscribed
    if payload.amount == 4900:
        sub_check = await db.execute(
            select(Subscription).filter(
                Subscription.user_id == current_user.id,
                Subscription.status == "active"
            )
        )
        if sub_check.scalars().first():
            raise HTTPException(status_code=400, detail="User already subscribed to Karin Black")

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
    # Since this is a mock, we extract the amount from our mock intent_id format: pi_{uuid}_{amount}
    try:
        parts = intent_id.split("_")
        intent_amount = Decimal(parts[-1])
    except Exception:
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
    is_subscription = (intent_amount == Decimal("4900"))
    
    # Needs transaction_id, stripe_intent_id, account_id, amount_cents, currency, timestamp
    tx_id = str(uuid.uuid4())
    
    # We must find the account ID for the user
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id, Account.is_main == True))
    main_account = result.scalars().first()
    
    actual_amount = intent_amount / Decimal("100")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    mock_payload = {
        "transaction_id": tx_id,
        "account_id": main_account.id if main_account else None,
        "amount": -float(actual_amount) if is_subscription else float(actual_amount),
        "category": "Subscription" if is_subscription else "Top-up",
        "merchant": "Karin Black" if is_subscription else "Stripe Checkout",
        "transaction_type": "expense" if is_subscription else "credit",
        "transaction_side": "DEBIT" if is_subscription else "CREDIT",
        "timestamp": now,
        "stripe_intent_id": intent_id,
        "status": "cleared"
    }

    outbox_entry = Outbox(
        event_type="transaction.stripe.success",
        payload=mock_payload,
    )
    db.add(outbox_entry)
    
    if is_subscription:
        # Deduct from balance
        if main_account:
            main_account.balance -= actual_amount
        
        # Create subscription record
        new_sub = Subscription(
            user_id=current_user.id,
            plan_name="Karin Black",
            amount=actual_amount,
            status="active",
            current_period_end=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        )
        db.add(new_sub)
        
        # Update user status
        current_user.is_black = True
        
        # Emit activity
        emit_activity(
            db=db,
            user_id=current_user.id,
            category="settings",
            action="subscription_started",
            title="Upgraded to Karin Black",
            details={"amount": 49.00}
        )
    else:
        # Standard top-up logic
        if main_account:
            main_account.balance += actual_amount
            
        emit_activity(
            db=db,
            user_id=current_user.id,
            category="p2p",
            action="deposit_success",
            title=f"Deposited ${float(actual_amount):.2f} via Stripe",
            details={"transaction_id": tx_id, "amount": float(actual_amount)}
        )

    if idem_key:
        idem = IdempotencyKey(key=idem_key, user_id=current_user.id, response_code=200, response_body=response_data)
        db.add(idem)
        
    await db.commit()

    return PaymentIntentResponse(**response_data)

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
        "amount": float(sub.amount),
        "current_period_end": sub.current_period_end.isoformat(),
        "status": sub.status
    }

@router.post("/subscriptions/cancel")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        )
    )
    subs = result.scalars().all()
    if not subs:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    for sub in subs:
        sub.status = "cancelled"
    
    current_user.is_black = False
    
    emit_activity(
        db=db,
        user_id=current_user.id,
        category="settings",
        action="subscription_cancelled",
        title="Cancelled Karin Black Subscription"
    )
    
    await db.commit()
    return {"message": "Subscription cancelled successfully"}
