from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, desc
from models.user import User
from models.account import Account
from models.transaction import Transaction
from clickhouse_utils import get_ch_client, execute_ch_query, execute_ch_command, CH_DB
from activity import emit_activity
from config import settings
import logging

logger = logging.getLogger(__name__)

async def compliance_delete_user(db: AsyncSession, admin_id: int, target_id: int) -> bool:
    """Compliance-grade user deletion with Postgres anonymization and ClickHouse purge."""
    user = (await db.execute(select(User).where(User.id == target_id))).scalars().first()
    if not user:
        return False

    acc_ids = (await db.execute(select(Account.id).where(Account.user_id == target_id))).scalars().all()
    
    emit_activity(db, admin_id, "security", "user_deleted", f"Admin deleted user {target_id}", {"email": user.email})

    if acc_ids:
        await db.execute(text("UPDATE transactions SET merchant='DELETED', commentary=NULL WHERE account_id = ANY(:ids)"), {"ids": list(acc_ids)})

    for table in ["scheduled_payments", "payment_requests", "contacts", "idempotency_keys", "accounts", "users"]:
        col = "user_id" if table not in ["payment_requests", "users"] else ("requester_id" if table == "payment_requests" else "id")
        await db.execute(text(f"DELETE FROM {table} WHERE {col} = :uid"), {"uid": target_id})

    try:
        if acc_ids:
            await execute_ch_command(
                f"ALTER TABLE {CH_DB}.transactions DELETE WHERE account_id IN :ids",
                parameters={"ids": list(acc_ids)},
                client_getter=get_ch_client,
            )
        await execute_ch_command(
            f"ALTER TABLE {CH_DB}.activity_events DELETE WHERE user_id = :uid",
            parameters={"uid": target_id},
            client_getter=get_ch_client,
        )
    except Exception as e:
        logger.error(f"CH purge fail: {e}")

    await db.commit()
    return True


