"""Dashboard Data Router.

This module provides endpoints for fetching user-specific dashboard data,
including balances, recent transactions, and activity trends.
"""
import datetime
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import SessionLocal
from models.user import User
from models.account import Account
from auth_utils import get_db, get_current_user
from clickhouse_utils import get_ch_client, CH_DB
from schemas.dashboard import DashboardMetrics, RecentTransaction, ChartDataPoint
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

@router.get("/summary", response_model=DashboardMetrics)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve summarized financial metrics for the user."""
    # 1. Total Balance
    result = await db.execute(select(func.sum(Account.balance)).where(Account.user_id == current_user.id))
    total_balance = result.scalar() or 0

    # 2. Monthly Spending/Income (from ClickHouse)
    ch = get_ch_client()
    now = datetime.datetime.now(datetime.timezone.utc)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - datetime.timedelta(days=1)).replace(day=1)

    # Simplified mock/placeholder for complex metrics until further logic added
    return DashboardMetrics(
        total_balance=total_balance,
        monthly_spending=0,
        monthly_income=0,
        spending_change_pct=0.0,
        income_change_pct=0.0,
        recent_transactions=[],
        chart_data=[],
        category_distribution={}
    )

@router.get("/activity")
async def get_activity(
    category: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    search: Optional[str] = None,
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """Query the activity log from ClickHouse with Final deduplication."""
    try:
        ch = get_ch_client()
        params = {"user_id": current_user.id, "limit": limit, "offset": offset}
        conditions = ["user_id = {user_id:Int64}"]

        if category:
            conditions.append("category = {category:String}")
            params["category"] = category
        if from_date:
            conditions.append("event_time >= {from_date:String}")
            params["from_date"] = from_date
        if to_date:
            conditions.append("event_time <= {to_date:String}")
            params["to_date"] = to_date
        if search:
            conditions.append("(title ILIKE {search:String} OR details ILIKE {search:String})")
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(conditions)
        sort_dir = "ASC" if order == "asc" else "DESC"

        query = f"""
            SELECT event_id, user_id, category, action, event_time, title, details
            FROM {CH_DB}.activity_events FINAL
            WHERE {where_clause}
            ORDER BY event_time {sort_dir}
            LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
        """
        result = ch.query(query, parameters=params)
        
        count_res = ch.query(f"SELECT count() FROM {CH_DB}.activity_events FINAL WHERE {where_clause}", parameters=params)
        total = count_res.result_rows[0][0] if count_res.result_rows else 0

        events = [
            {
                "event_id": row[0], "user_id": row[1], "category": row[2],
                "action": row[3], "event_time": str(row[4]), "title": row[5], "details": row[6]
            } for row in result.result_rows
        ]
        return {"events": events, "total": total}
    except Exception as e:
        logger.error(f"Activity query failed: {e}")
        return {"events": [], "total": 0}

@router.get("/dashboard/balance-history")
async def get_balance_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get balance history trend for the user."""
    account = (await db.execute(select(Account).where(Account.user_id == current_user.id))).scalars().first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    try:
        ch = get_ch_client()
        # Use parametrized interval if possible, or f-string for now as days is trusted int
        query = f"""
            SELECT toDate(event_time) as date, sum(amount) as daily_change
            FROM {CH_DB}.transactions
            WHERE account_id = {account.id} AND event_time >= now() - INTERVAL {days} DAY
            GROUP BY toDate(event_time) ORDER BY date
        """
        result = ch.query(query).named_results()
        
        # Build history (simplified)
        history = [{"date": str(row["date"]), "daily_change": int(row["daily_change"])} for row in result]
        return {"balance_history": history, "current_balance": int(account.balance)}
    except Exception as e:
        logger.error(f"Balance history CH failed: {e}")
        return {"balance_history": [], "current_balance": int(account.balance)}

@router.get("/recent-transactions")
async def get_recent_transactions(
    hours: int = 24,
    account_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve transactions from ClickHouse ONLY."""
    accounts = (await db.execute(select(Account).where(Account.user_id == current_user.id))).scalars().all()
    user_account_ids = [acc.id for acc in accounts]

    if account_id:
        if account_id not in user_account_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        target_ids = [account_id]
    else:
        target_ids = user_account_ids

    if not target_ids:
         return {"transactions": []}

    # ClickHouse ONLY
    final_txs = []
    try:
        ids_str = ",".join(map(str, target_ids))
        ch = get_ch_client()
        query = f"""
            SELECT toString(transaction_id), amount, category, merchant, transaction_type, transaction_side, event_time, status
            FROM {CH_DB}.transactions WHERE account_id IN ({ids_str}) AND event_time >= now() - INTERVAL {hours} HOUR
            ORDER BY event_time DESC LIMIT 1 BY transaction_id
        """
        ch_rows = ch.query(query).named_results()
        for row in ch_rows:
            final_txs.append({
                "id": row["toString(transaction_id)"], "amount": int(row["amount"]),
                "category": row["category"], "merchant": row["merchant"],
                "transaction_type": row["transaction_type"], "transaction_side": row["transaction_side"],
                "created_at": str(row["event_time"]), "status": row["status"]
            })
    except Exception as e:
        logger.error(f"CH recent failed: {e}")

    final_txs.sort(key=lambda x: x["created_at"], reverse=True)
    return {"transactions": final_txs[:20]}

@router.get("/transactions")
async def get_transactions(
    days: int = Query(7, ge=1),
    tx_type: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    sort: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve filtered transaction history for the user from ClickHouse ONLY."""
    logger.info(f"🔍 [DASHBOARD] Fetching transactions for user {current_user.id} ({current_user.email}) from ClickHouse")
    
    # Still need Postgres for account IDs (metadata)
    acc_stmt = select(Account.id).where(Account.user_id == current_user.id)
    account_ids = (await db.execute(acc_stmt)).scalars().all()
    
    if not account_ids:
        return {"transactions": []}

    try:
        ch = get_ch_client()
        ids_str = ",".join(map(str, account_ids))
        
        conditions = [f"account_id IN ({ids_str})", f"event_time >= now() - INTERVAL {days} DAY"]
        
        if tx_type == "incoming":
            conditions.append("amount > 0")
        elif tx_type == "outgoing":
            conditions.append("amount < 0")
            
        if min_amount is not None:
            conditions.append(f"abs(amount) >= {min_amount * 100}")
        if max_amount is not None:
            conditions.append(f"abs(amount) <= {max_amount * 100}")
            
        where_clause = " AND ".join(conditions)
        sort_dir = "ASC" if sort.lower() == "asc" else "DESC"
        
        query = f"""
            SELECT toString(transaction_id) as tx_id, sender_email, recipient_email, amount, category, merchant, event_time, status, transaction_type
            FROM {CH_DB}.transactions
            WHERE {where_clause}
            ORDER BY event_time {sort_dir}
            LIMIT 1 BY transaction_id
        """
        ch_rows = ch.query(query).named_results()
        
        return {
            "transactions": [
                {
                    "id": row["tx_id"],
                    "sender_email": row["sender_email"],
                    "recipient_email": row["recipient_email"],
                    "amount": int(row["amount"]),
                    "category": row["category"],
                    "merchant": row["merchant"],
                    "timestamp": row["event_time"].isoformat() if hasattr(row["event_time"], 'isoformat') else str(row["event_time"]),
                    "status": row["status"],
                    "transaction_type": row["transaction_type"]
                } for row in ch_rows
            ]
        }
    except Exception as e:
        logger.error(f"CH transactions failed: {e}")
        return {"transactions": []}

