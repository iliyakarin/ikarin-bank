import time
import os
import json
import logging
from datetime import datetime, timedelta
import clickhouse_connect
from sqlalchemy.orm import Session
from database import SessionLocal, Transaction, Outbox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

CHECK_INTERVAL_SECONDS = 86400 # Run every 24 hours

def run_sync_check():
    logger.info("Starting Postgres <-> ClickHouse Sync Check...")

    # Connect to PostgreSQL
    db: Session = SessionLocal()
    
    try:
        # Connect to ClickHouse
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
        )

        # 1. Get recent transactions from Postgres (e.g. past 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        pg_transactions = db.query(Transaction).filter(
            Transaction.created_at >= cutoff_date
        ).all()

        if not pg_transactions:
            logger.info("No recent Postgres transactions found.")
            return

        pg_tx_map = {str(tx.id): tx for tx in pg_transactions}
        pg_ids = list(pg_tx_map.keys())

        # 2. Query ClickHouse for those specific IDs in chunks to prevent query size limits
        ch_ids = set()
        chunk_size = 1000
        for i in range(0, len(pg_ids), chunk_size):
            chunk = pg_ids[i:i + chunk_size]
            query = f"""
                SELECT toString(transaction_id) as id 
                FROM banking.transactions 
                WHERE transaction_id IN ({','.join([f"'{tid}'" for tid in chunk])})
            """
            ch_results = ch_client.query(query).result_rows
            ch_ids.update([row[0] for row in ch_results])

        # 3. Find missing IDs
        missing_ids = [tid for tid in pg_ids if tid not in ch_ids]
        
        if not missing_ids:
            logger.info(f"Sync check complete. All {len(pg_ids)} recent transactions are in ClickHouse.")
            return

        logger.warning(f"Found {len(missing_ids)} missing transactions in ClickHouse. Queuing for resync...")

        # 4. Create Outbox entries for missing transactions
        for tx_id in missing_ids:
            tx = pg_tx_map[tx_id]
            
            payload = {
                "transaction_id": str(tx.id),
                "parent_id": str(tx.parent_id) if tx.parent_id else None,
                "account_id": tx.account_id,
                "amount": float(tx.amount),
                "category": tx.category,
                "merchant": tx.merchant,
                "transaction_type": tx.transaction_type,
                "transaction_side": tx.transaction_side,
                "timestamp": tx.created_at.isoformat() if tx.created_at else datetime.utcnow().isoformat(),
                # Fallback sender/recipient logic used in transfer routes
                "sender_email": tx.merchant.replace("Received from ", "") if tx.transaction_type == "transfer" and tx.amount > 0 else None,
                "recipient_email": tx.merchant.replace("Transfer to ", "") if tx.transaction_type == "transfer" and tx.amount < 0 else None
            }
            
            outbox_entry = Outbox(
                event_type="TransactionCreated", # or Resync
                payload=payload,
                status="pending"
            )
            db.add(outbox_entry)
            
        db.commit()
        logger.info(f"Successfully queued {len(missing_ids)} missing transactions to the outbox.")

    except Exception as e:
        logger.error(f"Error during sync check: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info(f"Sync checker initialized. Checking every {CHECK_INTERVAL_SECONDS} seconds.")
    # Allow services to start up
    time.sleep(10)
    while True:
        try:
            run_sync_check()
        except Exception as e:
            logger.error(f"Fatal error in sync checker loop: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)
