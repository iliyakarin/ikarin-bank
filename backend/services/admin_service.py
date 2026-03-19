from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from database import User, Account, Transaction
from clickhouse_utils import get_ch_client, CH_DB
from activity import emit_activity
import logging

logger = logging.getLogger(__name__)

async def compliance_delete_user(db: AsyncSession, admin_user_id: int, target_user_id: int) -> bool:
    """
    Performs a compliance-grade deletion of a user.
    Anonymizes Postgres transactions and purges data from ClickHouse.
    """
    # 1. Verify User Exists
    result = await db.execute(select(User).filter(User.id == target_user_id))
    target_user = result.scalars().first()
    if not target_user:
        return False

    # 2. Collect accounts for ClickHouse purge
    result = await db.execute(select(Account.id).filter(Account.user_id == target_user_id))
    account_ids = [acc_id for acc_id in result.scalars().all()]

    # 3. Emit Audit Event BEFORE deletion
    emit_activity(
        db,
        admin_user_id,
        "security",
        "user_deleted",
        f"Admin deleted user ID {target_user_id}",
        {"target_user_id": target_user_id, "target_user_email": target_user.email},
        ip=None,
        user_agent=None
    )

    # 4. Anonymize Postgres Transactions
    if account_ids:
        await db.execute(
            text("""
                UPDATE transactions
                SET merchant = 'DELETED_USER',
                    commentary = NULL,
                    ip_address = NULL,
                    user_agent = NULL
                WHERE account_id = ANY(:account_ids)
            """),
            {"account_ids": account_ids}
        )

    # 5. Manual Cascade Deletion
    await db.execute(text("DELETE FROM scheduled_payments WHERE user_id = :uid"), {"uid": target_user_id})
    await db.execute(text("DELETE FROM payment_requests WHERE requester_id = :uid"), {"uid": target_user_id})
    await db.execute(text("DELETE FROM contacts WHERE user_id = :uid"), {"uid": target_user_id})
    await db.execute(text("DELETE FROM idempotency_keys WHERE user_id = :uid"), {"uid": target_user_id})
    await db.execute(text("DELETE FROM accounts WHERE user_id = :uid"), {"uid": target_user_id})
    await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": target_user_id})

    # 6. ClickHouse Purge
    try:
        ch = get_ch_client()
        if account_ids:
            ch.command(f"ALTER TABLE {CH_DB}.transactions DELETE WHERE account_id IN ({','.join(map(str, account_ids))})")
        ch.command(f"ALTER TABLE {CH_DB}.activity_events DELETE WHERE user_id = {target_user_id}")
    except Exception as e:
        logger.error(f"ClickHouse purge failed for user {target_user_id}: {e}")

    await db.commit()
    return True

from config import settings

async def get_system_metrics(db: AsyncSession):
    """Gathers high-level system metrics from Postgres and ClickHouse."""
    # Postgres Transaction Count
    result = await db.execute(select(func.count(Transaction.id)))
    pg_count = result.scalar()

    # ClickHouse Transaction Count
    ch_client = get_ch_client()
    ch_result = ch_client.query(f"SELECT count() FROM {settings.CLICKHOUSE_DB}.transactions")
    ch_count = ch_result.result_rows[0][0]

    return {
        "postgres_count": pg_count,
        "clickhouse_count": ch_count,
        "delta": pg_count - ch_count
    }
