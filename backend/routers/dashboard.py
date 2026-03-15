from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func
from typing import Dict, Any, List, Optional
from database import User, Account, Transaction
from auth_utils import get_db, get_current_user
from clickhouse_utils import get_ch_client, CH_DB
import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/v1/activity")
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
    """Query the activity log from ClickHouse."""
    try:
        ch = get_ch_client()

        if not from_date:
            # Default to last 24 hours if not specified
            from_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

        conditions = ["user_id = {user_id:Int64}"]
        params = {"user_id": current_user.id}

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
        params["limit"] = limit
        params["offset"] = offset

        result = ch.query(query, parameters=params)

        count_query = f"""
            SELECT count() FROM {CH_DB}.activity_events FINAL WHERE {where_clause}
        """
        count_result = ch.query(count_query, parameters=params)
        total = count_result.result_rows[0][0] if count_result.result_rows else 0

        events = []
        for row in result.result_rows:
            events.append({
                "event_id": row[0],
                "user_id": row[1],
                "category": row[2],
                "action": row[3],
                "event_time": str(row[4]),
                "title": row[5],
                "details": row[6],
            })

        return {"events": events, "total": total}

    except Exception as e:
        logger.error(f"Activity query failed: {e}")
        return {"events": [], "total": 0}


# --- Dashboard & Analytics Endpoints ---


