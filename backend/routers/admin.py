"""Administrative Management Router.

This module provides restricted endpoints for system monitoring, user management,
compliance operations, and data analytics across Postgres and ClickHouse.
"""
import asyncio
import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer, KafkaException
import clickhouse_connect

from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction
from models.management import Outbox
from schemas.users import UserResponse
from schemas.admin import SimulationRequest, QueryRequest, AdminCreditRequest
from auth_utils import get_db, get_current_user, RoleChecker
from clickhouse_utils import get_ch_client, execute_ch_query, CH_DB
from activity import emit_activity
from sync_checker import run_sync_check
from config import settings
from services.admin_service import compliance_delete_user, get_system_metrics
from services.event_emitter import emit_transactional_event
from idempotency import check_idempotency, complete_idempotency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_only = RoleChecker(["admin"])

@router.post("/credit")
async def admin_credit_account(
    payload: AdminCreditRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    """Credits a user's main account from outside the ledger.

    For demo/simulation use (e.g. payroll deposits): records an inbound
    transaction with no debiting counterparty, mirroring how
    services/transfer_service.py mutates balance directly before logging via
    emit_transactional_event.
    """
    if payload.idempotency_key:
        saved = await check_idempotency(db, payload.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    target = (await db.execute(select(User).where(User.email == payload.recipient_email))).scalars().first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    account = (await db.execute(
        select(Account).where(Account.user_id == target.id, Account.is_main == True)
    )).scalars().first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient has no main account")

    account.balance += payload.amount

    client_ip = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")
    idem_key = payload.idempotency_key or str(uuid.uuid4())

    tx_id = await emit_transactional_event(
        db=db,
        user_id=target.id,
        account_id=account.id,
        amount=payload.amount,
        category=payload.category,
        merchant=payload.source_name,
        transaction_type="deposit",
        transaction_side="CREDIT",
        sender_email=payload.source_name,
        recipient_email=target.email,
        internal_account_last_4=account.account_number_last_4,
        event_type="transaction.created",
        idempotency_key=idem_key,
        commentary=payload.commentary,
        ip_address=client_ip,
        user_agent=user_agent,
        status="cleared",
        activity_category="deposit",
        activity_action="received",
    )

    response_body = {"status": "success", "transaction_id": tx_id}
    if payload.idempotency_key:
        await complete_idempotency(db, payload.idempotency_key, response_body)

    await db.commit()
    return response_body

# --- PII Masking Helpers ---
def mask_email(email: str) -> str:
    if not email or "@" not in email: return email
    user, domain = email.split("@")
    if len(user) <= 1: return f"*@{domain}"
    return f"{user[0]}***@{domain}"

def mask_name(name: str) -> str:
    if not name: return name
    parts = name.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 1: masked_parts.append("*")
        else: masked_parts.append(f"{part[0]}***")
    return " ".join(masked_parts)

PREDEFINED_QUERIES = {
    "clickhouse": {
        "get_recent_transactions": f"SELECT * FROM {settings.CLICKHOUSE_DB}.transactions ORDER BY event_time DESC LIMIT :limit",
        "get_transaction_trace": f"SELECT transaction_id, event_time FROM {settings.CLICKHOUSE_DB}.transactions WHERE transaction_id IN :tx_ids",
        "get_activity_log": f"SELECT * FROM {settings.CLICKHOUSE_DB}.activity_events WHERE user_id = :user_id ORDER BY event_time DESC LIMIT :limit",
    },
    "postgres": {
        "get_recent_transactions": "SELECT * FROM transactions ORDER BY created_at DESC LIMIT :limit",
        "get_user_details": "SELECT id, email, first_name, last_name, role, created_at FROM users WHERE id = :user_id",
        "get_account_details": "SELECT id, user_id, name, balance, account_uuid FROM accounts WHERE id = :account_id",
    }
}

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    """Retrieves high-level system statistics and health metrics.

    Args:
        db (AsyncSession): The database session.
        current_user (User): The authenticated admin user.

    Returns:
        dict: Stats including transaction counts, Kafka lag, and sync status.
    """
    pg_count = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0
    ch_result = await execute_ch_query(f"SELECT count() FROM {settings.CLICKHOUSE_DB}.transactions", client_getter=get_ch_client)
    ch_count = ch_result.result_rows[0][0] if ch_result.result_rows else 0
    lag = -1
    try:
        admin = AdminClient({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
        metadata = admin.list_topics(timeout=10)
        if settings.KAFKA_TOPIC in metadata.topics: lag = 0
    except Exception as e: logger.error(f"Kafka metadata error: {e}")
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    volume_cents = (await db.execute(select(func.sum(Transaction.amount)).where(Transaction.category == "P2P", Transaction.created_at >= yesterday))).scalar() or 0
    return {"postgres_count": pg_count, "clickhouse_count": ch_count, "delta": pg_count - ch_count, "kafka_lag": lag, "system_volume": int(volume_cents), "sync_health": "in_sync" if (pg_count - ch_count) < 5 else "syncing", "status": "healthy" if lag >= 0 else "degraded"}

@router.get("/users", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    result = await db.execute(select(User).order_by(User.id.desc()).offset(skip).limit(limit))
    users = result.scalars().all()
    for user in users:
        user.email = mask_email(user.email)
        user.backup_email = mask_email(user.backup_email) if user.backup_email else None
        user.first_name = mask_name(user.first_name)
        user.last_name = mask_name(user.last_name)
    return users

@router.get("/users/search", response_model=UserResponse)
async def search_user_by_email(email: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    user = (await db.execute(select(User).where(User.email == email))).scalars().first()
    if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.email = mask_email(user.email)
    user.backup_email = mask_email(user.backup_email) if user.backup_email else None
    user.first_name = mask_name(user.first_name)
    user.last_name = mask_name(user.last_name)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    """Deletes a user and their associated data for compliance.

    Args:
        user_id (int): The ID of the user to delete.
        db (AsyncSession): The database session.
        current_user (User): The authenticated admin user.

    Returns:
        Response: A 204 No Content response.

    Raises:
        HTTPException: If the user is not found.
    """
    if not await compliance_delete_user(db, current_user.id, user_id): raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/traces")
async def get_traces(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    pg_txs = (await db.execute(select(Transaction).order_by(Transaction.created_at.desc()).limit(20))).scalars().all()
    tx_ids = [tx.id for tx in pg_txs]
    ch_map = {}
    try:
        query = f"SELECT transaction_id, event_time FROM {settings.CLICKHOUSE_DB}.transactions WHERE transaction_id IN :tx_ids"
        ch_res = await execute_ch_query(query, parameters={'tx_ids': tx_ids}, client_getter=get_ch_client)
        ch_txs = ch_res.named_results()
        ch_map = {row["transaction_id"]: row["event_time"] for row in ch_txs}
    except Exception as e: logger.warning(f"ClickHouse trace failed: {e}")
    traces = []
    for tx in pg_txs:
        ch_time = ch_map.get(tx.id)
        traces.append({"id": tx.id, "merchant": tx.merchant, "postgres_at": tx.created_at.isoformat(), "clickhouse_at": ch_time.isoformat() if ch_time else None, "latency": (ch_time - tx.created_at).total_seconds() * 1000 if ch_time else None, "status": "cleared" if ch_time else tx.status})
    return traces

@router.post("/simulate")
async def simulate_traffic(req: SimulationRequest, background_tasks: BackgroundTasks, current_user: User = Depends(admin_only)):
    background_tasks.add_task(run_simulation, req.tps, req.count)
    return {"status": "simulation_started", "tps": req.tps, "total": req.count}

async def run_simulation(tps: int, count: int):
    delay = 1.0 / tps
    for i in range(count):
        async with SessionLocal() as db:
            try:
                tx_id = str(uuid.uuid4())
                new_tx = Transaction(id=tx_id, account_id=1, amount=1000, category="Simulation", merchant=f"Bot-{i}", status="sent_to_kafka", transaction_side="DEBIT")
                db.add(new_tx)
                await db.commit()
            except Exception as e: logger.error(f"Sim error: {e}")
        await asyncio.sleep(delay)

@router.get("/postgres-logs")
async def get_postgres_logs(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    txs = (await db.execute(select(Transaction).order_by(Transaction.created_at.desc()).limit(10))).scalars().all()
    return txs

@router.get("/clickhouse-logs")
async def get_ch_logs(current_user: User = Depends(admin_only)):
    result = await execute_ch_query(f"SELECT * FROM {settings.CLICKHOUSE_DB}.transactions ORDER BY event_time DESC LIMIT 10", client_getter=get_ch_client)
    logs = result.named_results()
    for log in logs:
        # log["sender_email"] = mask_email(log.get("sender_email"))
        # log["recipient_email"] = mask_email(log.get("recipient_email"))
        log["status"] = "cleared"
        log["created_at"] = log.get("event_time")
    return logs

@router.post("/query")
async def execute_admin_query(request: QueryRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    source = request.params.get("source", "clickhouse")
    start_time = datetime.now()
    if source == "postgres":
        query_template = PREDEFINED_QUERIES["postgres"].get(request.query)
        if not query_template: raise HTTPException(status_code=400, detail="Invalid postgres query")
        result = await db.execute(text(query_template), request.params)
        data = [dict(row._mapping) for row in result]
        columns = list(data[0].keys()) if data else []
    else:
        query_template = PREDEFINED_QUERIES["clickhouse"].get(request.query)
        if not query_template: raise HTTPException(status_code=400, detail="Invalid clickhouse query")
        res = await execute_ch_query(query_template, parameters=request.params, client_getter=get_ch_client)
        data, columns = res.named_results(), res.column_names
    for row in data:
        # for key in ["email", "sender_email", "recipient_email", "target_email"]:
        #     if key in row: row[key] = mask_email(row[key])
        for key in ["first_name", "last_name"]:
            if key in row: row[key] = mask_name(row[key])
    return {"columns": columns, "data": data, "rowCount": len(data), "executionTime": round((datetime.now() - start_time).total_seconds() * 1000, 2)}

@router.get("/banking-metrics")
async def get_banking_metrics(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)):
    return await get_system_metrics(db)

@router.get("/kafka")
async def get_kafka_status(current_user: User = Depends(admin_only)):
    try:
        admin = AdminClient({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
        metadata = admin.list_topics(timeout=10)
        return {"topics": list(metadata.topics.keys())}
    except Exception as e:
        logger.error(f"Kafka status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
