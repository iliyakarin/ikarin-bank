import logging
import datetime
import uuid
import httpx
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from config import settings
from database import User, Account, Transaction, Outbox, IdempotencyKey, ScheduledPayment, PaymentRequest
from activity import emit_activity
from money_utils import from_cents

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SIMULATOR_URL = settings.SIMULATOR_URL
SIMULATOR_API_KEY = settings.SIMULATOR_API_KEY


async def process_p2p_transfer(
    db: AsyncSession,
    current_user: User,
    recipient_email: str,
    amount: int,
    source_account_id: Optional[int] = None,
    commentary: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    payment_request_id: Optional[int] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Orchestrates the entire P2P transfer process including validation, 
    balance updates, transaction recording, and outbox emission.
    """
    
    # 1. Recipient Lookup
    result = await db.execute(select(User).filter(User.email == recipient_email))
    recipient = result.scalars().first()
    
    if not recipient:
        # Check if it's a vendor
        vendors_resp = await get_vendors()
        vendor = next((v for v in vendors_resp if v["email"] == recipient_email), None)
        if vendor:
            return await _handle_vendor_payment(
                db, current_user, vendor, amount, source_account_id, commentary, idempotency_key, client_ip, user_agent
            )
        raise HTTPException(status_code=404, detail="Recipient not found")

    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    # 2. Payment Request Validation
    payment_request = None
    if payment_request_id:
        result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == payment_request_id))
        payment_request = result.scalars().first()
        if not payment_request:
            raise HTTPException(status_code=404, detail="Payment request not found")
        if payment_request.target_email != current_user.email:
            raise HTTPException(status_code=403, detail="Not authorized for this payment request")
        if payment_request.status not in ["pending_target", "pending_requester"]:
            raise HTTPException(status_code=400, detail="Payment request is inactive")
        if amount < payment_request.amount:
            raise HTTPException(status_code=400, detail=f"Amount must be at least {from_cents(payment_request.amount)}")

    # 3. Resolve Accounts
    sender_account_query = select(Account).filter(Account.user_id == current_user.id)
    if source_account_id:
        sender_account_query = sender_account_query.filter(Account.id == source_account_id)
    else:
        sender_account_query = sender_account_query.filter(Account.is_main == True)
    
    result = await db.execute(sender_account_query)
    resolved_sender_account = result.scalars().first()
    if not resolved_sender_account:
        raise HTTPException(status_code=404, detail="Source account not found")

    result = await db.execute(select(Account).filter(Account.user_id == recipient.id, Account.is_main == True))
    resolved_recipient_account = result.scalars().first()
    if not resolved_recipient_account:
        raise HTTPException(status_code=404, detail="Recipient main account not found")

    # 4. Atomic Balance Update
    sender_account, recipient_account = await _execute_p2p_balances(
        db, resolved_sender_account.id, resolved_recipient_account.id, amount
    )

    # 5. Transaction Recording
    tx_id_parent, tx_id_sender, tx_id_recipient = _create_p2p_transactions(
        db, sender_account.id, recipient_account.id, amount, recipient.email, current_user.email,
        idempotency_key, client_ip or "0.0.0.0", user_agent or "unknown",
        sender_account.account_number_last_4, recipient_account.account_number_last_4,
        commentary, payment_request_id
    )

    # 6. Outbox Emission
    _create_p2p_outbox_entries(
        db, sender_account, recipient_account, amount, current_user.email, recipient.email,
        tx_id_parent, tx_id_sender, tx_id_recipient, commentary
    )

    # 7. Finalize State
    if payment_request:
        payment_request.status = "paid"
        payment_request.updated_at = datetime.datetime.now(datetime.timezone.utc)

    # Emit Activities
    emit_activity(
        db, current_user.id, "p2p", "sent", f"Sent {from_cents(amount)} to {recipient.email}",
        {"transaction_id": tx_id_parent, "recipient_email": recipient.email, "amount": amount},
        ip=client_ip, user_agent=user_agent
    )
    emit_activity(
        db, recipient.id, "p2p", "received", f"Received {from_cents(amount)} from {current_user.email}",
        {"transaction_id": tx_id_parent, "sender_email": current_user.email, "amount": amount},
        ip=client_ip, user_agent=user_agent
    )

    await db.commit()
    return {"status": "success", "transaction_id": tx_id_parent}

async def _handle_vendor_payment(
    db: AsyncSession, current_user: User, vendor: dict, amount: int, 
    source_account_id: Optional[int], commentary: Optional[str],
    idempotency_key: Optional[str], client_ip: str, user_agent: str
):
    sender_account_query = select(Account).filter(Account.user_id == current_user.id)
    if source_account_id:
        sender_account_query = sender_account_query.filter(Account.id == source_account_id)
    else:
        sender_account_query = sender_account_query.filter(Account.is_main == True)
        
    result = await db.execute(sender_account_query.with_for_update())
    sender_account = result.scalars().first()
    if not sender_account:
        raise HTTPException(status_code=404, detail="Source account not found")

    if sender_account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # Execute Vendor Payment
    sim_resp = await execute_vendor_payment_immediate(vendor["id"], "EXTERNAL", amount)

    # Update Balance
    sender_account.balance -= amount

    # Create Transaction Record
    status_map = {"CLEARED": "cleared", "FAILED": "failed"}
    tx_id = str(uuid.uuid4())
    vendor_tx = Transaction(
        id=tx_id,
        account_id=sender_account.id,
        amount=-amount,
        category="Bill Pay",
        merchant=vendor["name"],
        status=status_map.get(sim_resp.get("status"), "failed"),
        transaction_type="expense",
        transaction_side="DEBIT",
        failure_reason=sim_resp.get("failure_reason"),
        commentary=commentary or f"Bill Payment to {vendor['name']}",
        internal_account_last_4=sender_account.account_number_last_4,
        recipient_email=vendor["email"],
        sender_email=current_user.email,
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(vendor_tx)
    await db.commit()
    return {"status": "success", "transaction_id": tx_id, "vendor_status": sim_resp.get("status")}

async def get_vendors():
    """Proxy to get vendors from vendor-simulator."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("http://vendor-simulator:8001/vendors", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                return data.get("vendors", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching vendors: {e}")
            return []


def _calculate_next_run_at(reference_date: datetime.datetime, frequency: str, interval: str = None) -> Optional[datetime.datetime]:
    """Calculates the next execution date based on frequency and reference date."""
    if frequency == "One-time":
        return None
    
    if frequency == "Daily":
        return reference_date + datetime.timedelta(days=1)
    
    if frequency == "Weekly":
        return reference_date + datetime.timedelta(weeks=1)
    
    if frequency == "Bi-weekly":
        return reference_date + datetime.timedelta(weeks=2)
    
    if frequency == "Monthly":
        # Advance by exactly one month
        month = reference_date.month
        year = reference_date.year + (month // 12)
        month = (month % 12) + 1
        
        # Max days in the new month
        if month == 2:
            max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
        else:
            max_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
            
        day = min(reference_date.day, max_day)
        return reference_date.replace(year=year, month=month, day=day)

    if frequency == "Annually":
        try:
            return reference_date.replace(year=reference_date.year + 1)
        except ValueError: # Handle Feb 29
            return reference_date.replace(year=reference_date.year + 1, day=28)

    if frequency == "Specific Day of Week":
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if not interval or interval not in days_of_week:
            return reference_date + datetime.timedelta(weeks=1)
        
        target_weekday = days_of_week.index(interval)
        current_weekday = reference_date.weekday()
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
        return reference_date + datetime.timedelta(days=days_ahead)

    if frequency == "Specific Date of Month":
        try:
            target_day = int(interval)
        except (TypeError, ValueError):
            return reference_date + datetime.timedelta(days=30)
            
        # Move to next month and try to set the requested day
        month = reference_date.month
        year = reference_date.year + (month // 12)
        month = (month % 12) + 1
        
        if month == 2:
            max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
        else:
            max_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
            
        actual_day = min(target_day, max_day)
        return reference_date.replace(year=year, month=month, day=actual_day)

    return None


async def _execute_p2p_balances(
    db: AsyncSession,
    sender_account_id: int,
    recipient_account_id: int,
    amount: Decimal
) -> Tuple[Account, Account]:
    """Locks accounts and updates balances atomically."""
    # Order by ID to prevent deadlocks.
    first_id, second_id = sorted([sender_account_id, recipient_account_id])

    result1 = await db.execute(
        select(Account)
        .filter(Account.id == first_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    acc1 = result1.scalars().first()
    result2 = await db.execute(
        select(Account)
        .filter(Account.id == second_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    acc2 = result2.scalars().first()

    if first_id == sender_account_id:
        sender_account = acc1
        recipient_account = acc2
    else:
        sender_account = acc2
        recipient_account = acc1

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found")
        
    if sender_account.balance < amount:
        raise HTTPException(
            status_code=400, detail="Insufficient funds for this transfer."
        )

    if not recipient_account:
        raise HTTPException(status_code=404, detail="Recipient account not found")

    sender_account.balance -= amount
    recipient_account.balance += amount

    return sender_account, recipient_account

def _create_p2p_transactions(
    db: Session,
    sender_account_id: int,
    recipient_account_id: int,
    amount: Decimal,
    recipient_email: str,
    sender_email: str,
    idempotency_key: Optional[str],
    client_ip: str,
    user_agent: str,
    sender_account_last_4: str | None = None,
    recipient_account_last_4: str | None = None,
    commentary: Optional[str] = None,
    payment_request_id: Optional[int] = None
) -> Tuple[str, str, str]:
    """Creates transaction records for sender and recipient."""
    tx_id_parent = str(uuid.uuid4())
    tx_id_sender = str(uuid.uuid4())
    tx_id_recipient = str(uuid.uuid4())

    sender_tx = Transaction(
        id=tx_id_sender,
        parent_id=tx_id_parent,
        account_id=sender_account_id,
        amount=-amount,
        category="Transfer",
        merchant=f"Transfer to {recipient_email}",
        status="cleared", 
        transaction_type="transfer",
        transaction_side="DEBIT",
        idempotency_key=idempotency_key,
        ip_address=client_ip,
        user_agent=user_agent,
        commentary=commentary,
        payment_request_id=payment_request_id,
        internal_account_last_4=sender_account_last_4,
        sender_email=sender_email,
        recipient_email=recipient_email
    )

    recipient_tx = Transaction(
        id=tx_id_recipient,
        parent_id=tx_id_parent,
        account_id=recipient_account_id,
        amount=amount,
        category="Transfer",
        merchant=f"Received from {sender_email}",
        status="cleared",
        transaction_type="transfer",
        transaction_side="CREDIT",
        idempotency_key=idempotency_key,
        ip_address=client_ip,
        user_agent=user_agent,
        commentary=commentary,
        payment_request_id=payment_request_id,
        internal_account_last_4=recipient_account_last_4,
        sender_email=sender_email,
        recipient_email=recipient_email
    )

    db.add(sender_tx)
    db.add(recipient_tx)

    return tx_id_parent, tx_id_sender, tx_id_recipient

def _create_p2p_outbox_entries(
    db: Session,
    sender_account: Account,
    recipient_account: Account,
    amount: Decimal,
    sender_email: str,
    recipient_email: str,
    tx_id_parent: str,
    tx_id_sender: str,
    tx_id_recipient: str,
    commentary: Optional[str] = None
):
    """Creates outbox entries for Kafka processing."""
    sender_payload = {
        "transaction_id": tx_id_sender,
        "parent_id": tx_id_parent,
        "account_id": sender_account.id,
        "internal_account_last_4": sender_account.account_number_last_4,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": -int(amount),
        "category": "Transfer",
        "merchant": f"Transfer to {recipient_email}",
        "transaction_type": "transfer",
        "transaction_side": "DEBIT",
        "status": "cleared",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "commentary": commentary
    }

    recipient_payload = {
        "transaction_id": tx_id_recipient,
        "parent_id": tx_id_parent,
        "account_id": recipient_account.id,
        "internal_account_last_4": recipient_account.account_number_last_4,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": int(amount),
        "category": "Transfer",
        "merchant": f"Received from {sender_email}",
        "transaction_type": "transfer",
        "transaction_side": "CREDIT",
        "status": "cleared",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "commentary": commentary
    }

    db.add(Outbox(event_type="p2p.sender", payload=sender_payload))
    db.add(Outbox(event_type="p2p.recipient", payload=recipient_payload))