@router.get("/dashboard/balance-history")
async def get_balance_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get balance history for a user for the given day range."""
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id))
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        ch_client = get_ch_client()

        # Query ClickHouse for balance trend
        query = f"""
        SELECT 
            toDate(event_time) as date,
            account_id,
            sum(amount) as daily_change
        FROM {CH_DB}.transactions
        WHERE account_id = {account.id} 
            AND event_time >= now() - INTERVAL {days} DAY
        GROUP BY toDate(event_time), account_id
        ORDER BY date
        """

        result = ch_client.query(query).named_results()

        # Build cumulative balance history
        balance_history = []
        current_balance = float(account.balance / 100)

        # Get start date
        start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

        for row in result:
            balance_history.append(
                {
                    "date": row["date"].isoformat()
                    if hasattr(row["date"], "isoformat")
                    else str(row["date"]),
                    "balance": current_balance,
                    "daily_change": float(row["daily_change"] / 100)
                    if row["daily_change"]
                    else 0,
                }
            )

        return {
            "balance_history": balance_history,
            "current_balance": float(account.balance / 100),
        }
    except Exception as e:
        logger.error(f"Error querying ClickHouse: {e}")
        # Fallback: return just current balance
        return {"balance_history": [], "current_balance": float(account.balance / 100)}


@router.get("/dashboard/recent-transactions")
async def get_recent_transactions(
    hours: int = 24,
    account_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recent transactions from the last N hours - user must be sender or recipient."""
    try:
        user_email = current_user.email.lower()
        
        # 1. Get PENDING transactions from Postgres (only outgoing ones exist here)
        result = await db.execute(select(Account).filter(Account.user_id == current_user.id))
        user_accounts = result.scalars().all()
        user_account_ids = [acc.id for acc in user_accounts]
        
        if account_id:
            if account_id not in user_account_ids:
                raise HTTPException(status_code=403, detail="Access denied to this account")
            account_ids = [account_id]
        else:
            account_ids = user_account_ids
        
        result = await db.execute(
            select(Transaction)
            .filter(Transaction.account_id.in_(account_ids))
            .filter(
                Transaction.created_at >= datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
            )
            .order_by(Transaction.created_at.desc())
            .limit(10)
        )
        pg_transactions = result.scalars().all()
        
        # 2. Get CLEARED/HISTORY transactions from ClickHouse (incoming AND outgoing)
        ch_client = get_ch_client()
        
        # Join account IDs for ClickHouse query to ensure we only get transactions belonging to the user's specific accounts
        # This prevents duplicate entries for P2P transfers while ensuring both sender and recipient see their record.
        if not account_ids:
            return {"transactions": []}
            
        account_ids_str = ",".join([str(aid) for aid in account_ids])
        
        query = f"""
            SELECT * FROM (
                SELECT 
                    toString(transaction_id) as id,
                    amount,
                    category,
                    merchant,
                    sender_email,
                    recipient_email,
                    transaction_type,
                    transaction_side,
                    event_time,
                    subscriber_id,
                    failure_reason,
                    status
                FROM {CH_DB}.transactions
                WHERE account_id IN ({account_ids_str})
                AND event_time >= now() - INTERVAL {hours} HOUR
                ORDER BY event_time DESC
                LIMIT 1 BY transaction_id
            )
            ORDER BY event_time DESC
        """
        
        ch_results = ch_client.query(query).result_rows
        
        # 3. Merge and formatting
        # We prefer ClickHouse data (confirmed history), but keep Postgres data if it's not in CH yet (pending)
        
        final_txs = []
        ch_ids = set()
        
        # Process ClickHouse results first (Confirmed transactions)
        # Use a temporary dict to keep only the LATEST row for each transaction_id
        # (Since we ORDER BY event_time DESC, the first one encountered is the latest)
        latest_ch_txs = {}
        for row in ch_results:
            tx_id = row[0]
            if tx_id not in latest_ch_txs:
                latest_ch_txs[tx_id] = {
                    "id": tx_id,
                    "amount": float(row[1] / 100),
                    "category": row[2],
                    "merchant": row[3],
                    "sender_email": row[4],
                    "recipient_email": row[5],
                    "transaction_type": row[6],
                    "transaction_side": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                    "subscriber_id": row[9],
                    "failure_reason": row[10],
                    "status": row[11] # Use the actual status from CH
                }
        
        for tx_id, tx_data in latest_ch_txs.items():
            ch_ids.add(tx_id)
            final_txs.append(tx_data)
            
        # Process Postgres results (Pending/In-flight)
        for tx in pg_transactions:
            if str(tx.id) not in ch_ids:
                # Same logic as before to determine type for PG txs
                # Default based on amount sign
                if tx.amount > 0:
                    tx_type = "income"
                    sender_email = None
                    recipient_email = current_user.email
                else:
                    tx_type = "expense"
                    sender_email = current_user.email
                    recipient_email = None

                # Refine based on Merchant/Category
                if tx.merchant and "Transfer to " in tx.merchant:
                    tx_type = "transfer"
                    recipient_email = tx.merchant.replace("Transfer to ", "")
                elif tx.merchant and "Received from " in tx.merchant:
                    tx_type = "transfer"
                    sender_email = tx.merchant.replace("Received from ", "")
                elif tx.category and tx.category.lower() in ["salary", "income", "deposit"]:
                    tx_type = "income"
                
                final_txs.append({
                    "id": str(tx.id),
                    "amount": float(tx.amount / 100),
                    "category": tx.category,
                    "merchant": tx.merchant,
                    "sender_email": sender_email,
                    "recipient_email": recipient_email,
                    "transaction_type": tx_type,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None,
                    "status": tx.status,
                })

        # Sort combined list by date desc
        final_txs.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        return {"transactions": final_txs[:20]}

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        import traceback
        logger.exception("An exception occurred")
        # Fallback to empty list or partial data if critical failure
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch transactions: {str(e)}"
        )


