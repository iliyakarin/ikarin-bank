import datetime
import uuid
import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from database import Account, Transaction, Outbox, User, IdempotencyKey, Subscription
from activity import emit_activity
from money_utils import from_cents

logger = logging.getLogger(__name__)

async def _atomic_topup_balance(
    db: AsyncSession,
    user_id: int,
    amount_cents: int,
    idempotency_key: str,
    gateway_session_id: str
):
    # 1. Get User & Primary Account
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        logger.error(f"User not found for topup ID: {user_id}")
        return

    # 2. Idempotency Check
    result = await db.execute(
        select(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).with_for_update()
    )
    existing_key = result.scalars().first()
    if existing_key:
        logger.info(f"TopUp inherently skipped -> idempotency key found: {idempotency_key}")
        return

    db.add(IdempotencyKey(key=idempotency_key, user_id=user.id))

    result = await db.execute(
        select(Account).filter(Account.user_id == user.id, Account.is_main == True).with_for_update()
    )
    account = result.scalars().first()
    if not account:
        logger.error(f"Main account not found for user ID: {user_id}")
        return

    # 3. Update Balance
    account.balance += amount_cents

    # 4. Create Transaction
    tx_id = str(uuid.uuid4())
    tx = Transaction(
        id=tx_id,
        parent_id=tx_id,
        account_id=account.id,
        amount=amount_cents,
        category="Top-up",
        merchant="Simulated Gateway",
        status="cleared",
        transaction_type="deposit",
        transaction_side="CREDIT",
        idempotency_key=idempotency_key,
        ip_address="gateway_webhook",
        user_agent="gateway",
        sender_email="gateway@karinbank.com",
        recipient_email=user.email,
        commentary=f"Gateway Session: {gateway_session_id}",
        internal_account_last_4=account.account_number_last_4
    )
    db.add(tx)

    # 5. Create Outbox Event
    outbox_payload = {
        "transaction_id": tx_id,
        "parent_id": tx_id,
        "account_id": account.id,
        "internal_account_last_4": account.account_number_last_4,
        "sender_email": "gateway@karinbank.com",
        "recipient_email": user.email,
        "amount": amount_cents,
        "category": "Top-up",
        "merchant": "Simulated Gateway",
        "transaction_type": "deposit",
        "transaction_side": "CREDIT",
        "status": "cleared",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "commentary": f"Gateway Session: {gateway_session_id}"
    }
    db.add(Outbox(event_type="deposit.success", payload=outbox_payload))
    
    # 6. Emit Activity
    emit_activity(
        db=db,
        user_id=user.id,
        category="p2p",
        action="deposit_success",
        title=f"Deposited ${from_cents(amount_cents)} via Gateway",
        details={"transaction_id": tx_id, "amount": amount_cents}
    )

    await db.commit()


async def handle_checkout_completed(session: dict, db: AsyncSession):
    """
    Handles a successful checkout session completion or PaymentIntent success.
    Supports both one-time payments and subscriptions.
    """
    session_id = session.get("id")
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    mode = metadata.get("mode", "payment")
    
    if not user_id:
        logger.error(f"No user ID in metadata for session/intent {session_id}")
        return

    try:
        user_id = int(user_id)
    except ValueError:
        logger.error(f"Invalid user ID in metadata: {user_id}")
        return

    # For PaymentIntent, amount is 'amount', for Checkout Session it's 'amount_total'
    amount_total = session.get("amount_total") or session.get("amount")
    
    if mode == "payment":
        amount_cents = int(amount_total)
        idempotency_key = f"stripe_deposit_{session_id}"
 
        try:
            await _atomic_topup_balance(
                db=db,
                user_id=user_id,
                amount_cents=amount_cents,
                idempotency_key=idempotency_key,
                gateway_session_id=session_id
            )
            logger.info(f"Deposit successful for user {user_id}: {amount_cents}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Deposit failed for user {user_id}: {e}")

    elif mode == "subscription":
        # Handle subscription creation
        stripe_sub_id = session.get("subscription")
        idempotency_key = f"stripe_sub_{stripe_sub_id}"
        
        # Check idempotency
        res = await db.execute(select(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key))
        if res.scalars().first():
            logger.info(f"Subscription fulfillment skipped (idempotent): {idempotency_key}")
            return

        db.add(IdempotencyKey(key=idempotency_key, user_id=user_id))
        
        # Update User
        res = await db.execute(select(User).filter(User.id == user_id))
        user = res.scalars().first()
        if user:
            user.is_black = True
            
            # Create Subscription record
            new_sub = Subscription(
                user_id=user_id,
                plan_name="Karin Black",
                amount=4900,
                status="active",
                current_period_end=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
            )
            db.add(new_sub)
            
            emit_activity(
                db=db,
                user_id=user_id,
                category="settings",
                action="subscription_started",
                title="Upgraded to Karin Black",
                details={"stripe_subscription_id": stripe_sub_id}
            )
            await db.commit()
            logger.info(f"Subscription activated for user {user_id}")

async def handle_subscription_deleted(stripe_subscription: dict, db: AsyncSession):
    """
    Handles subscription cancellation from Stripe.
    """
    stripe_sub_id = stripe_subscription.get("id")
    # Finding user by searching for active subscription with this ID would be ideal
    # For now, we'll search by user_id if present in metadata or just find the user's active sub
    customer_id = stripe_subscription.get("customer")
    
    # Normally we'd look up user by stripe_customer_id
    # But for simplicity in this mock-to-real transition, let's find the user's most recent active sub
    # In production, you MUST store stripe_customer_id and stripe_subscription_id.
    
    # For this exercise, we'll try to find the User via metadata if available
    metadata = stripe_subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    
    if user_id:
        res = await db.execute(select(User).filter(User.id == int(user_id)))
        user = res.scalars().first()
        if user:
            user.is_black = False
            
            # Deactivate all active subs for this user
            res = await db.execute(
                select(Subscription).filter(
                    Subscription.user_id == user.id,
                    Subscription.status == "active"
                )
            )
            active_subs = res.scalars().all()
            for sub in active_subs:
                sub.status = "cancelled"
            
            emit_activity(
                db=db,
                user_id=user.id,
                category="settings",
                action="subscription_cancelled",
                title="Karin Black Subscription Ended",
                details={"stripe_subscription_id": stripe_sub_id}
            )
            await db.commit()
            logger.info(f"Subscription deactivated for user {user.id}")
