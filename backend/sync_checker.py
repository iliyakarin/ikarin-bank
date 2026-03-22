import time
import logging
from datetime import datetime, timezone, timedelta
import asyncio
import clickhouse_connect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select
from database import Transaction, Outbox
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 86400

async def run_sync_check():
    logger.info("Checking Postgres <-> ClickHouse Sync...")
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(engine) as db:
        try:
            ch = clickhouse_connect.get_client(host=settings.CLICKHOUSE_HOST, port=settings.CLICKHOUSE_PORT, username=settings.CLICKHOUSE_USER, password=settings.CLICKHOUSE_PASSWORD)
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            pg_txs = (await db.execute(select(Transaction).where(Transaction.created_at >= cutoff))).scalars().all()
            if not pg_txs: return

            pg_map = {str(tx.id): tx for tx in pg_txs}
            pg_ids = list(pg_map.keys())
            ch_status = {}
            for i in range(0, len(pg_ids), 1000):
                chunk = pg_ids[i:i+1000]
                res = ch.query(f"SELECT toString(transaction_id), status FROM {settings.CLICKHOUSE_DB}.transactions WHERE transaction_id IN {{ids:Array(String)}} ORDER BY event_time DESC", parameters={'ids': chunk}).result_rows
                for row in res:
                    if row[0] not in ch_status: ch_status[row[0]] = row[1]

            to_sync = []
            for tid, tx in pg_map.items():
                if tid not in ch_status: to_sync.append((tx, "transaction.created"))
                elif tx.status != ch_status[tid]: to_sync.append((tx, "transaction.status_update"))

            if not to_sync:
                logger.info("Sync verified.")
                return

            for tx, etype in to_sync:
                db.add(Outbox(event_type=etype, payload={
                    "transaction_id": str(tx.id), "parent_id": str(tx.parent_id) if tx.parent_id else None,
                    "account_id": tx.account_id, "amount": int(tx.amount), "category": tx.category,
                    "merchant": tx.merchant, "transaction_type": tx.transaction_type, "transaction_side": tx.transaction_side,
                    "status": tx.status, "timestamp": tx.created_at.isoformat()
                }))
            await db.commit()
            logger.info(f"Queued {len(to_sync)} sync events.")
        except Exception as e: logger.error(f"Sync error: {e}")

async def main():
    while True:
        await run_sync_check()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