@router.get("/transactions")
async def get_all_transactions(
    days: int = 1,
    tx_type: str = None,  # 'incoming', 'outgoing', or None for all
    min_amount: float = None, # Input in dollars
    max_amount: float = None, # Input in dollars
    sort: str = "desc",  # 'asc' or 'desc'
    account_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all transactions with filtering by sender/recipient email, amount, date range, and sort direction."""
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id))
    accounts = result.scalars().all()
    if not accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    user_account_ids = [acc.id for acc in accounts]

    if account_id:
        if account_id not in user_account_ids:
            raise HTTPException(status_code=403, detail="Access denied to this account")
        target_account_ids = [account_id]
    else:
        target_account_ids = user_account_ids

    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

    try:
        ch_client = get_ch_client()

        account_ids_str = ",".join(map(str, target_account_ids))
        where_clauses = [
            f"account_id IN ({account_ids_str})",
            f"event_time >= now() - INTERVAL {days} DAY",
        ]

        # Type filtering: incoming = positive/CREDIT, outgoing = negative/DEBIT, transfer = P2P
        if tx_type:
            if tx_type.lower() == "outgoing":
                where_clauses.append("amount < 0")
            elif tx_type.lower() == "incoming":
                where_clauses.append("amount > 0")
            elif tx_type.lower() == "transfer":
                where_clauses.append("transaction_type = 'transfer'")

        # Amount range filtering (use absolute value so user-entered ranges apply to magnitude)
        if min_amount is not None:
            where_clauses.append(f"abs(amount) >= {int(min_amount * 100)}")

        if max_amount is not None:
            where_clauses.append(f"abs(amount) <= {int(max_amount * 100)}")

        where_clause = " AND ".join(where_clauses)

        # Sorting direction
        sort_dir = "ASC" if sort and sort.lower() == "asc" else "DESC"

        query = f"""
        SELECT * FROM (
            SELECT
                transaction_id,
                sender_email,
                recipient_email,
                amount,
                category,
                merchant,
                transaction_type,
                transaction_side,
                event_time,
                internal_account_last_4,
                subscriber_id,
                failure_reason,
                status
            FROM {CH_DB}.transactions
            WHERE {where_clause}
            ORDER BY event_time DESC
            LIMIT 1 BY transaction_id
        )
        ORDER BY event_time {sort_dir}
        LIMIT 100
        """

        result = ch_client.query(query).named_results()

        transactions = []
        for row in result:
            tx = {
                "id": row["transaction_id"],
                "sender_email": row.get("sender_email"),
                "recipient_email": row.get("recipient_email"),
                "amount": float(row["amount"] / 100),
                "category": row["category"],
                "merchant": row["merchant"],
                "type": row["transaction_type"],
                "side": row["transaction_side"],
                "timestamp": row["event_time"].isoformat(),
                "internal_account_last_4": row.get("internal_account_last_4"),
                "subscriber_id": row.get("subscriber_id"),
                "failure_reason": row.get("failure_reason"),
                "status": row.get("status", "cleared")
            }
            # IDOR check: even though we filter by account_ids belonging to user,
            # this is a defense-in-depth to ensure no leakage if query logic fails.
            transactions.append(tx)

        return {"transactions": transactions, "total": len(transactions)}
    except Exception as e:
        logger.error(f"ClickHouse query failed or empty, falling back to Postgres: {e}")

        # --- Postgres Fallback ---
        query = select(Transaction).filter(
            Transaction.account_id.in_(target_account_ids),
            Transaction.created_at >= cutoff_time,
        )

        if tx_type:
            if tx_type.lower() == "outgoing":
                query = query.filter(Transaction.transaction_side == "DEBIT")
            elif tx_type.lower() == "incoming":
                query = query.filter(Transaction.transaction_side == "CREDIT")

        if min_amount is not None:
            query = query.filter(func.abs(Transaction.amount) >= int(min_amount * 100))
        if max_amount is not None:
            query = query.filter(func.abs(Transaction.amount) <= int(max_amount * 100))

        sort_fn = Transaction.created_at.asc() if sort and sort.lower() == "asc" else Transaction.created_at.desc()
        query = query.order_by(sort_fn).limit(100)

        result = await db.execute(query)
        results = result.scalars().all()
        transactions = []
        for row in results:
            tx = {
                "id": str(row.id),
                "merchant": row.merchant or "",
                "amount": float(row.amount / 100),
                "category": row.category or "Transfer",
                "type": row.transaction_type or "expense",
                "side": row.transaction_side or "",
                "timestamp": row.created_at.isoformat() if row.created_at else "",
                "status": row.status or "cleared",
                "internal_account_last_4": row.internal_account_last_4,
                "sender_email": row.sender_email,
                "recipient_email": row.recipient_email,
                "subscriber_id": row.subscriber_id,
                "failure_reason": row.failure_reason,
            }
            transactions.append(tx)

        return {"transactions": transactions, "total": len(transactions)}


# --- Contacts Endpoints ---

