#!/usr/bin/env python3
"""
Generate realistic transaction data for the past 40 days
and ingest into PostgreSQL and ClickHouse
Includes expenses, income (salary), and P2P transfers with proper balance updates
"""

import random
import uuid
import os
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2
import clickhouse_connect
import json

# Database connections
PG_CONN = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    database=os.getenv("POSTGRES_DB", "banking_db"),
    user=os.getenv("POSTGRES_USER", "admin"),
    password=os.getenv("POSTGRES_PASSWORD")
)

CH_CLIENT = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=os.getenv("CLICKHOUSE_PORT", "8123"),
    username=os.getenv("CLICKHOUSE_USER", "admin"),
    password=os.getenv("CLICKHOUSE_PASSWORD")
)
CH_DB = os.getenv("CLICKHOUSE_DB", "banking_log")

# User and account data
USERS = {
    "ikarin@example.com": {"id": 1, "account_id": 1},
    "ikarin2@admin.com": {"id": 3, "account_id": 3}
}

# Expenses (items that should decrease balance)
EXPENSE_MERCHANTS = {
    "Groceries": ["Whole Foods", "Trader Joe's", "Kroger", "Safeway", "Costco"],
    "Dining": ["Starbucks", "McDonald's", "Chipotle", "Olive Garden", "TGI Friday's"],
    "Transportation": ["Uber", "Lyft", "Shell Gas", "Chevron", "Parking Plus"],
    "Entertainment": ["Netflix", "Spotify", "Disney+", "Hulu", "Movie Theater"],
    "Shopping": ["Amazon", "Walmart", "Target", "Best Buy", "Apple Store"],
    "Travel": ["Delta Airlines", "United Airlines", "Marriott", "Hilton", "Airbnb"],
    "Cloud Services": ["AWS", "Google Cloud", "Azure", "DigitalOcean"],
    "Utilities": ["Electric Co", "Water Company", "Internet Provider", "Phone Service"],
    "Healthcare": ["CVS Pharmacy", "Walgreens", "Hospital", "Dental Office"],
    "Office Supplies": ["Staples", "Office Depot", "Amazon Business", "Micro Center"],
    "Subscription": ["Adobe Cloud", "Microsoft 365", "Slack", "Zoom Pro"]
}

# Income sources
INCOME_MERCHANTS = {
    "Salary": ["Company Salary", "Monthly Paycheck"],
    "Freelance": ["Freelance Income", "Contract Work", "Consulting Fee"],
    "Refund": ["Store Refund", "Tax Refund"]
}

