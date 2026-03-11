import os
import uuid
import datetime
from decimal import Decimal
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import User, Account, Transaction, Outbox
from schemas.transfers import P2PTransferRequest
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def _validate_p2p_transfer(
    transfer: P2PTransferRequest,
    current_user: User,
    db: AsyncSession
) -> User:
    """Validates the transfer request and returns the recipient user."""
    # Recipient Lookup
    result = await db.execute(select(User).filter(User.email == transfer.recipient_email))
    recipient = result.scalars().first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    return recipient


async def _execute_p2p_balances(
    db: AsyncSession,
    sender_account_id: int,
    recipient_account_id: int,
    amount: Decimal
) -> Tuple[Account, Account]:
    """Locks accounts and updates balances atomically."""
    # Order by ID to prevent deadlocks.
    first_id, second_id = sorted([sender_account_id, recipient_account_id])

    result1 = await db.execute(select(Account).filter(Account.id == first_id).with_for_update())
    acc1 = result1.scalars().first()
    result2 = await db.execute(select(Account).filter(Account.id == second_id).with_for_update())
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
        status="cleared", # P2P transfers are instant in the internal ledger
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
        "amount": -float(amount),
        "category": "Transfer",
        "merchant": f"Transfer to {recipient_email}",
        "transaction_type": "transfer",
        "transaction_side": "DEBIT",
        "status": "cleared", # cleared in postgres already
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
        "amount": float(amount),
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



SIMULATOR_URL = os.getenv("SIMULATOR_URL")
SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY")

async def get_vendors():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{SIMULATOR_URL}/vendors")
            if resp.status_code == 200:
                return resp.json().get("vendors", [])
        except Exception as e:
            logger.error(f"Fetching vendors: {e}")
        return []


async def execute_vendor_payment_immediate(merchant_id: str, subscriber_id: str, amount: Decimal):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "merchant_id": merchant_id,
                "subscriber_id": subscriber_id,
                "amount": float(amount)
            }
            resp = await client.post(
                f"{SIMULATOR_URL}/billpay/execute",
                json=payload,
                headers={"X-API-KEY": SIMULATOR_API_KEY}
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Executing vendor payment: {e}")
            return {"status": "FAILED", "failure_reason": str(e)}


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

