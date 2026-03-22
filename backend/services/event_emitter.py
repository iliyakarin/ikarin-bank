"""Unified event emission service for financial transactions.

This module provides a single entry point for creating transaction records,
outbox entries for Kafka emission, and activity logs.
"""
import datetime
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from models.transaction import Transaction
from models.management import Outbox
from activity import emit_activity

async def emit_transactional_event(
    db: AsyncSession,
    user_id: int,
    account_id: int,
    amount: int,
    category: str,
    merchant: str,
    transaction_type: str,
    transaction_side: str,
    sender_email: str,
    recipient_email: str,
    internal_account_last_4: str,
    event_type: str,
    idempotency_key: str,
    commentary: Optional[str] = None,
    ip_address: str = "0.0.0.0",
    user_agent: str = "unknown",
    payload_extra: Optional[Dict[str, Any]] = None,
    payment_request_id: Optional[int] = None,
    status: str = "cleared",
    parent_id: Optional[str] = None,
    activity_category: str = "p2p",
    activity_action: Optional[str] = None
):
    """Unified function to create a Transaction, an Outbox entry, and an Activity log.

    Ensures all related systems (DB, Kafka, Activity Feed) are notified of a core
    financial event in an atomic-like fashion (within the same DB transaction).

    Args:
        db (AsyncSession): The database session.
        user_id (int): The ID of the owner user.
        account_id (int): The ID of the account involved.
        amount (int): The transaction amount in cents.
        category (str): The transaction category (e.g., 'P2P', 'Top-up').
        merchant (str): The merchant or counterparty name.
        transaction_type (str): The type (e.g., 'transfer', 'deposit').
        transaction_side (str): Either 'DEBIT' or 'CREDIT'.
        sender_email (str): Email of the sender.
        recipient_email (str): Email of the recipient.
        internal_account_last_4 (str): Last 4 digits of the internal account involved.
        event_type (str): The type used for Kafka outbox (e.g., 'transfer.success').
        idempotency_key (str): Key to prevent duplicate processing.
        commentary (str, optional): Optional notes for the transaction.
        ip_address (str): IP address of the requester.
        user_agent (str): User agent of the requester.
        payload_extra (dict, optional): Additional data to include in the Kafka payload.
        payment_request_id (int, optional): ID of the associated payment request.
        status (str): Status of the transaction (default 'cleared').
        parent_id (str, optional): Parent transaction ID for grouped transactions.
        activity_category (str): Category for the activity feed.
        activity_action (str, optional): Action for the activity feed (overrides default).

    Returns:
        str: The newly generated transaction ID (UUID).
    """
    tx_id = str(uuid.uuid4())
    final_parent_id = parent_id or tx_id
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 1. Transaction Record
    transaction = Transaction(
        id=tx_id,
        parent_id=final_parent_id,
        account_id=account_id,
        amount=amount,
        category=category,
        merchant=merchant,
        status=status,
        transaction_type=transaction_type,
        transaction_side=transaction_side,
        idempotency_key=idempotency_key,
        ip_address=ip_address,
        user_agent=user_agent,
        sender_email=sender_email,
        recipient_email=recipient_email,
        commentary=commentary,
        internal_account_last_4=internal_account_last_4,
        payment_request_id=payment_request_id
    )
    db.add(transaction)
    
    # 2. Outbox Entry (Kafka)
    outbox_payload = {
        "transaction_id": tx_id,
        "parent_id": final_parent_id,
        "account_id": account_id,
        "internal_account_last_4": internal_account_last_4,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": amount,
        "category": category,
        "merchant": merchant,
        "transaction_type": transaction_type,
        "transaction_side": transaction_side,
        "status": status,
        "timestamp": timestamp,
        "commentary": commentary,
        **(payload_extra or {})
    }
    db.add(Outbox(event_type=event_type, payload=outbox_payload))
    
    # 3. Activity Log (Feed)
    if not activity_action:
        activity_action = "sent" if transaction_side == "DEBIT" else "received"
        
    activity_title = f"{activity_action.title()} {category}" # Simple default
    if category == "Top-up":
        from money_utils import from_cents
        activity_title = f"Deposited ${from_cents(amount)} via Gateway"
        activity_action = "deposit_success"
    elif category == "P2P":
        from money_utils import from_cents
        amount_str = from_cents(abs(amount))
        if transaction_side == "DEBIT":
            activity_title = f"Sent {amount_str} to {recipient_email}"
        else:
            activity_title = f"Received {amount_str} from {sender_email}"
            
    emit_activity(
        db=db,
        user_id=user_id,
        category=activity_category,
        action=activity_action,
        title=activity_title,
        details={"transaction_id": tx_id, "parent_id": final_parent_id},
        ip=ip_address,
        user_agent=user_agent
    )
    
    return tx_id
