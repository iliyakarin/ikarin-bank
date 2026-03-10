import asyncio
import os
import uuid
from decimal import Decimal
from sqlalchemy import select
from database import User, Account, Transaction, Outbox, SessionLocal

TARGET_EMAIL = "admin@example.com"
AMOUNT_TO_ADD = Decimal("1000000.00")

async def add_funds():
    async with SessionLocal() as db:
        # 1. Find the user
        result = await db.execute(select(User).filter(User.email == TARGET_EMAIL))
        user = result.scalars().first()
        
        if not user:
            print(f"Error: User {TARGET_EMAIL} not found.")
            return

        # 2. Find the main account
        result = await db.execute(
            select(Account).filter(Account.user_id == user.id, Account.is_main == True)
        )
        account = result.scalars().first()
        
        if not account:
            print(f"Error: Main account for user {TARGET_EMAIL} not found.")
            return

        print(f"Found user {user.email} (ID: {user.id})")
        print(f"Current balance: {account.balance}")

        # 3. Update account balance
        account.balance += AMOUNT_TO_ADD
        
        # 4. Create a transaction record
        tx_id = str(uuid.uuid4())
        transaction = Transaction(
            id=tx_id,
            account_id=account.id,
            amount=AMOUNT_TO_ADD,
            category="Adjustment",
            merchant="System Admin",
            status="cleared",
            transaction_type="income",
            transaction_side="CREDIT",
            commentary="Manual fund injection for dev test",
            created_at=asyncio.get_event_loop().time() # This will be replaced by datetime in actual execution
        )
        # Fix created_at to use datetime
        import datetime
        transaction.created_at = datetime.datetime.utcnow()
        
        db.add(transaction)

        # 5. Create an outbox event
        outbox_event = Outbox(
            event_type="transaction.created",
            payload={
                "id": tx_id,
                "account_id": account.id,
                "user_id": user.id,
                "amount": str(AMOUNT_TO_ADD),
                "type": "income",
                "status": "cleared"
            }
        )
        db.add(outbox_event)

        # Commit all changes
        await db.commit()
        
        print(f"Successfully added {AMOUNT_TO_ADD} to {TARGET_EMAIL}.")
        print(f"New balance: {account.balance}")
        print(f"Transaction ID: {tx_id}")

if __name__ == "__main__":
    asyncio.run(add_funds())
