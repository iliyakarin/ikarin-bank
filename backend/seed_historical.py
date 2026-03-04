import os
import uuid
import json
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Set up environment to run standalone (within docker)
os.environ.setdefault("POSTGRES_HOST", "postgres")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "admin")
os.environ.setdefault("POSTGRES_PASSWORD", "admin123")
os.environ.setdefault("POSTGRES_DB", "banking_db")

from database import SessionLocal, User, Account, Transaction, Outbox

target_emails = ["ikarin2@admin.com", "ikarin@example.com"]

EXPENSES = ["Groceries", "Dining", "Transportation", "Entertainment", "Shopping"]
MERCHANTS = ["Amazon", "Whole Foods", "Uber", "Netflix", "Target", "Starbucks"]

def seed_data():
    db = SessionLocal()
    
    users_data = {}
    for email in target_emails:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found. Skipping.")
            continue
        account = db.query(Account).filter(Account.user_id == user.id).first()
        if not account:
            print(f"Account for {email} not found. Skipping.")
            continue
            
        users_data[email] = {
            "user_id": user.id,
            "account_id": account.id,
            "account": account
        }

    if not users_data:
        print("No users found to seed.")
        return

    now = datetime.utcnow()
    transactions_added = 0
    total_days = 365
    
    for i in range(total_days, -1, -1):
        current_date = now - timedelta(days=i)
        
        for email, udata in users_data.items():
            acc_id = udata["account_id"]
            acc = udata["account"]
            
            # 1. Salary 2 times a month (1st and 15th)
            if current_date.day in [1, 15]:
                amount = Decimal(str(round(random.uniform(3000, 5000), 2)))
                tx_id = str(uuid.uuid4())
                
                # Create Income Transaction
                tx = Transaction(
                    id=tx_id,
                    account_id=acc_id,
                    amount=amount,
                    category="Salary",
                    merchant="Company Payroll",
                    status="cleared",
                    transaction_type="income",
                    transaction_side="CREDIT",
                    created_at=current_date
                )
                db.add(tx)
                acc.balance += amount
                
                # Outbox for kafka
                payload = {
                    "id": tx_id,
                    "account_id": acc_id,
                    "sender_email": "employer@company.com",
                    "recipient_email": email,
                    "amount": float(amount),
                    "category": "Salary",
                    "merchant": "Company Payroll",
                    "transaction_type": "income",
                    "timestamp": current_date.isoformat()
                }
                outbox = Outbox(
                    event_type="publish_transaction",
                    payload=payload,
                    created_at=current_date
                )
                db.add(outbox)
                transactions_added += 1

            # 2. Daily Expenses (1-2 per day)
            num_expenses = random.randint(1, 2)
            for _ in range(num_expenses):
                amount = Decimal(str(round(random.uniform(10, 150), 2)))
                if acc.balance < amount:
                    continue # Skip if cant afford
                    
                tx_id = str(uuid.uuid4())
                cat = random.choice(EXPENSES)
                merch = random.choice(MERCHANTS)
                
                # Create Expense Transaction
                tx = Transaction(
                    id=tx_id,
                    account_id=acc_id,
                    amount=amount,
                    category=cat,
                    merchant=merch,
                    status="cleared",
                    transaction_type="expense",
                    transaction_side="DEBIT",
                    created_at=current_date
                )
                db.add(tx)
                acc.balance -= amount
                
                # Outbox
                payload = {
                    "id": tx_id,
                    "account_id": acc_id,
                    "sender_email": email,
                    "recipient_email": None,
                    "amount": -float(amount),
                    "category": cat,
                    "merchant": merch,
                    "transaction_type": "expense",
                    "timestamp": current_date.isoformat()
                }
                outbox = Outbox(
                    event_type="publish_transaction",
                    payload=payload,
                    created_at=current_date
                )
                db.add(outbox)
                transactions_added += 1
                
    db.commit()
    print(f"Successfully added {transactions_added} transactions and updated balances.")

if __name__ == "__main__":
    seed_data()
