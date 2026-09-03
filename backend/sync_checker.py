import time
import logging
from datetime import datetime, timezone, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Transaction, Outbox, engine
from config import settings
from clickhouse_utils import execute_ch_query
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 86400  # 24 hours in seconds

async def auto_settle_transactions(db: AsyncSession):
    """Auto-settle pending/processing transactions older than 45 seconds into 'cleared'."""
    try:
        settle_cutoff = datetime.now(timezone.utc) - timedelta(seconds=45)
        stmt = select(Transaction).where(
            Transaction.status.in_(["pending", "processing", "sent_to_kafka", "in_progress"]),
            Transaction.created_at <= settle_cutoff
        )
        txs = (await db.execute(stmt)).scalars().all()
        if not txs:
            return

        for tx in txs:
            tx.status = "cleared"
            db.add(Outbox(event_type="transaction.status_update", payload={
                "transaction_id": str(tx.id),
                "parent_id": str(tx.parent_id) if tx.parent_id else None,
                "account_id": tx.account_id,
                "amount": int(tx.amount),
                "category": tx.category,
                "merchant": tx.merchant,
                "transaction_type": tx.transaction_type,
                "transaction_side": tx.transaction_side,
                "status": "cleared",
                "timestamp": tx.created_at.isoformat()
            }))
        await db.commit()
        logger.info(f"Auto-settled {len(txs)} transactions to 'cleared'.")
    except Exception as e:
        logger.error(f"Auto-settle error: {e}")

async def run_sync_check():
    logger.info("Checking Postgres <-> ClickHouse Sync...")
    async with AsyncSession(engine) as db:
        try:
            await auto_settle_transactions(db)
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            pg_txs = (await db.execute(select(Transaction).where(Transaction.created_at >= cutoff))).scalars().all()
            if not pg_txs: return

            pg_map = {str(tx.id): tx for tx in pg_txs}
            pg_ids = list(pg_map.keys())
            ch_status = {}
            for i in range(0, len(pg_ids), 1000):
                chunk = pg_ids[i:i+1000]
                query_res = await execute_ch_query(
                    f"SELECT toString(transaction_id), status FROM {settings.CLICKHOUSE_DB}.transactions WHERE transaction_id IN {{ids:Array(String)}} ORDER BY event_time DESC",
                    parameters={'ids': chunk}
                )
                for row in query_res.result_rows:
                    if row[0] not in ch_status: ch_status[row[0]] = row[1]

            to_sync = []
            for tid, tx in pg_map.items():
                effective_status = "cleared" if tx.status in ("cleared", "settled", "sent_to_kafka") else tx.status
                if tid not in ch_status:
                    to_sync.append((tx, "transaction.created", effective_status))
                elif effective_status != ch_status[tid]:
                    to_sync.append((tx, "transaction.status_update", effective_status))

            if not to_sync:
                logger.info("Sync verified.")
                return

            for tx, etype, eff_status in to_sync:
                db.add(Outbox(event_type=etype, payload={
                    "transaction_id": str(tx.id), "parent_id": str(tx.parent_id) if tx.parent_id else None,
                    "account_id": tx.account_id, "amount": int(tx.amount), "category": tx.category,
                    "merchant": tx.merchant, "transaction_type": tx.transaction_type, "transaction_side": tx.transaction_side,
                    "status": eff_status, "timestamp": tx.created_at.isoformat()
                }))
            await db.commit()
            logger.info(f"Queued {len(to_sync)} sync events.")
        except Exception as e: logger.error(f"Sync error: {e}")

async def main():
    while True:
        Path("/tmp/heartbeat.txt").touch(exist_ok=True)
        await run_sync_check()
        for _ in range(max(1, CHECK_INTERVAL // 15)):
            await asyncio.sleep(15)
            Path("/tmp/heartbeat.txt").touch(exist_ok=True)
            async with AsyncSession(engine) as db:
                await auto_settle_transactions(db)

if __name__ == "__main__":
    asyncio.run(main())
