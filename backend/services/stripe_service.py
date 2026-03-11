import datetime
import uuid
import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from database import Account, Transaction, Outbox, User, IdempotencyKey

logger = logging.getLogger(__name__)

async def _atomic_topup_balance(
    db: AsyncSession,
    user_email: str,
    amount: Decimal,
    idempotency_key: str,
    stripe_session_id: str
):
    # 1. Get User & Primary Account
    result = await db.execute(select(User).filter(User.email == user_email))
    user = result.scalars().first()
    if not user:
        logger.error(f"User not found for topup: {user_email}")
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
        logger.error(f"Main account not found for user: {user_email}")
        return

    # 3. Update Balance
    account.balance += amount

    # 4. Create Transaction
    tx_id = str(uuid.uuid4())
    tx = Transaction(
        id=tx_id,
        parent_id=tx_id,
        account_id=account.id,
        amount=amount,
        category="Deposit",
        merchant="Stripe Top-Up",
        status="cleared",
        transaction_type="deposit",
        transaction_side="CREDIT",
        idempotency_key=idempotency_key,
        ip_address="stripe_webhook",
        user_agent="stripe",
        sender_email="stripe@karinbank.com",
        recipient_email=user_email,
        commentary=f"Stripe Session: {stripe_session_id}",
        internal_account_last_4=account.account_number_last_4
    )
    db.add(tx)

    # 5. Create Outbox Event
    outbox_payload = {
        "transaction_id": tx_id,
        "parent_id": tx_id,
        "account_id": account.id,
        "internal_account_last_4": account.account_number_last_4,
        "sender_email": "stripe@karinbank.com",
        "recipient_email": user_email,
        "amount": float(amount),
        "category": "Deposit",
        "merchant": "Stripe Top-Up",
        "transaction_type": "deposit",
        "transaction_side": "CREDIT",
        "status": "cleared",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "commentary": f"Stripe Session: {stripe_session_id}"
    }
    db.add(Outbox(event_type="stripe.deposit", payload=outbox_payload))
    
    await db.commit()


async def handle_topup(session_event: dict, db: AsyncSession):
    """
    Handles a successful top-up from Stripe checkout session.
    Expects amount to be in cents, converts to Decimal dollars.
    """
    session_id = session_event.get("id")
    metadata = session_event.get("metadata", {})
    user_email = metadata.get("user_id")  # stored as 'sub' in standard jwt which is email
    
    if not user_email:
        logger.error(f"No user ID in metadata for session {session_id}")
        return

    amount_total = session_event.get("amount_total")
    if not amount_total:
         logger.error("No amount found in session")
         return

    amount_dollars = Decimal(str(amount_total)) / Decimal("100")
    
    idempotency_key = f"stripe_topup_{session_id}"

    try:
        await _atomic_topup_balance(
            db=db,
            user_email=user_email,
            amount=amount_dollars,
            idempotency_key=idempotency_key,
            stripe_session_id=session_id
        )
        logger.info(f"Top-up successful for {user_email}: {amount_dollars}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Top-up failed for {user_email}: {e}")
