"""Security Checks: Velocity Limiting & Anomaly Detection."""
import datetime
from datetime import timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import Transaction, Account
from activity import emit_activity
from money_utils import from_cents
import logging
from clickhouse_utils import get_ch_client, CH_DB

logger = logging.getLogger(__name__)

VELOCITY_MAX_TX_PER_MINUTE = 10
ANOMALY_MULTIPLIER = 5.0

async def check_velocity(db: AsyncSession, user_id: int) -> bool:
    """Check if user is sending too many transactions in the last minute."""
    one_min_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)
    acc_ids = (await db.execute(select(Account.id).where(Account.user_id == user_id))).scalars().all()
    if not acc_ids: return True

    count = (await db.execute(select(func.count(Transaction.id)).where(
        Transaction.account_id.in_(acc_ids),
        Transaction.transaction_side == "DEBIT",
        Transaction.created_at >= one_min_ago,
    ))).scalar() or 0

    if count >= VELOCITY_MAX_TX_PER_MINUTE:
        emit_activity(db, user_id, "security", "velocity_alert", f"⚡ High velocity: {count} tx/min", {"count": count, "limit": VELOCITY_MAX_TX_PER_MINUTE})
        await db.commit()
        return False
    return True

async def check_anomaly(db: AsyncSession, user_id: int, amount: int) -> bool:
    """Check if transaction amount is anomalously large via ClickHouse history."""
    try:
        acc_ids = (await db.execute(select(Account.id).where(Account.user_id == user_id))).scalars().all()
        if not acc_ids: return False

        ch = get_ch_client()
        res = ch.query(f"SELECT avg(abs(amount)), count() FROM {CH_DB}.transactions FINAL WHERE account_id IN {{ids:Array(Int64)}} AND event_time >= now() - INTERVAL 90 DAY", parameters={'ids': acc_ids})
        if not res.result_rows or res.result_rows[0][1] < 5: return False

        avg_val = int(res.result_rows[0][0])
        if avg_val > 0 and amount >= avg_val * ANOMALY_MULTIPLIER:
            emit_activity(db, user_id, "security", "anomaly_alert", f"🔍 Unusual amount: {from_cents(amount)} (avg: {from_cents(avg_val)})", {"amount": amount, "average": avg_val})
            return True
        return False
    except Exception as e:
        logger.warning(f"Anomaly check fail: {e}")
        return False
