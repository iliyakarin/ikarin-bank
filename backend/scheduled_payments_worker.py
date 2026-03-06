import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session
from database import SessionLocal, ScheduledPayment, Account, User, Transaction, Outbox
from main import _execute_p2p_balances, _create_p2p_transactions, _create_p2p_outbox_entries, _calculate_next_run_at

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_scheduled_payments():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find due payments: (Active or Retrying) and next_run_at <= now
        due_payments = db.query(ScheduledPayment).filter(
            ScheduledPayment.status.in_(["Active", "Retrying"]),
            ScheduledPayment.next_run_at <= now
        ).all()

        if not due_payments:
            return

        logger.info(f"Process {len(due_payments)} due auto payments...")

        for payment in due_payments:
            try:
                process_single_payment(db, payment, now)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing payment {payment.id}: {e}")

    finally:
        db.close()

def process_single_payment(db: Session, payment: ScheduledPayment, now: datetime):
    # Retrieve the sender
    sender_user = db.query(User).filter(User.id == payment.user_id).first()
    if not sender_user:
        fail_payment(db, payment, "Sender not found", permanently=True)
        return

    # Determine Funding Account
    if payment.funding_account_id:
        funding_account = db.query(Account).filter(Account.id == payment.funding_account_id).first()
    else:
        funding_account = db.query(Account).filter(Account.user_id == payment.user_id, Account.is_main == True).first()

    if not funding_account:
        fail_payment(db, payment, "Funding account not found", permanently=True)
        return

    # Determine Recipient
    recipient = db.query(User).filter(User.email == payment.recipient_email).first()
    if not recipient:
        fail_payment(db, payment, "Recipient not found", permanently=True)
        return

    recipient_account = db.query(Account).filter(Account.user_id == recipient.id, Account.is_main == True).first()
    if not recipient_account:
        fail_payment(db, payment, "Recipient main account not found", permanently=True)
        return

    # Lock and transfer (simulate P2P logic but within this transaction)
    try:
        # Sort IDs for deterministic locking
        first_id, second_id = sorted([funding_account.id, recipient_account.id])
        acc1 = db.query(Account).filter(Account.id == first_id).with_for_update().first()
        acc2 = db.query(Account).filter(Account.id == second_id).with_for_update().first()
        
        if first_id == funding_account.id:
            sender_locked = acc1
            recipient_locked = acc2
        else:
            sender_locked = acc2
            recipient_locked = acc1

        if sender_locked.balance < payment.amount:
            # INSUFFICIENT FUNDS
            handle_insufficient_funds(db, payment, sender_user, funding_account, recipient)
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
            "Scheduled Payment"
        )
        # Manually ensure status='cleared' since outbound is initially 'pending' but internal DB transfers are fast
        # Wait, the outbound needs to be 'pending' so Kafka picks it up properly if we use Outbox?
        # Let's let outbox_worker do its job
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

        # Check end condition
        if payment.end_condition == "target" and payment.target_payments and payment.payments_made >= payment.target_payments:
            payment.status = "Completed"
            payment.next_run_at = None
        else:
            # Set next run date
            payment.next_run_at = _calculate_next_run_at(now, payment.frequency, payment.frequency_interval)
            
            if payment.end_condition == "date" and payment.end_date and payment.next_run_at > payment.end_date:
                payment.status = "Completed"
                payment.next_run_at = None

        logger.info(f"Payment {payment.id} successful.")

    except Exception as e:
        logger.error(f"Transfer error for scheduled payment {payment.id}: {e}")
        fail_payment(db, payment, str(e), permanently=False)

def handle_insufficient_funds(db: Session, payment: ScheduledPayment, sender: User, funding_account: Account, recipient: User):
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
        created_at=datetime.utcnow()
    )
    db.add(failed_tx)

    if payment.retry_count >= 3:
        payment.status = "Failed" # Terminal state
        payment.next_run_at = None
        logger.info(f"Payment {payment.id} permanently failed after 3 retries.")
    else:
        payment.status = "Retrying"
        payment.next_run_at = datetime.utcnow() + timedelta(days=1)
        logger.info(f"Payment {payment.id} failed logic due to funds. Retry {payment.retry_count}/3 scheduled for +24h.")

def fail_payment(db: Session, payment: ScheduledPayment, reason: str, permanently: bool = True):
    if permanently:
        payment.status = "Failed"
        payment.next_run_at = None
    else:
        # Same logic as insufficient funds basically
        payment.retry_count += 1
        if payment.retry_count >= 3:
            payment.status = "Failed"
            payment.next_run_at = None
        else:
            payment.status = "Retrying"
            payment.next_run_at = datetime.utcnow() + timedelta(days=1)

def main():
    logger.info("Starting Scheduled Payments Worker...")
    while True:
        try:
            process_scheduled_payments()
        except Exception as e:
            logger.error(f"Worker crashed: {e}")
        time.sleep(60) # Run every minute

if __name__ == "__main__":
    main()
