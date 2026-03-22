from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from models.user import User, Subscription
from models.account import Account
from models.transaction import Transaction
from models.management import ScheduledPayment, Contact, Outbox
from clickhouse_utils import get_ch_client, CH_DB
from activity import emit_activity
from config import settings
import logging

logger = logging.getLogger(__name__)

async def compliance_delete_user(db: AsyncSession, admin_id: int, target_id: int) -> bool:
    """Compliance-grade user deletion with Postgres anonymization and ClickHouse purge."""
    user = (await db.execute(select(User).where(User.id == target_id))).scalars().first()
    if not user: return False

    acc_ids = (await db.execute(select(Account.id).where(Account.user_id == target_id))).scalars().all()
    
    emit_activity(db, admin_id, "security", "user_deleted", f"Admin deleted user {target_id}", {"email": user.email})

    if acc_ids:
        await db.execute(text("UPDATE transactions SET merchant='DELETED', commentary=NULL WHERE account_id = ANY(:ids)"), {"ids": list(acc_ids)})

    for table in ["scheduled_payments", "payment_requests", "contacts", "idempotency_keys", "accounts", "users"]:
        col = "user_id" if table not in ["payment_requests", "users"] else ("requester_id" if table == "payment_requests" else "id")
        await db.execute(text(f"DELETE FROM {table} WHERE {col} = :uid"), {"uid": target_id})

    try:
        ch = get_ch_client()
        if acc_ids: ch.command(f"ALTER TABLE {CH_DB}.transactions DELETE WHERE account_id IN ({','.join(map(str, acc_ids))})")
        ch.command(f"ALTER TABLE {CH_DB}.activity_events DELETE WHERE user_id = {target_id}")
    except Exception as e:
        logger.error(f"CH purge fail: {e}")

    await db.commit()
    return True

async def get_system_metrics(db: AsyncSession):
    """Gathers system metrics for health comparison."""
    pg_count = (await db.execute(select(func.count(Transaction.id)))).scalar()
    ch_count = get_ch_client().query(f"SELECT count() FROM {settings.CLICKHOUSE_DB}.transactions").result_rows[0][0]
    return {"postgres_count": pg_count, "clickhouse_count": ch_count, "delta": pg_count - ch_count}
