#!/usr/bin/env python3
import asyncio
import os
import uuid
from decimal import Decimal
import datetime # Moved import to top for consistent UTC-aware timestamps
import random # Added for account number generation
from sqlalchemy import select
from database import User, Account, Transaction, Outbox, SessionLocal

# TARGET_EMAIL and AMOUNT_TO_ADD are now passed as arguments to add_funds

async def add_funds(target_email: str, amount_to_add: Decimal):
    async with SessionLocal() as db:
        # 1. Find the user
        result = await db.execute(select(User).filter(User.email == target_email))
        user = result.scalars().first()

        if not user:
            print(f"Error: User {target_email} not found.")
            return

        # 2. Find the main account
        result = await db.execute(
            select(Account).filter(Account.user_id == user.id, Account.is_main == True)
        )
        account = result.scalars().first()

        if not account:
            print(f"No main account for {target_email}. Creating one...")
            account_number = "".join([str(random.randint(0, 9)) for _ in range(10)])
            from account_service import encrypt_account_number
            account = Account(
                user_id=user.id,
                account_number_encrypted=encrypt_account_number(account_number),
                account_number_last_4=account_number[-4:],
                balance=Decimal("0.00"),
                is_main=True
            )
            db.add(account)
            await db.flush() # Get the ID

        print(f"Found user {user.email} (ID: {user.id})")
        print(f"Current balance: {account.balance}")

        # 3. Update account balance
        account.balance += amount_to_add

        # 4. Create a transaction record
        tx_id = str(uuid.uuid4())
        transaction = Transaction(
            id=tx_id,
            account_id=account.id,
            amount=amount_to_add,
            category="Adjustment",
            merchant="System Admin",
            status="cleared",
            transaction_type="income",
            transaction_side="CREDIT",
            commentary="Manual fund injection for dev test",
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )

        db.add(transaction)

        # 5. Create an outbox event
        outbox_event = Outbox(
            event_type="transaction.created",
            payload={
                "transaction_id": tx_id,
                "parent_id": tx_id,
                "account_id": account.id,
                "internal_account_last_4": account.account_number_last_4,
                "sender_email": "system@karinbank.com",
                "recipient_email": user.email,
                "amount": float(amount_to_add),
                "category": "Adjustment",
                "merchant": "System Admin",
                "transaction_type": "income",
                "transaction_side": "CREDIT",
                "status": "cleared",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "commentary": "Manual fund injection for dev test"
            }
        )
        db.add(outbox_event)

        # Commit all changes
        await db.commit()

        print(f"Successfully added {amount_to_add} to {target_email}.")
        print(f"New balance: {account.balance}")
        print(f"Transaction ID: {tx_id}")

if __name__ == "__main__":
    import sys
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@example.com"
    amount = Decimal(sys.argv[2]) if len(sys.argv) > 2 else Decimal("10000000.00")
    asyncio.run(add_funds(email, amount))
