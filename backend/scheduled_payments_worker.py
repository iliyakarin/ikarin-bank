import asyncio
import logging
import datetime
from datetime import timezone, timedelta
import uuid
import httpx
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, and_, or_
from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction
from models.management import ScheduledPayment, Outbox
from services.transfer_service import _create_p2p_transactions, _calculate_next_run_at, _create_p2p_outbox_entries
from config import settings

logger = logging.getLogger(__name__)

SIMULATOR_URL = settings.SIMULATOR_URL
SIMULATOR_API_KEY = getattr(settings, "SIMULATOR_API_KEY", "default-key")

async def get_vendors():
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{SIMULATOR_URL}/vendors", timeout=5.0)
            return res.json().get("vendors", []) if res.status_code == 200 else []
        except Exception: return []

async def execute_vendor_payment(v_id: str, s_id: str, amount: int):
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(f"{SIMULATOR_URL}/billpay/execute", json={"merchant_id": v_id, "subscriber_id": s_id, "amount": float(amount)/100.0}, headers={"X-API-Key": SIMULATOR_API_KEY}, timeout=10.0)
            return res.json()
        except Exception as e: return {"status": "FAILED", "failure_reason": str(e)}

async def process_scheduled_payments():
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(engine) as db:
        try:
            now = datetime.datetime.now(timezone.utc)
            stmt = select(ScheduledPayment).where(ScheduledPayment.status.in_(["Active", "Retrying"]), ScheduledPayment.next_run_at <= now)
            due = (await db.execute(stmt)).scalars().all()
            for p in due:
                try:
                    await process_single_payment(db, p, now)
                    await db.commit()
                except Exception as e:
                    logger.error(f"Fail p {p.id}: {e}")
                    await db.rollback()
        except Exception as e: logger.error(f"Worker loop err: {e}")

async def process_single_payment(db: AsyncSession, p: ScheduledPayment, now: datetime.datetime):
    user = (await db.execute(select(User).where(User.id == p.user_id))).scalars().first()
    if not user:
        p.status, p.next_run_at = "Failed", None
        return

    acc_stmt = select(Account).where(Account.user_id == p.user_id)
    if p.funding_account_id: acc_stmt = acc_stmt.where(Account.id == p.funding_account_id)
    else: acc_stmt = acc_stmt.where(Account.is_main == True)
    f_acc = (await db.execute(acc_stmt)).scalars().first()
    if not f_acc:
        p.status, p.next_run_at = "Failed", None
        return

    rec = (await db.execute(select(User).where(User.email == p.recipient_email))).scalars().first()
    if not rec:
        vendors = await get_vendors()
        v = next((v for v in vendors if v["email"] == p.recipient_email), None)
        if v:
            if f_acc.balance < p.amount:
                await handle_fail(db, p, f_acc, user.email, v["email"], v["name"])
                return
            sim = await execute_vendor_payment(v["id"], p.subscriber_id or "UNK", p.amount)
            f_acc.balance -= p.amount
            db.add(Transaction(
                id=str(uuid.uuid4()), account_id=f_acc.id, amount=-p.amount, category="Bill Pay", merchant=v["name"],
                status="cleared" if sim.get("status") == "CLEARED" else "failed", transaction_type="expense",
                transaction_side="DEBIT", failure_reason=sim.get("failure_reason"), internal_account_last_4=f_acc.account_number_last_4,
                sender_email=user.email, recipient_email=v["email"]
            ))
            p.payments_made += 1
            _update_schedule(p, now)
            return
        p.status, p.next_run_at = "Failed", None
        return

    r_acc = (await db.execute(select(Account).where(Account.user_id == rec.id, Account.is_main == True))).scalars().first()
    if not r_acc:
        p.status, p.next_run_at = "Failed", None
        return

    if f_acc.balance < p.amount:
        await handle_fail(db, p, f_acc, user.email, rec.email, f"Transfer to {rec.email}")
        return

    f_acc.balance -= p.amount
    r_acc.balance += p.amount
    p_id, s_id, rec_id = await _create_p2p_transactions(db, f_acc.id, r_acc.id, p.amount, rec.email, user.email, None, "127.0.0.1", "system", f_acc.account_number_last_4, r_acc.account_number_last_4, "Scheduled")
    await _create_p2p_outbox_entries(db, f_acc, r_acc, p.amount, user.email, rec.email, p_id, s_id, rec_id, "Scheduled")
    p.payments_made += 1
    _update_schedule(p, now)

def _update_schedule(p: ScheduledPayment, now: datetime.datetime):
    if p.frequency == "One-time" or (p.end_condition == "target" and p.payments_made >= (p.target_payments or 0)):
        p.status, p.next_run_at = "Completed", None
    else:
        p.next_run_at = _calculate_next_run_at(now, p.frequency)
        if p.end_condition == "date" and p.end_date and p.next_run_at > p.end_date:
            p.status, p.next_run_at = "Completed", None

async def handle_fail(db, p, acc, s_email, r_email, merchant):
    p.retry_count += 1
    db.add(Transaction(
        id=str(uuid.uuid4()), account_id=acc.id, amount=-p.amount, category="Transfer", merchant=merchant,
        status="failed", transaction_type="transfer", transaction_side="DEBIT", failure_reason="Insufficient funds",
        internal_account_last_4=acc.account_number_last_4, sender_email=s_email, recipient_email=r_email
    ))
    if p.retry_count >= 3: p.status, p.next_run_at = "Failed", None
    else: p.status, p.next_run_at = "Retrying", datetime.datetime.now(timezone.utc) + timedelta(days=1)

async def main():
    while True:
        await process_scheduled_payments()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
