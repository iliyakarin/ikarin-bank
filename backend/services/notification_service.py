from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from models.transaction import Transaction, PaymentRequest
from models.account import Account
from money_utils import from_cents

async def get_user_notifications(db: AsyncSession, user_id: int, user_email: str) -> List[Dict[str, Any]]:
    """Fetches and formats notifications for a user."""
    notifications = []

    # 1. Transactions
    acc_query = select(Account.id).where(Account.user_id == user_id)
    account_ids = (await db.execute(acc_query)).scalars().all()
    
    if account_ids:
        tx_query = select(Transaction).where(
            and_(
                Transaction.account_id.in_(account_ids),
                Transaction.status != "cancelled"
            )
        ).order_by(Transaction.created_at.desc()).limit(10)
        transactions = (await db.execute(tx_query)).scalars().all()

        for tx in transactions:
            notifications.append(_format_transaction_notification(tx))

    # 2. Payment Requests
    req_query = select(PaymentRequest).where(
        or_(
            PaymentRequest.requester_id == user_id,
            PaymentRequest.target_email == user_email
        )
    ).order_by(PaymentRequest.created_at.desc()).limit(10)
    requests = (await db.execute(req_query)).scalars().all()

    for req in requests:
        notifications.append(_format_payment_request_notification(req, user_id))

    notifications.sort(key=lambda x: x["created_at"], reverse=True)
    return notifications[:10]

def _format_transaction_notification(tx: Transaction) -> Dict[str, Any]:
    if tx.status == "failed":
        title, msg = "Payment Failed", (tx.commentary or "Transaction failed.")
    else:
        is_income = tx.amount > 0 and tx.transaction_side == "CREDIT"
        title = "Payment Received" if is_income else "Payment Sent"
        
        if tx.transaction_type == "transfer":
            prefix = "from " if is_income else "to "
            clean_merchant = tx.merchant.replace("Received from ", "").replace("Transfer to ", "") if tx.merchant else "Unknown"
            msg = f"{prefix}{clean_merchant}"
        else:
            msg = f"Merchant: {tx.merchant}" if tx.merchant else "Transaction processed"

    return {
        "id": f"tx_{tx.id}",
        "type": "transaction",
        "title": title,
        "message": msg,
        "amount": tx.amount,
        "created_at": tx.created_at,
        "link": "/client/transactions"
    }

def _format_payment_request_notification(req: PaymentRequest, user_id: int) -> Dict[str, Any]:
    is_requester = req.requester_id == user_id
    title = "Request Sent" if is_requester else "Request Received"
    msg = f"{'You requested' if is_requester else 'Someone requested'} {from_cents(req.amount)} {'from ' + req.target_email if is_requester else 'from you'}"

    return {
        "id": f"pr_{req.id}",
        "type": "payment_request",
        "title": title,
        "message": msg,
        "amount": req.amount,
        "created_at": req.created_at,
        "link": "/client/send?tab=request"
    }
