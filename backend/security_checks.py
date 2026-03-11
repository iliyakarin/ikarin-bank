"""
Security Checks: Velocity Limiting & Anomaly Detection
Called before P2P transfers to protect against suspicious activity.
"""
import datetime
from datetime import timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import Transaction, Account
from activity import emit_activity
import os
import logging
from clickhouse_utils import get_ch_client, CH_DB

logger = logging.getLogger(__name__)

# Limits
VELOCITY_MAX_TX_PER_MINUTE = 10
ANOMALY_MULTIPLIER = 5.0


async def check_velocity(db: AsyncSession, user_id: int) -> bool:
    """
    Check if user is sending too many transactions in the last minute.
    Returns True if the user is within limits, raises HTTPException if not.
    """
    one_minute_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)

    # Get all account IDs for this user
    result = await db.execute(select(Account.id).filter(Account.user_id == user_id))
    account_ids = [a for a in result.scalars().all()]

    if not account_ids:
        return True

    # Count recent outgoing transactions across all user accounts
    result = await db.execute(
        select(func.count(Transaction.id))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_side == "DEBIT",
            Transaction.created_at >= one_minute_ago,
        )
    )
    recent_count = result.scalar() or 0

    if recent_count >= VELOCITY_MAX_TX_PER_MINUTE:
        # Log the security event
        emit_activity(
            db,
            user_id,
            "security",
            "velocity_alert",
            f"⚡ High velocity: {recent_count} transactions in 1 minute",
            {
                "count": recent_count,
                "limit": VELOCITY_MAX_TX_PER_MINUTE,
                "window": "1 minute",
            },
        )
        await db.commit()
        return False

    return True

async def check_anomaly(db: AsyncSession, user_id: int, amount: Decimal) -> bool:
    """
    Check if a transaction amount is anomalously large compared to user's history.
    Queries ClickHouse for 90-day average. Returns True if flagged as anomaly.
    Does NOT block the transaction — only flags it in the activity log.
    """
    try:
        ch = get_ch_client()

        # Get user's account IDs for the query
        result = await db.execute(select(Account.id).filter(Account.user_id == user_id))
        account_ids = [a for a in result.scalars().all()]

        if not account_ids:
            return False

        ids_str = ",".join(str(i) for i in account_ids)

        result = ch.query(
            f"""
            SELECT
                avg(abs(amount)) as avg_amount,
                stddevPop(abs(amount)) as std_amount,
                count() as tx_count
            FROM {CH_DB}.transactions FINAL
            WHERE account_id IN ({ids_str})
              AND event_time >= now() - INTERVAL 90 DAY
            """
        )

        if not result.result_rows or result.result_rows[0][2] < 5:
            # Not enough history to compute meaningful average
            return False

        avg_amount = float(result.result_rows[0][0])
        tx_count = result.result_rows[0][2]

        if avg_amount <= 0:
            return False

        # Flag if amount is 5× or more the average
        if float(amount) >= avg_amount * ANOMALY_MULTIPLIER:
            emit_activity(
                db,
                user_id,
                "security",
                "anomaly_alert",
                f"🔍 Unusual amount: ${float(amount):.2f} (avg: ${avg_amount:.2f})",
                {
                    "amount": float(amount),
                    "average": round(avg_amount, 2),
                    "multiplier": round(float(amount) / avg_amount, 1),
                    "history_count": tx_count,
                },
            )
            # Don't commit — caller will commit with the transaction
            return True

        return False

    except Exception as e:
        logger.warning(f"Anomaly check failed (non-blocking): {e}")
        return False
