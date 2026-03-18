import time
import os
import json
import logging
from datetime import datetime
from datetime import timezone, timedelta
import asyncio
import clickhouse_connect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import SessionLocal, Transaction, Outbox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from config import settings

CHECK_INTERVAL_SECONDS = 86400 # Run every 24 hours

async def run_sync_check():
    logger.info("Starting Postgres <-> ClickHouse Sync Check...")

    # Connect to PostgreSQL
    async with SessionLocal() as db:
    
        try:
            # Connect to ClickHouse
            ch_client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST, 
                port=settings.CLICKHOUSE_PORT, 
                username=settings.CLICKHOUSE_USER, 
                password=settings.CLICKHOUSE_PASSWORD
            )

            # 1. Get recent transactions from Postgres (e.g. past 7 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            result = await db.execute(select(Transaction).filter(
                Transaction.created_at >= cutoff_date
            ))
            pg_transactions = result.scalars().all()

            if not pg_transactions:
                logger.info("No recent Postgres transactions found.")
                return

            pg_tx_map = {str(tx.id): tx for tx in pg_transactions}
            pg_ids = list(pg_tx_map.keys())

            # 2. Query ClickHouse for those specific IDs
            ch_status_map = {}
            chunk_size = 1000
            for i in range(0, len(pg_ids), chunk_size):
                chunk = pg_ids[i:i + chunk_size]
                query = f"""
                    SELECT toString(transaction_id) as id, status
                    FROM {settings.CLICKHOUSE_DB}.transactions 
                    WHERE transaction_id IN {{ids:Array(String)}}
                    ORDER BY event_time DESC
                """
                ch_results = ch_client.query(query, parameters={'ids': chunk}).result_rows
                for row in ch_results:
                    tid, status = row
                    if tid not in ch_status_map: # Only keep the latest one because of ORDER BY
                        ch_status_map[tid] = status

            # 3. Find missing OR out-of-sync transactions
            to_sync = []
            for tid, pg_tx in pg_tx_map.items():
                if tid not in ch_status_map:
                    to_sync.append((pg_tx, "missing"))
                elif pg_tx.status != ch_status_map[tid]:
                    to_sync.append((pg_tx, "status_mismatch"))
            
            if not to_sync:
                logger.info(f"Sync check complete. All {len(pg_ids)} recent transactions are consistent in ClickHouse.")
                return

            logger.warning(f"Found {len(to_sync)} transactions needing sync (missing or status mismatch). Queuing...")

            # 4. Create Outbox entries for syncing
            for tx, reason in to_sync:
                event_type = "transaction.created" if reason == "missing" else "transaction.status_update"
                
                payload = {
                    "transaction_id": str(tx.id),
                    "parent_id": str(tx.parent_id) if tx.parent_id else None,
                    "account_id": tx.account_id,
                    "amount": int(tx.amount),
                    "category": tx.category,
                    "merchant": tx.merchant,
                    "transaction_type": tx.transaction_type,
                    "transaction_side": tx.transaction_side,
                    "status": tx.status,
                    "timestamp": tx.created_at.isoformat() if tx.created_at else datetime.now(timezone.utc).isoformat(),
                    # Logic for sender/recipient
                    "sender_email": tx.merchant.replace("Received from ", "") if tx.transaction_type == "transfer" and tx.amount > 0 else None,
                    "recipient_email": tx.merchant.replace("Transfer to ", "") if tx.transaction_type == "transfer" and tx.amount < 0 else None
                }
                
                outbox_entry = Outbox(
                    event_type=event_type,
                    payload=payload,
                    status="pending"
                )
                db.add(outbox_entry)
                
            await db.commit()
            logger.info(f"Successfully queued {len(to_sync)} transactions to the outbox.")

        except Exception as e:
            logger.error(f"Error during sync check: {e}")
            # db rolls back automatically on error in async context manager

if __name__ == "__main__":
    logger.info(f"Sync checker initialized. Checking every {CHECK_INTERVAL_SECONDS} seconds.")
    # Allow services to start up
    time.sleep(10)
    while True:
        try:
            asyncio.run(run_sync_check())
        except Exception as e:
            logger.error(f"Fatal error in sync checker loop: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)
