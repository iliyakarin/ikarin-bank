"""Service for handling fund deposits and subscriptions.

This module processes webhooks from payment gateways, manages balance
top-ups, and handles subscription lifecycle events.
"""
import datetime
import uuid
import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from database import SessionLocal
from models.user import User, Subscription
from models.account import Account, PaymentMethod
from activity import emit_activity
from money_utils import from_cents

from idempotency import check_idempotency
from services.event_emitter import emit_transactional_event

logger = logging.getLogger(__name__)

async def _atomic_topup_balance(
    db: AsyncSession, user_id: int, amount_cents: int, idempotency_key: str, gateway_session_id: str
):
    """Atomically credits user balance and records a transaction.

    This function performs an idempotency check, locks the user's main account,
    updates the balance, and emits a transactional event for record-keeping.

    Args:
        db (AsyncSession): The database session.
        user_id (int): The ID of the user to credit.
        amount_cents (int): The amount to credit in cents.
        idempotency_key (str): Unique key to prevent duplicate processing.
        gateway_session_id (str): The ID of the session from the payment gateway.
    """
    # 1. User & Account Lookup with Lock
    user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if not user:
        logger.error(f"User not found for topup ID: {user_id}")
        return

    # 2. Idempotency Check
    if await check_idempotency(db, idempotency_key, user.id):
        return

    account = (await db.execute(select(Account).where(Account.user_id == user.id, Account.is_main == True).with_for_update())).scalars().first()
    if not account:
        logger.error(f"Main account not found for user ID: {user_id}")
        return

    # 3. Update Balance
    account.balance += amount_cents

    # 4. Use unified event emitter for Top-up
    await emit_transactional_event(
        db=db, user_id=user.id, account_id=account.id, amount=amount_cents,
        category="Top-up", merchant="Simulated Gateway", transaction_type="deposit",
        transaction_side="CREDIT", sender_email="gateway@karinbank.com",
        recipient_email=user.email, internal_account_last_4=account.account_number_last_4,
        event_type="deposit.success", idempotency_key=idempotency_key,
        commentary=f"Gateway Session: {gateway_session_id}",
        ip_address="gateway_webhook", user_agent="gateway"
    )

    await db.commit()

async def handle_checkout_completed(session: dict, db: AsyncSession):
    """Processes a completed checkout session from the payment gateway.

    Handles both direct one-time deposits (payments) and subscription starts.
    Uses metadata in the session to identify the user and operation mode.

    Args:
        session (dict): The checkout session data from the gateway.
        db (AsyncSession): The database session.
    """
    s_id = session.get("id")
    meta = session.get("metadata", {})
    u_id_str = meta.get("user_id")
    mode = meta.get("mode", "payment")

    if not u_id_str:
        logger.error(f"Missing user_id in metadata for session {s_id}")
        return

    try:
        u_id = int(u_id_str)
    except ValueError:
        logger.error(f"Invalid user_id {u_id_str}")
        return

    total = session.get("amount_total") or session.get("amount")
    if mode == "payment":
        try:
            await _atomic_topup_balance(db, u_id, int(total), f"deposit_mock_{s_id}", s_id)
            logger.info(f"Deposit success for user {u_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Deposit fail for user {u_id}: {e}")
    elif mode == "subscription":
        ik = f"deposit_sub_{session.get('subscription')}"
        if await check_idempotency(db, ik, u_id):
            return
        user = (await db.execute(select(User).where(User.id == u_id))).scalars().first()
        if user:
            user.is_black = True
            # Deduct subscription fee from main account
            account = (await db.execute(select(Account).where(Account.user_id == user.id, Account.is_main == True).with_for_update())).scalars().first()
            if account:
                account.balance -= 4900
            
            db.add(Subscription(
                user_id=u_id, plan_name="Karin Black", amount=4900, status="active",
                current_period_end=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
            ))
            emit_activity(
                db, u_id, "settings", "subscription_started", "Upgraded to Karin Black",
                {"deposit_subscription_id": session.get("subscription")}
            )
            await db.commit()

async def handle_subscription_deleted(deposit_subscription: dict, db: AsyncSession):
    """Handles deletion/cancellation of a subscription.

    Resets the user's premium status and marks all active subscriptions as cancelled
    in the database.

    Args:
        deposit_subscription (dict): The subscription data from the gateway.
        db (AsyncSession): The database session.
    """
    sub_id = deposit_subscription.get("id")
    meta = deposit_subscription.get("metadata", {})
    u_id_str = meta.get("user_id")

    if u_id_str:
        user = (await db.execute(select(User).where(User.id == int(u_id_str)))).scalars().first()
        if user:
            user.is_black = False
            subs = (await db.execute(select(Subscription).where(Subscription.user_id == user.id, Subscription.status == "active"))).scalars().all()
            for s in subs:
                s.status = "cancelled"
            emit_activity(
                db, user.id, "settings", "subscription_cancelled", "Karin Black Subscription Ended",
                {"deposit_subscription_id": sub_id}
            )
            await db.commit()