def generate_transactions(days=40):
    """Generate realistic transactions including expenses, income, and transfers"""
    transactions = []
    balance_tracker = {
        "ikarin@example.com": Decimal("64230.15"),
        "ikarin2@admin.com": Decimal("2500.00")
    }
    
    base_date = datetime.now() - timedelta(days=days)
    
    # Step 1: Add weekly salary income every Monday
    current_date = base_date
    while current_date <= datetime.now():
        # Check if it's Monday (weekday() returns 0 for Monday)
        if current_date.weekday() == 0:
            for user_email in USERS.keys():
                salary_amount = Decimal(str(round(random.uniform(3500, 5500), 2)))
                transactions.append({
                    "id": str(uuid.uuid4()),
                    "account_id": USERS[user_email]["account_id"],
                    "amount": salary_amount,
                    "category": "Salary",
                    "merchant": "Company Salary",
                    "status": "completed",
                    "created_at": current_date,
                    "sender_email": "Employer",  # Special marker for income
                    "recipient_email": user_email,
                    "transaction_type": "income",
                    "timestamp": current_date.isoformat()
                })
                balance_tracker[user_email] += salary_amount
        
        current_date += timedelta(days=1)
    
    # Step 2: Add random expenses (most transactions)
    expense_count = 0
    while expense_count < 80:  # Generate 80 expense transactions
        random_days = random.randint(0, days-1)
        tx_date = base_date + timedelta(days=random_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        # Pick sender (the one spending money)
        sender_email = random.choice(list(USERS.keys()))
        sender_account_id = USERS[sender_email]["account_id"]
        
        # Pick expense category and merchant
        expense_category = random.choice(list(EXPENSE_MERCHANTS.keys()))
        merchant = random.choice(EXPENSE_MERCHANTS[expense_category])
        
        # Generate expense amount
        amount = Decimal(str(round(random.uniform(10, 500), 2)))
        
        # Only add if it won't create negative balance
        if balance_tracker[sender_email] >= amount:
            transactions.append({
                "id": str(uuid.uuid4()),
                "account_id": sender_account_id,
                "amount": amount,
                "category": expense_category,
                "merchant": merchant,
                "status": "completed",
                "created_at": tx_date,
                "sender_email": sender_email,
                "recipient_email": merchant,  # Merchant as recipient
                "transaction_type": "expense",
                "timestamp": tx_date.isoformat()
            })
            balance_tracker[sender_email] -= amount
            expense_count += 1
    
    # Step 3: Add P2P transfers between users (some transactions)
    transfer_count = 0
    while transfer_count < 15:  # Generate 15 P2P transfers
        random_days = random.randint(0, days-1)
        tx_date = base_date + timedelta(days=random_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        # Pick sender and recipient (different)
        sender_email, recipient_email = random.sample(list(USERS.keys()), 2)
        sender_account_id = USERS[sender_email]["account_id"]
        
        # Generate transfer amount
        amount = Decimal(str(round(random.uniform(50, 300), 2)))
        
        # Only add if sender has sufficient balance
        if balance_tracker[sender_email] >= amount:
            transactions.append({
                "id": str(uuid.uuid4()),
                "account_id": sender_account_id,
                "amount": amount,
                "category": "Transfer",
                "merchant": f"Transfer to {recipient_email}",
                "status": "completed",
                "created_at": tx_date,
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "transaction_type": "transfer",
                "timestamp": tx_date.isoformat()
            })
            balance_tracker[sender_email] -= amount
            balance_tracker[recipient_email] += amount
            transfer_count += 1
    
    # Sort by date
    transactions.sort(key=lambda x: x["created_at"])
    
    return transactions, balance_tracker

def get_current_balance(cursor, account_id):
    """Get current balance from database"""
    cursor.execute("SELECT balance FROM accounts WHERE id = %s", (account_id,))
    result = cursor.fetchone()
    return result[0] if result else Decimal('0')

def insert_to_postgres(transactions, balance_tracker):
    """Insert transactions into PostgreSQL and update account balances"""
    cursor = PG_CONN.cursor()
    
    try:
        # First, insert all transactions (new ones only)
        inserted_count = 0
        for tx in transactions:
            try:
                cursor.execute("""
                    INSERT INTO transactions (id, account_id, amount, category, merchant, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    tx["id"],
                    tx["account_id"],
                    float(tx["amount"]),
                    tx["category"],
                    tx["merchant"],
                    tx["status"],
                    tx["created_at"]
                ))
                inserted_count += 1
            except psycopg2.IntegrityError:
                # Transaction already exists, skip it
                PG_CONN.rollback()
                continue
        
        # Recalculate balances based on transaction types
        for email, user_data in USERS.items():
            account_id = user_data["account_id"]
            
            # Get income (where recipient is the user)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE account_id = %s AND category = 'Salary'
            """, (account_id,))
            income = Decimal(str(cursor.fetchone()[0]))
            
            # Get expenses and transfers (where sender is the user)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE account_id = %s AND category != 'Salary'
            """, (account_id,))
            expenses = Decimal(str(cursor.fetchone()[0]))
            
            # Starting balance is 100000, plus income, minus expenses
            new_balance = Decimal('100000') + income - expenses
            cursor.execute("""
                UPDATE accounts SET balance = %s WHERE id = %s
            """, (float(new_balance), account_id))
            balance_tracker[email] = new_balance
        
        PG_CONN.commit()
        print(f"✅ Inserted {inserted_count} new transactions into PostgreSQL")
        print(f"✅ Updated account balances:")
        for email, balance in sorted(balance_tracker.items()):
            print(f"   • {email}: ${balance:,.2f}")
    except Exception as e:
        PG_CONN.rollback()
        print(f"❌ Error inserting to PostgreSQL: {e}")
        raise
    finally:
        cursor.close()

def insert_to_clickhouse(transactions):
    """Insert transactions into ClickHouse for analytics"""
    try:
        data_to_insert = [
            [
                tx["id"],
                tx["account_id"],
                tx["sender_email"],
                tx["recipient_email"],
                float(tx["amount"]),
                tx["category"],
                tx["merchant"],
                tx["transaction_type"],
                tx["timestamp"]
            ]
            for tx in transactions
        ]
        
        CH_CLIENT.insert(
            f'{CH_DB}.transactions',
            data_to_insert,
            column_names=[
                'transaction_id',
                'account_id',
                'sender_email',
                'recipient_email',
                'amount',
                'category',
                'merchant',
                'transaction_type',
                'event_time'
            ]
        )
        print(f"✅ Inserted {len(transactions)} transactions into ClickHouse")
    except Exception as e:
        print(f"❌ Error inserting to ClickHouse: {e}")
        raise

def print_summary(transactions, balance_tracker):
    """Print summary statistics"""
    print("\n" + "="*70)
    print("📊 TRANSACTION DATA GENERATION SUMMARY")
    print("="*70)
    
    total_transactions = len(transactions)
    total_volume = sum(tx["amount"] for tx in transactions)
    
    # Categorize by type
    income_txs = [tx for tx in transactions if tx["transaction_type"] == "income"]
    expense_txs = [tx for tx in transactions if tx["transaction_type"] == "expense"]
    transfer_txs = [tx for tx in transactions if tx["transaction_type"] == "transfer"]
    
    income_total = sum(tx["amount"] for tx in income_txs)
    expense_total = sum(tx["amount"] for tx in expense_txs)
    transfer_total = sum(tx["amount"] for tx in transfer_txs)
    
    print(f"\n📈 Overall Statistics:")
    print(f"  Total Transactions: {total_transactions}")
    print(f"  Total Volume: ${total_volume:,.2f}")
    print(f"  Average Transaction: ${total_volume/total_transactions:,.2f}")
    
    print(f"\n💰 Transaction Breakdown:")
    print(f"  Income:    {len(income_txs):2d} transactions  ${income_total:,.2f}")
    print(f"  Expenses:  {len(expense_txs):2d} transactions  ${expense_total:,.2f}")
    print(f"  Transfers: {len(transfer_txs):2d} transactions  ${transfer_total:,.2f}")
    
    print(f"\n👥 Account Balances:")
    for email, balance in sorted(balance_tracker.items()):
        print(f"  • {email}: ${balance:,.2f}")
    
    # Group expenses by category
    expense_categories = {}
    for tx in expense_txs:
        expense_categories[tx["category"]] = expense_categories.get(tx["category"], 0) + 1
    
    print(f"\n📂 Expense Categories:")
    for category, count in sorted(expense_categories.items(), key=lambda x: x[1], reverse=True):
        total = sum(tx["amount"] for tx in expense_txs if tx["category"] == category)
        print(f"  • {category}: {count} - ${total:,.2f}")
    
    print(f"\n📅 Date Range: Last 40 days")
    print(f"✅ All data successfully ingested to both PostgreSQL and ClickHouse\n")

def main():
    print("🚀 Generating transaction data for past 40 days...")
    print("   Including salaries (every Monday), expenses, and P2P transfers...")
    
    # Generate transactions
    transactions, balance_tracker = generate_transactions(days=40)
    
    # Insert into databases
    print("\n📝 Ingesting into databases...")
    insert_to_postgres(transactions, balance_tracker)
    insert_to_clickhouse(transactions)
    
    # Print summary
    print_summary(transactions, balance_tracker)

if __name__ == "__main__":
    main()
