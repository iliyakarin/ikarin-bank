import logging
import datetime
import uuid
import httpx
from decimal import Decimal
from typing import List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from config import settings
from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import PaymentRequest
from models.management import ScheduledPayment
from activity import emit_activity
from money_utils import from_cents

from date_utils import calculate_next_run_at
from idempotency import check_idempotency
from services.event_emitter import emit_transactional_event

from services.mock_client import MockServiceClient

logger = logging.getLogger(__name__)

# Initialize Mock Clients
simulator_client = MockServiceClient(
    base_url=settings.SIMULATOR_URL, 
    api_key=getattr(settings, "SIMULATOR_API_KEY", "default-key")
)

async def _get_account_by_user(
    db: AsyncSession, 
    user_id: int, 
    account_id: Optional[int] = None, 
    lock: bool = False
) -> Account:
    """Consolidated helper to fetch a user's account with optional lock."""
    stmt = select(Account).where(Account.user_id == user_id)
    
    if account_id:
        stmt = stmt.where(Account.id == account_id)
    else:
        stmt = stmt.where(Account.is_main == True)
        
    if lock:
        stmt = stmt.with_for_update()
        
    account = (await db.execute(stmt)).scalars().first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Account not found"
        )
    return account

async def execute_vendor_payment_immediate(vendor_id: str, subscriber_id: str, amount: int):
    """Calls the vendor simulator to process a payment."""
    try:
        return await simulator_client.post(
            "/billpay/execute",
            data={
                "merchant_id": vendor_id,
                "subscriber_id": subscriber_id,
                "amount": float(amount) / 100.0
            }
        )
    except HTTPException as e:
        return {"status": "FAILED", "failure_reason": f"Simulator error: {e.detail}"}
    except Exception as e:
        logger.error(f"Error calling vendor simulator: {e}")
        return {"status": "FAILED", "failure_reason": str(e)}

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
    user_agent: Optional[str] = None,
    subscriber_id: Optional[str] = None
):
    """Orchestrates the entire P2P transfer process."""
    if recipient_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot transfer to yourself")

    # 1. Identify Recipient
    recipient = await _find_user_by_email(db, recipient_email)
    if not recipient:
        vendor = await _find_vendor_by_email(recipient_email)
        if vendor:
            return await _handle_vendor_payment(
                db, current_user, vendor, amount, source_account_id, commentary, 
                idempotency_key, client_ip or "0.0.0.0", user_agent or "unknown", subscriber_id
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    # 2. Validation
    payment_request = None
    if payment_request_id:
        payment_request = await _validate_payment_request(db, payment_request_id, current_user, amount)

    # 3. Fetch Accounts
    sender_account = await _get_account_by_user(db, current_user.id, source_account_id)
    recipient_account = await _get_account_by_user(db, recipient.id)

    # 4. Execute Core Balance Update
    sender_account, recipient_account = await _execute_p2p_balances(db, sender_account.id, recipient_account.id, amount)

    # 5. Emit Events
    parent_id = str(uuid.uuid4())
    
    # Sender side
    await emit_transactional_event(
        db=db, user_id=current_user.id, account_id=sender_account.id, amount=-amount,
        category="p2p", merchant=f"To {recipient.email}", transaction_type="transfer",
        transaction_side="DEBIT", sender_email=current_user.email, recipient_email=recipient.email,
        internal_account_last_4=sender_account.account_number_last_4, event_type="p2p.sender",
        idempotency_key=idempotency_key, commentary=commentary, ip_address=client_ip or "0.0.0.0",
        user_agent=user_agent or "unknown", payment_request_id=payment_request_id, parent_id=parent_id
    )

    # Recipient side
    await emit_transactional_event(
        db=db, user_id=recipient.id, account_id=recipient_account.id, amount=amount,
        category="p2p", merchant=f"From {current_user.email}", transaction_type="transfer",
        transaction_side="CREDIT", sender_email=current_user.email, recipient_email=recipient.email,
        internal_account_last_4=recipient_account.account_number_last_4, event_type="p2p.recipient",
        idempotency_key=idempotency_key, commentary=commentary, ip_address=client_ip or "0.0.0.0",
        user_agent=user_agent or "unknown", payment_request_id=payment_request_id, parent_id=parent_id
    )

    if payment_request:
        payment_request.status = "paid"
        payment_request.updated_at = datetime.datetime.now(datetime.timezone.utc)

    return {"status": "success", "transaction_id": parent_id}

async def _find_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    return (await db.execute(select(User).where(User.email == email))).scalars().first()

async def _find_vendor_by_email(email: str) -> Optional[dict]:
    vendors = await get_vendors()
    return next((v for v in vendors if v["email"] == email), None)

async def _validate_payment_request(db: AsyncSession, pr_id: int, user: User, amount: int) -> PaymentRequest:
    request = (await db.execute(select(PaymentRequest).where(PaymentRequest.id == pr_id))).scalars().first()
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment request not found")
    if request.target_email != user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if request.status not in ["pending_target", "pending_requester"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request inactive")
    if amount < request.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient amount")
    return request

async def _handle_vendor_payment(
    db: AsyncSession, current_user: User, vendor: dict, amount: int,
    source_account_id: Optional[int], commentary: Optional[str],
    idempotency_key: Optional[str], client_ip: str, user_agent: str,
    subscriber_id: Optional[str]
):
    if not subscriber_id: 
        raise HTTPException(status_code=400, detail="Subscriber ID required")

    sender_account = await _get_account_by_user(db, current_user.id, source_account_id, lock=True)
    
    if sender_account.balance < amount: 
        raise HTTPException(status_code=400, detail="Insufficient funds")

    sim_resp = await execute_vendor_payment_immediate(vendor["id"], subscriber_id, amount)
    sender_account.balance -= amount

    tx_id = await emit_transactional_event(
        db=db, user_id=current_user.id, account_id=sender_account.id, amount=-amount,
        category="Bill Pay", merchant=vendor["name"],
        status="cleared" if sim_resp.get("status") == "CLEARED" else "failed",
        transaction_type="expense", transaction_side="DEBIT", 
        failure_reason=sim_resp.get("failure_reason"),
        commentary=commentary or f"Bill Pay to {vendor['name']}",
        recipient_email=vendor["email"], sender_email=current_user.email,
        subscriber_id=subscriber_id, idempotency_key=idempotency_key or str(uuid.uuid4()),
        ip_address=client_ip, user_agent=user_agent, event_type="vendor.payment",
        internal_account_last_4=sender_account.account_number_last_4
    )
    await db.commit()
    return {"status": "success", "transaction_id": tx_id, "vendor_status": sim_resp.get("status")}

async def get_vendors():
    """Fetches vendors from the simulator."""
    try:
        res = await simulator_client.get("/vendors")
        return res.get("vendors", [])
    except Exception:
        return []

async def _execute_p2p_balances(db: AsyncSession, sender_id: int, recipient_id: int, amount: int) -> Tuple[Account, Account]:
    """Atomically update balances for both accounts."""
    ids = sorted([sender_id, recipient_id])
    accounts_stmt = select(Account).where(Account.id.in_(ids)).with_for_update()
    accounts = (await db.execute(accounts_stmt)).scalars().all()
    
    acc_map = {acc.id: acc for acc in accounts}
    sender = acc_map.get(sender_id)
    recipient = acc_map.get(recipient_id)
    
    if not sender or not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        
    if sender.balance < amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")
        
    sender.balance -= amount
    recipient.balance += amount
    return sender, recipient

# Transaction and Outbox helpers removed in favor of event_emitter.py
