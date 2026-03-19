import asyncio
import logging
import os
import time
from datetime import datetime
from datetime import timezone, timedelta
import uuid
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import SessionLocal, ScheduledPayment, Account, User, Transaction, Outbox
from services.transfer_service import _create_p2p_transactions, _create_p2p_outbox_entries, _calculate_next_run_at

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import settings

SIMULATOR_URL = settings.SIMULATOR_URL
SIMULATOR_API_KEY = settings.SIMULATOR_API_KEY

async def get_vendors():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{SIMULATOR_URL}/vendors")
            if resp.status_code == 200:
                return resp.json().get("vendors", [])
        except httpx.RequestError as e:
            logger.error(f"Network error fetching vendors: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching vendors: {e}")

async def execute_vendor_payment(merchant_id: str, subscriber_id: str, amount: int):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "merchant_id": merchant_id,
                "subscriber_id": subscriber_id,
                "amount": amount
            }
            resp = await client.post(
                f"{SIMULATOR_URL}/billpay/execute",
                json=payload,
                headers={"X-API-KEY": SIMULATOR_API_KEY}
            )
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Network error executing vendor payment: {e}")
            return {"status": "FAILED", "failure_reason": str(e), "trace_id": "ERROR"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing vendor payment: {e}")
            return {"status": "FAILED", "failure_reason": str(e), "trace_id": "ERROR"}

async def process_scheduled_payments():
    async with SessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            # Find due payments: (Active or Retrying) and next_run_at <= now
            result = await db.execute(select(ScheduledPayment).filter(
                ScheduledPayment.status.in_(["Active", "Retrying"]),
                ScheduledPayment.next_run_at <= now
            ))
            due_payments = result.scalars().all()

            if not due_payments:
                return

            logger.info(f"Process {len(due_payments)} due auto payments...")

            for payment in due_payments:
                try:
                    await process_single_payment(db, payment, now)
                    await db.commit()
                except Exception as e:
                    # rollback implicit
                    logger.error(f"Error processing payment {payment.id}: {e}")
        except Exception as e:
            logger.error(f"Error checking scheduled payments: {e}")

async def process_single_payment(db: AsyncSession, payment: ScheduledPayment, now: datetime):
    # Retrieve the sender
    result = await db.execute(select(User).filter(User.id == payment.user_id))
    sender_user = result.scalars().first()
    if not sender_user:
        fail_payment(db, payment, "Sender not found", permanently=True)
        return

    # Determine Funding Account
    if payment.funding_account_id:
        result = await db.execute(select(Account).filter(Account.id == payment.funding_account_id))
        funding_account = result.scalars().first()
    else:
        result = await db.execute(select(Account).filter(Account.user_id == payment.user_id, Account.is_main == True))
        funding_account = result.scalars().first()

    if not funding_account:
        fail_payment(db, payment, "Funding account not found", permanently=True)
        return

    # Determine Recipient
    result = await db.execute(select(User).filter(User.email == payment.recipient_email))
    recipient = result.scalars().first()

    if not recipient:
        # Check if it's a vendor
        vendors = await get_vendors()
        vendor = next((v for v in vendors if v["email"] == payment.recipient_email), None)

        if vendor:
            # VENDOR PAYMENT FLOW
            if funding_account.balance < payment.amount:
                # Reuse existing insufficient funds logic but with a dummy recipient representation
                # Create a mini mock user for the failure record
                mock_recipient = type('obj', (object,), {'email': payment.recipient_email})
                await handle_insufficient_funds(db, payment, sender_user, funding_account, mock_recipient)
                return

            # Execute via Simulator
            # The UI should have captured subscriber_id and saved it in ScheduledPayment
            sim_resp = await execute_vendor_payment(
                merchant_id=vendor["id"],
                subscriber_id=payment.subscriber_id or "UNKNOWN",
                amount=int(payment.amount)
            )

            # Update Balance
            funding_account.balance -= payment.amount

            # Create Transaction Record
            status_map = {"CLEARED": "cleared", "FAILED": "failed"}
            vendor_tx = Transaction(
                id=str(uuid.uuid4()),
                account_id=funding_account.id,
                amount=-payment.amount,
                category="Bill Pay",
                merchant=vendor["name"],
                status=status_map.get(sim_resp.get("status"), "failed"),
                transaction_type="expense",
                transaction_side="DEBIT",
                failure_reason=sim_resp.get("failure_reason"),
                commentary=f"Bill Payment to {vendor['name']}",
                internal_account_last_4=funding_account.account_number_last_4,
                sender_email=sender_user.email,
                recipient_email=vendor["email"],
                subscriber_id=payment.subscriber_id,
                idempotency_key=str(uuid.uuid4()),
                created_at=datetime.now(timezone.utc)
            )
            db.add(vendor_tx)

            # Update Payment Record
            payment.payments_made += 1
            if sim_resp.get("status") == "CLEARED":
                payment.retry_count = 0
                payment.status = "Active"
                logger.info(f"Vendor payment {payment.id} to {vendor['name']} cleared.")
            else:
                # Handle simulator-level failure (e.g., NSF from simulator perspective)
                fail_payment(db, payment, sim_resp.get("failure_reason", "Simulator Failure"), permanently=False)
                logger.warning(f"Vendor payment {payment.id} failed: {sim_resp.get('failure_reason')}")

            # Check end condition and set next run (reusing logic later)
            update_payment_schedule(payment, now)
            return
        else:
            fail_payment(db, payment, "Recipient not found", permanently=True)
            return

    result = await db.execute(select(Account).filter(Account.user_id == recipient.id, Account.is_main == True))
    recipient_account = result.scalars().first()
    if not recipient_account:
        fail_payment(db, payment, "Recipient main account not found", permanently=True)
        return

    # Lock and transfer (simulate P2P logic but within this transaction)
    try:
        # Sort IDs for deterministic locking
        first_id, second_id = sorted([funding_account.id, recipient_account.id])
        result1 = await db.execute(select(Account).filter(Account.id == first_id).with_for_update())
        acc1 = result1.scalars().first()
        result2 = await db.execute(select(Account).filter(Account.id == second_id).with_for_update())
        acc2 = result2.scalars().first()

        if first_id == funding_account.id:
            sender_locked = acc1
            recipient_locked = acc2
        else:
            sender_locked = acc2
            recipient_locked = acc1

        if sender_locked.balance < payment.amount:
            # INSUFFICIENT FUNDS
            await handle_insufficient_funds(db, payment, sender_user, funding_account, recipient)
            return

        # Execute Transfer
        sender_locked.balance -= payment.amount
        recipient_locked.balance += payment.amount

        # Write Transactions
        tx_id_parent, tx_id_sender, tx_id_recipient = _create_p2p_transactions(
            db,
            sender_locked.id,
            recipient_locked.id,
            payment.amount,
            recipient.email,
            sender_user.email,
            str(uuid.uuid4()), # Need new idempotency key for this run
            "127.0.0.1",
            "system-worker",
            sender_account_last_4=sender_locked.account_number_last_4,
            recipient_account_last_4=recipient_locked.account_number_last_4,
            commentary="Scheduled Payment"
        )
        # Update Transactions with subscriber_id if any (unlikely for P2P but for completeness)
        # (Already handled by helper in main.py usually, but we could add it here)

        _create_p2p_outbox_entries(
            db,
            sender_locked.id,
            recipient_locked.id,
            payment.amount,
            sender_user.email,
            recipient.email,
            tx_id_parent,
            tx_id_sender,
            tx_id_recipient,
            "Scheduled Payment"
        )

        # Update Payment Record
        payment.payments_made += 1
        payment.retry_count = 0
        payment.status = "Active"

        update_payment_schedule(payment, now)

        logger.info(f"Payment {payment.id} successful.")

    except Exception as e:
        logger.error(f"Transfer error for scheduled payment {payment.id}: {e}")
        fail_payment(db, payment, str(e), permanently=False)

def update_payment_schedule(payment: ScheduledPayment, now: datetime):
    # Check end condition
    if payment.frequency == "One-time":
        payment.status = "Completed"
        payment.next_run_at = None
    elif payment.end_condition == "target" and payment.target_payments and payment.payments_made >= payment.target_payments:
        payment.status = "Completed"
        payment.next_run_at = None
    else:
        # Set next run date
        payment.next_run_at = _calculate_next_run_at(now, payment.frequency, payment.frequency_interval)

        if payment.end_condition == "date" and payment.end_date and payment.next_run_at > payment.end_date:
            payment.status = "Completed"
            payment.next_run_at = None

async def handle_insufficient_funds(db: AsyncSession, payment: ScheduledPayment, sender: User, funding_account: Account, recipient: User):
    payment.retry_count += 1

    # Create a failed transaction record to notify the user
    failed_tx = Transaction(
        id=str(uuid.uuid4()),
        account_id=funding_account.id,
        amount=-payment.amount,
        category="Transfer",
        merchant=f"Transfer to {recipient.email}",
        status="failed",
        transaction_type="transfer",
        transaction_side="DEBIT",
        failure_reason="Insufficient funds",
        commentary="Recurring payment failed. Please Top Up and Retry.",
        internal_account_last_4=funding_account.account_number_last_4,
        sender_email=sender.email,
        recipient_email=recipient.email,
        subscriber_id=getattr(payment, 'subscriber_id', None),
        created_at=datetime.now(timezone.utc)
    )
    db.add(failed_tx)

    # Emit to ClickHouse via Outbox
    from main import _create_p2p_outbox_entries
    from database import Account
    # We only need the sender's side for a failed funding attempt
    db.add(Outbox(
        event_type="p2p.sender",
        payload={
            "transaction_id": failed_tx.id,
            "account_id": funding_account.id,
            "amount": int(failed_tx.amount),
            "category": failed_tx.category,
            "merchant": failed_tx.merchant,
            "transaction_type": failed_tx.transaction_type,
            "transaction_side": failed_tx.transaction_side,
            "status": "failed",
            "failure_reason": failed_tx.failure_reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "commentary": failed_tx.commentary
        }
    ))
    # Invoke common fail_payment logic for retry handling
    fail_payment(db, payment, "Insufficient funds", permanently=False)


def fail_payment(db: AsyncSession, payment: ScheduledPayment, reason: str, permanently: bool = True):
    payment.failure_reason = reason
    if permanently:
        payment.status = "Failed"
        payment.next_run_at = None
        logger.info(f"Payment {payment.id} permanently failed: {reason}")
    else:
        # Retry logic consolidated here
        payment.retry_count += 1
        if payment.retry_count >= 3:
            payment.status = "Failed"
            payment.next_run_at = None
            logger.info(f"Payment {payment.id} permanently failed after 3 retries due to {reason}.")
        else:
            payment.status = "Retrying"
            payment.next_run_at = datetime.now(timezone.utc) + timedelta(days=1)
            logger.info(f"Payment {payment.id} failed logic due to {reason}. Retry {payment.retry_count}/3 scheduled for +24h.")

async def main():
    logger.info("Starting Scheduled Payments Worker...")
    while True:
        try:
            await process_scheduled_payments()
        except Exception as e:
            logger.error(f"Worker crashed: {e}")
        await asyncio.sleep(60) # Run every minute

if __name__ == "__main__":
    asyncio.run(main())