async def get_system_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Gathers comprehensive real-time banking metrics for the Admin Mission Control."""
    # 1. Total Balance across all bank accounts in Postgres
    total_balance_res = (await db.execute(select(func.coalesce(func.sum(Account.balance), 0)))).scalar() or 0
    total_balance = int(total_balance_res)

    # 2. Active users count
    active_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # 3. User growth history (last 30 days)
    growth_stmt = (
        select(
            func.date(User.created_at).label("reg_date"),
            func.count(User.id).label("user_count")
        )
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at).asc())
    )
    growth_rows = (await db.execute(growth_stmt)).all()
    user_growth = [{"date": str(r[0]), "count": int(r[1])} for r in growth_rows]
    if not user_growth:
        user_growth = [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "count": active_users}]

    # 4. Postgres count for comparison
    pg_count = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0

    # 5. ClickHouse queries for volume, velocity, top transactions, and merchant stats
    total_volume_24h = 0
    tx_count_24h = 0
    top_transactions: List[Dict[str, Any]] = []
    hourly_volume_map: Dict[int, Dict[str, int]] = {i: {"count": 0, "total": 0} for i in range(24)}
    merchant_stats: List[Dict[str, Any]] = []
    ch_count = 0

    try:
        # Total ClickHouse record count
        ch_cnt_res = await execute_ch_query(f"SELECT count() FROM {CH_DB}.transactions", client_getter=get_ch_client)
        ch_count = ch_cnt_res.result_rows[0][0] if ch_cnt_res.result_rows else 0

        # 24H Volume and Count
        vol_24h_res = await execute_ch_query(
            f"SELECT count(), coalesce(sum(amount), 0) FROM {CH_DB}.transactions WHERE event_time >= now() - INTERVAL 24 HOUR",
            client_getter=get_ch_client,
        )
        if vol_24h_res.result_rows and vol_24h_res.result_rows[0][0] > 0:
            tx_count_24h = int(vol_24h_res.result_rows[0][0])
            total_volume_24h = int(vol_24h_res.result_rows[0][1])
        else:
            # Fallback to all-time if no transactions in last 24h
            all_vol_res = await execute_ch_query(
                f"SELECT count(), coalesce(sum(amount), 0) FROM {CH_DB}.transactions",
                client_getter=get_ch_client,
            )
            if all_vol_res.result_rows:
                tx_count_24h = int(all_vol_res.result_rows[0][0])
                total_volume_24h = int(all_vol_res.result_rows[0][1])

        # Top 10 High Value Transactions
        top_tx_res = await execute_ch_query(
            f"""SELECT toString(transaction_id), amount, merchant, category, 
                       toString(event_time), account_id, transaction_type, transaction_side, status
                FROM {CH_DB}.transactions 
                ORDER BY amount DESC 
                LIMIT 10""",
            client_getter=get_ch_client,
        )
        for row in (top_tx_res.result_rows or []):
            top_transactions.append({
                "id": str(row[0]),
                "amount": int(row[1]),
                "merchant": str(row[2] or "Transaction"),
                "category": str(row[3] or "general"),
                "created_at": str(row[4]),
                "account_id": int(row[5] or 0),
                "transaction_type": str(row[6] or "transfer"),
                "transaction_side": str(row[7] or "DEBIT"),
                "status": str(row[8] or "cleared"),
            })

        # Hourly Volume Breakdown (24 hours)
        hourly_res = await execute_ch_query(
            f"""SELECT toHour(event_time) as h, count(), coalesce(sum(amount), 0) 
                FROM {CH_DB}.transactions 
                GROUP BY h 
                ORDER BY h ASC""",
            client_getter=get_ch_client,
        )
        for row in (hourly_res.result_rows or []):
            hour = int(row[0])
            if 0 <= hour <= 23:
                hourly_volume_map[hour] = {"count": int(row[1]), "total": int(row[2])}

        # Top Merchants by Volume
        merchant_res = await execute_ch_query(
            f"""SELECT merchant, count() as cnt, coalesce(sum(amount), 0) as total 
                FROM {CH_DB}.transactions 
                WHERE merchant != '' AND merchant != 'DELETED'
                GROUP BY merchant 
                ORDER BY total DESC 
                LIMIT 5""",
            client_getter=get_ch_client,
        )
        for row in (merchant_res.result_rows or []):
            merchant_stats.append({
                "merchant": str(row[0]),
                "transaction_count": int(row[1]),
                "total_amount": int(row[2]),
            })

    except Exception as e:
        logger.error(f"Failed to fetch ClickHouse banking metrics: {e}")

    # Fallback to Postgres if ClickHouse returned no top transactions
    if not top_transactions and pg_count > 0:
        pg_top = (await db.execute(
            select(Transaction).order_by(desc(Transaction.amount)).limit(10)
        )).scalars().all()
        for t in pg_top:
            top_transactions.append({
                "id": str(t.id),
                "amount": int(t.amount),
                "merchant": t.merchant or "Transaction",
                "category": t.category or "general",
                "created_at": t.created_at.isoformat() if t.created_at else datetime.now(timezone.utc).isoformat(),
                "account_id": t.account_id,
                "transaction_type": t.transaction_type or "transfer",
                "transaction_side": t.transaction_side or "DEBIT",
                "status": t.status or "cleared",
            })

    hourly_volume = [{"hour": h, "count": hourly_volume_map[h]["count"], "total": hourly_volume_map[h]["total"]} for h in range(24)]
    avg_ticket_size = int(total_volume_24h / max(1, tx_count_24h)) if tx_count_24h > 0 else 0

    return {
        "totalVolume": total_volume_24h,
        "transactionCount": tx_count_24h,
        "totalBalance": total_balance,
        "activeUsers": active_users,
        "avgTransactionSize": avg_ticket_size,
        "topTransactions": top_transactions,
        "hourlyVolume": hourly_volume,
        "merchantStats": merchant_stats,
        "userGrowth": user_growth,
        "postgres_count": pg_count,
        "clickhouse_count": ch_count,
        "delta": pg_count - ch_count,
    }


async def get_all_transactions_for_admin(
    db: AsyncSession,
    days: int = 30,
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Retrieves paginated bank-wide transactions for admin auditing."""
    params: Dict[str, Any] = {"days": days, "limit": limit, "offset": offset}
    where_clauses = ["event_time >= now() - INTERVAL :days DAY"]

    if search:
        where_clauses.append("(merchant ILIKE :search OR sender_email ILIKE :search OR recipient_email ILIKE :search OR toString(transaction_id) ILIKE :search)")
        params["search"] = f"%{search}%"
    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT toString(transaction_id) as tx_id, account_id, sender_email, recipient_email,
               amount, category, merchant, transaction_type, transaction_side,
               toString(event_time) as event_time, status, internal_account_last_4, subscriber_id
        FROM {CH_DB}.transactions
        WHERE {where_sql}
        ORDER BY event_time DESC
        LIMIT :limit OFFSET :offset
    """

    count_query = f"""
        SELECT count() FROM {CH_DB}.transactions WHERE {where_sql}
    """

    transactions = []
    total = 0

    try:
        res = await execute_ch_query(query, parameters=params, client_getter=get_ch_client)
        cnt_res = await execute_ch_query(count_query, parameters=params, client_getter=get_ch_client)
        total = cnt_res.result_rows[0][0] if cnt_res.result_rows else 0

        for row in (res.result_rows or []):
            transactions.append({
                "id": str(row[0]),
                "account_id": int(row[1]),
                "sender_email": str(row[2] or ""),
                "recipient_email": str(row[3] or ""),
                "amount": int(row[4]),
                "category": str(row[5] or "general"),
                "merchant": str(row[6] or "Transaction"),
                "transaction_type": str(row[7] or "transfer"),
                "transaction_side": str(row[8] or "DEBIT"),
                "event_time": str(row[9]),
                "status": str(row[10] or "cleared"),
                "internal_account_last_4": str(row[11] or ""),
                "subscriber_id": str(row[12] or ""),
            })
    except Exception as e:
        logger.error(f"ClickHouse admin transactions query failed: {e}")
        # Fallback to Postgres
        stmt = select(Transaction).order_by(desc(Transaction.created_at)).limit(limit).offset(offset)
        pg_txs = (await db.execute(stmt)).scalars().all()
        total = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0
        for t in pg_txs:
            transactions.append({
                "id": str(t.id),
                "account_id": t.account_id,
                "sender_email": t.sender_email or "",
                "recipient_email": t.recipient_email or "",
                "amount": int(t.amount),
                "category": t.category or "general",
                "merchant": t.merchant or "Transaction",
                "transaction_type": t.transaction_type or "transfer",
                "transaction_side": t.transaction_side or "DEBIT",
                "event_time": t.created_at.isoformat() if t.created_at else "",
                "status": t.status or "cleared",
                "internal_account_last_4": t.internal_account_last_4 or "",
                "subscriber_id": t.subscriber_id or "",
            })

    return {"transactions": transactions, "total": total}
