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
from clickhouse_utils import execute_ch_query, CH_DB
from clickhouse_queries import (
    build_balance_history_query,
    build_recent_transactions_query,
    build_transactions_query,
)
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
        result = await execute_ch_query(query, parameters=params)
        
        count_res = await execute_ch_query(f"SELECT count() FROM {CH_DB}.activity_events FINAL WHERE {where_clause}", parameters=params)
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
        query, params = build_balance_history_query(CH_DB, account.id, days)
        ch_res = await execute_ch_query(query, parameters=params)
        result = ch_res.named_results()
        
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
        query, params = build_recent_transactions_query(CH_DB, target_ids, hours)
        ch_res = await execute_ch_query(query, parameters=params)
        ch_rows = ch_res.named_results()
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
        query, params = build_transactions_query(
            CH_DB, list(account_ids), days,
            tx_type=tx_type, min_amount=min_amount,
            max_amount=max_amount, sort=sort,
        )
        ch_res = await execute_ch_query(query, parameters=params)
        ch_rows = ch_res.named_results()
        
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

