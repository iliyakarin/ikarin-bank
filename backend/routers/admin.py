from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, BackgroundTasks
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import Session
from database import User, Account, Transaction, Outbox, SessionLocal
from schemas.users import UserResponse
from schemas.admin import SimulationRequest, QueryRequest
from auth_utils import get_db, get_current_user, RoleChecker
from datetime import datetime, timezone, timedelta
import json
import logging
import random
import uuid
import os
import re
import asyncio
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer, KafkaException
from clickhouse_utils import get_ch_client, CH_DB
import clickhouse_connect
from activity import emit_activity
from sync_checker import run_sync_check
from config import settings
from services.admin_service import compliance_delete_user, get_system_metrics

KAFKA_BOOTSTRAP_SERVERS = settings.KAFKA_BOOTSTRAP_SERVERS
KAFKA_TOPIC = settings.KAFKA_TOPIC
KAFKA_USER = settings.KAFKA_USER
KAFKA_PASSWORD = settings.KAFKA_PASSWORD

CH_HOST = settings.CLICKHOUSE_HOST
CH_PORT = settings.CLICKHOUSE_PORT
CH_USER = settings.CLICKHOUSE_USER
CH_PASSWORD = settings.CLICKHOUSE_PASSWORD

logger = logging.getLogger(__name__)

router = APIRouter()
admin_only = RoleChecker(["admin"])

# Security: Predefined query registry to prevent arbitrary SQL execution
PREDEFINED_QUERIES = {
    "clickhouse": {
        "get_recent_transactions": f"SELECT * FROM {settings.CLICKHOUSE_DB}.transactions ORDER BY event_time DESC LIMIT :limit",
        "get_transaction_trace": f"SELECT transaction_id, event_time FROM {settings.CLICKHOUSE_DB}.transactions WHERE transaction_id IN :tx_ids",
        "get_activity_log": f"SELECT * FROM {settings.CLICKHOUSE_DB}.activity_events WHERE user_id = :user_id ORDER BY event_time DESC LIMIT :limit",
    },
    "postgres": {
        "get_recent_transactions": "SELECT * FROM transactions ORDER BY created_at DESC LIMIT :limit",
        "get_user_details": "SELECT id, email, full_name, role, created_at FROM users WHERE id = :user_id",
        "get_account_details": "SELECT id, user_id, name, balance, account_uuid FROM accounts WHERE id = :account_id",
    }
}

@router.get("/admin/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)
):
    # 1. Postgres Count
    result = await db.execute(select(func.count(Transaction.id)))
    pg_count = result.scalar()

    # 2. ClickHouse Count
    ch_client = get_ch_client()
    ch_result = ch_client.query(f"SELECT count() FROM {settings.CLICKHOUSE_DB}.transactions")
    ch_count = ch_result.result_rows[0][0]

    # 3. Delta
    delta = pg_count - ch_count

    # 4. Kafka Lag (Simplified but more descriptive)
    admin = AdminClient(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        }
    )

    try:
        metadata = admin.list_topics(timeout=5)
        topic_metadata = metadata.topics.get(KAFKA_TOPIC)
        if topic_metadata:
            partitions = len(topic_metadata.partitions)
            lag = partitions * 10  # Placeholder for actual lag calculation
        else:
            lag = -1
    except Exception as e:
        logger.error(f"Error fetching Kafka metadata: {e}")
        lag = -1

    # 5. System Volume (24h)
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)

    result = await db.execute(
        select(func.sum(Transaction.amount))
        .filter(Transaction.category == "P2P", Transaction.created_at >= yesterday)
    )
    system_volume_cents = result.scalar() or 0
    system_volume = int(system_volume_cents)

    return {
        "postgres_count": pg_count,
        "clickhouse_count": ch_count,
        "delta": delta,
        "kafka_lag": lag,
        "system_volume": int(system_volume),
        "sync_health": "in_sync" if delta < 5 else "syncing",
        "status": "healthy" if lag < 5000 and lag >= 0 else "degraded",
    }


@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Admin-only: List all users in the system."""
    result = await db.execute(
        select(User).order_by(User.id.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return users


@router.get("/users/search", response_model=UserResponse)
async def search_user_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Admin-only: Search for a user by their email address."""
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Compliance-grade User Deletion (Right to Erasure).
    Delegates anonymization and purging to the admin service.
    """
    success = await compliance_delete_user(db, current_user.id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return None


@router.get("/admin/traces")
async def get_traces(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)
):
    # Get last 20 transactions from Postgres
    result = await db.execute(
        select(Transaction).order_by(Transaction.created_at.desc()).limit(20)
    )
    pg_txs = result.scalars().all()
    tx_ids = [tx.id for tx in pg_txs]

    # Get matching records from ClickHouse
    try:
        ch_client = get_ch_client()
        # Using IN clause for efficiency
        # Use parameterized query to prevent SQL injection
        query = "SELECT transaction_id, event_time FROM transactions WHERE transaction_id IN {tx_ids:Array(String)}"
        ch_txs = ch_client.query(query, parameters={'tx_ids': tx_ids}).named_results()
        ch_map = {row["transaction_id"]: row["event_time"] for row in ch_txs}
    except Exception as e:
        logger.warning(f"ClickHouse trace lookup failed: {e}")
        ch_map = {}

    traces = []
    for tx in pg_txs:
        ch_time = ch_map.get(tx.id)
        traces.append(
            {
                "id": tx.id,
                "merchant": tx.merchant,
                "postgres_at": tx.created_at.isoformat(),
                "kafka_at": (
                    tx.created_at + timedelta(milliseconds=50)
                ).isoformat(),  # Simulated
                "clickhouse_at": ch_time.isoformat() if ch_time else None,
                "latency": (ch_time - tx.created_at).total_seconds() * 1000
                if ch_time
                else None,
                "status": "cleared" if ch_time else tx.status,
            }
        )

    return traces


# --- Simulation Endpoints ---



@router.post("/admin/simulate")
async def simulate_traffic(
    req: SimulationRequest,
    background_tasks: BackgroundTasks,
    # Ensure this endpoint is protected by admin_only dependency
    current_user: User = Depends(admin_only),
):
    background_tasks.add_task(run_simulation, req.tps, req.count)
    return {"status": "simulation_started", "tps": req.tps, "total": req.count}


async def run_simulation(tps: int, count: int):
    # Re-using the logic from create_transfer but in a loop
    delay = 1.0 / tps
    for i in range(count):
        # We need a fresh DB session in background
        db = SessionLocal()
        tx_id = str(uuid.uuid4())
        try:
            new_tx = Transaction(
                id=tx_id,
                account_id=1,
                amount=1000, # 10.00 as 1000 cents
                category="Simulation",
                merchant=f"Bot-{i}",
                status="pending",
                internal_account_last_4="Simulation", # Placeholder for bot
                sender_email="simulation@bot.karin",
                recipient_email="simulation@bot.karin"
            )
            db.add(new_tx)
            await db.commit()

            payload = {
                "transaction_id": tx_id,
                "account_id": 1,
                "amount": 1000, # 1000 cents
                "category": "Simulation",
                "merchant": f"Bot-{i}",
                "status": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if producer:
                await producer.send(KAFKA_TOPIC, json.dumps(payload).encode("utf-8"))

            # Update status to sent_to_kafka
            new_tx.status = "sent_to_kafka"
            await db.commit()
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            await db.close()

        if i % tps == 0:
            await asyncio.sleep(1)  # Simple rate limiting
        else:
            await asyncio.sleep(delay)


# --- Original Endpoints ---


@router.get("/admin/kafka-status")
def get_kafka_status(current_user: User = Depends(admin_only)):
    """Get Kafka topics status (Admin only)."""
    admin = AdminClient(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        }
    )
    topics = admin.list_topics(timeout=10)
    return {"topics": list(topics.topics.keys())}


@router.get("/admin/postgres-logs")
async def get_postgres_logs(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)
):
    result = await db.execute(select(Transaction).order_by(Transaction.created_at.desc()).limit(10))
    return result.scalars().all()


@router.get("/admin/clickhouse-logs")
def get_ch_logs(current_user: User = Depends(admin_only)):
    # Connect to ClickHouse
    client = get_ch_client()
    result = client.query(
        f"SELECT * FROM {CH_DB}.transactions ORDER BY event_time DESC LIMIT 10"
    )

    logs = result.named_results()
    for log in logs:
        log["status"] = "cleared"
        log["created_at"] = log["event_time"]  # For frontend consistency
    return logs


@router.post("/admin/sync-clickhouse")
def manual_sync_clickhouse(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(admin_only)
):
    background_tasks.add_task(run_sync_check)
    return {"status": "success", "message": "Manual ClickHouse sync started in the background."}


@router.get("/admin/config")
async def get_admin_config(current_user: User = Depends(admin_only)):
    """Returns full configuration for database connectivity (admin-only)."""

    return {
        "env": settings.ENV,
        "clickhouse": {
            "host": settings.CLICKHOUSE_HOST,
            "port": settings.CLICKHOUSE_PORT,
            "username": settings.CLICKHOUSE_USER,
            "password": settings.CLICKHOUSE_PASSWORD,
            "database": settings.CLICKHOUSE_DB
        },
        "postgres": {
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "username": settings.POSTGRES_USER,
            "password": settings.POSTGRES_PASSWORD,
            "database": settings.POSTGRES_DB
        },
        "kafka": {
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "username": settings.KAFKA_USER,
            "password": settings.KAFKA_PASSWORD,
            "topic": settings.KAFKA_TOPIC
        }
    }


# Kafka Producer state
producer = None



# _validate_sql_query removed as we now use a predefined query registry.


def _execute_clickhouse_query(request: QueryRequest) -> Tuple[List, List]:
    """Executes a predefined query against ClickHouse."""
    query_name = request.query  # Now we expect the name of the predefined query
    source_queries = PREDEFINED_QUERIES.get("clickhouse", {})

    if query_name not in source_queries:
        raise HTTPException(status_code=400, detail=f"Invalid ClickHouse query name: {query_name}")

    query_template = source_queries[query_name]

    ch_client = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_READONLY_PASSWORD or settings.CLICKHOUSE_PASSWORD,
    )

    result = ch_client.query(query_template, parameters=request.params)
    return result.result_rows, result.column_names


async def _execute_postgres_query(request: QueryRequest, db: AsyncSession) -> Tuple[List, List]:
    """Executes a predefined query against PostgreSQL."""
    query_name = request.query
    source_queries = PREDEFINED_QUERIES.get("postgres", {})

    if query_name not in source_queries:
        raise HTTPException(status_code=400, detail=f"Invalid Postgres query name: {query_name}")

    query_template = source_queries[query_name]

    # Execute PostgreSQL query with parameter binding to prevent SQL injection
    result = await db.execute(text(query_template), request.params)
    data = [dict(row._mapping) for row in result]
    columns = list(data[0].keys()) if data else []
    return data, columns


def _execute_kafka_query(request: QueryRequest) -> Tuple[List, List]:
    """Executes a query against Kafka."""
    if request.query == "get_recent_messages":
        return _get_kafka_recent_messages()
    elif request.query == "get_topic_stats":
        return _get_kafka_topic_stats()
    else:
        raise HTTPException(status_code=400, detail="Unknown Kafka query type")


def _get_kafka_recent_messages() -> Tuple[List, List]:
    """Retrieves recent messages from Kafka."""
    consumer_conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "admin_query_group",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }

    if KAFKA_USER and KAFKA_PASSWORD:
        consumer_conf["sasl.mechanisms"] = "PLAIN"
        consumer_conf["security.protocol"] = "SASL_PLAINTEXT"
        consumer_conf["sasl.username"] = KAFKA_USER
        consumer_conf["sasl.password"] = KAFKA_PASSWORD

    consumer = Consumer(consumer_conf)
    messages = []

    try:
        consumer.subscribe([KAFKA_TOPIC])
        # Read last 100 messages
        for i in range(100):
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                break

            try:
                data = json.loads(msg.value().decode("utf-8"))
                messages.append(
                    {
                        "key": msg.key().decode("utf-8")
                        if msg.key()
                        else None,
                        "value": data,
                        "partition": msg.partition(),
                        "offset": msg.offset(),
                        "timestamp": msg.timestamp()[1]
                        if msg.timestamp()[0]
                        else None,
                    }
                )
            except:
                pass

        consumer.close()
        columns = ["key", "value", "partition", "offset", "timestamp"]
        return messages, columns

    except Exception as e:
        consumer.close()
        raise HTTPException(
            status_code=500, detail=f"Kafka error: {str(e)}"
        )


def _get_kafka_topic_stats() -> Tuple[List, List]:
    """Retrieves Kafka topic statistics."""
    admin_client = AdminClient(
        {"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS}
    )

    if KAFKA_USER and KAFKA_PASSWORD:
        admin_client = AdminClient(
            {
                "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
                "sasl.mechanisms": "PLAIN",
                "security.protocol": "SASL_PLAINTEXT",
                "sasl.username": KAFKA_USER,
                "sasl.password": KAFKA_PASSWORD,
            }
        )

    try:
        metadata = admin_client.list_topics(timeout=10)
        topic_metadata = metadata.topics.get(KAFKA_TOPIC)

        if topic_metadata:
            partitions = topic_metadata.partitions
            total_messages = sum(
                p.high_watermark
                for p in partitions.values()
                if p.high_watermark
            )

            data = [
                {
                    "topic": KAFKA_TOPIC,
                    "partitions": len(partitions),
                    "total_messages": total_messages,
                    "status": "active",
                }
            ]
            columns = ["topic", "partitions", "total_messages", "status"]
        else:
            data = []
            columns = []
        return data, columns

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get topic stats: {str(e)}"
        )


@router.post("/admin/query")
async def execute_admin_query(
    request: QueryRequest,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    """Execute admin query against ClickHouse, PostgreSQL, or Kafka"""
    try:
        source = request.params.get("source", "clickhouse")
        start_time = datetime.now()

        if source == "clickhouse":
            data, columns = _execute_clickhouse_query(request)
        elif source == "postgres":
            data, columns = await _execute_postgres_query(request, db)
        elif source == "kafka":
            data, columns = _execute_kafka_query(request)
        else:
            raise HTTPException(status_code=400, detail="Invalid data source specified")

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "columns": columns,
            "data": data,
            "rowCount": len(data),
            "executionTime": round(execution_time, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin query error: {e}")
        import traceback

        logger.exception("An exception occurred")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")



@router.get("/admin/banking-metrics")
async def get_banking_metrics(
    current_user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    """Get comprehensive banking metrics for admin dashboard"""
    try:
        # PostgreSQL queries for user/account data
        total_balance_result = await db.execute(select(func.sum(Account.balance)))
        total_balance = total_balance_result.scalar() or 0
        active_users_result = await db.execute(
            select(func.count(User.id)).filter(
                User.created_at >= datetime.now() - timedelta(days=1)
            )
        )
        active_users_24h = active_users_result.scalar() or 0
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0

        # ClickHouse queries for transaction data
        ch_client = get_ch_client()

        # 24h transaction metrics
        volume_query = """
        SELECT
            SUM(amount) as total_volume,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_transaction_size
        FROM {CH_DB}.transactions
        WHERE event_time >= now() - INTERVAL 1 DAY
        """


        volume_result = ch_client.query(volume_query.format(CH_DB=CH_DB))
        volume_data = volume_result.result_rows[0]
        total_volume = int(volume_data[0]) if volume_data[0] else 0
        transaction_count = int(volume_data[1]) if volume_data[1] else 0
        avg_transaction_size = int(volume_data[2]) if volume_data[2] else 0

        # Top transactions in last 24h
        top_transactions_query = """
        SELECT merchant, amount, account_id, event_time as created_at
        FROM {CH_DB}.transactions
        WHERE event_time >= now() - INTERVAL 1 DAY
        ORDER BY amount DESC
        LIMIT 10
        """


        top_result = ch_client.query(top_transactions_query.format(CH_DB=CH_DB))
        top_transactions = [
            {
                "merchant": row[0],
                "amount": int(row[1]),
                "account_id": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in top_result.result_rows
        ]

        # Hourly volume for last 24h
        hourly_query = """
        SELECT
            toHour(event_time) as hour,
            COUNT(*) as count,
            SUM(amount) as total
        FROM {CH_DB}.transactions
        WHERE event_time >= now() - INTERVAL 1 DAY
        GROUP BY hour
        ORDER BY hour
        """

        hourly_result = ch_client.query(hourly_query.format(CH_DB=CH_DB))
        hourly_volume = [
            {
                "hour": int(row[0]),
                "count": int(row[1]),
                "total": int(row[2]) if row[2] else 0,
            }
            for row in hourly_result.result_rows
        ]

        # Top merchants by volume (7 days)
        merchant_query = """
        SELECT
            merchant,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount
        FROM {CH_DB}.transactions
        WHERE event_time >= now() - INTERVAL 7 DAY
            AND merchant != ''
        GROUP BY merchant
        ORDER BY total_amount DESC
        LIMIT 10
        """

        merchant_result = ch_client.query(merchant_query.format(CH_DB=CH_DB))
        merchant_stats = [
            {
                "merchant": row[0],
                "transaction_count": int(row[1]),
                "total_amount": int(row[2]) if row[2] else 0,
            }
            for row in merchant_result.result_rows
        ]

        # User registration trends (30 days)
        user_growth_query = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as count
        FROM users
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """

        user_growth_result = await db.execute(text(user_growth_query))
        user_growth = [
            {"date": str(row[0]), "count": int(row[1])} for row in user_growth_result
        ]

        return {
            "totalVolume": int(total_volume),
            "transactionCount": transaction_count,
            "totalBalance": int(total_balance),
            "activeUsers": active_users_24h,
            "avgTransactionSize": int(avg_transaction_size),
            "topTransactions": [
                {**tx, "amount": int(tx["amount"])} for tx in top_transactions
            ],
            "hourlyVolume": [
                {**h, "total": int(h["total"])} for h in hourly_volume
            ],
            "merchantStats": [
                {**m, "total_amount": int(m["total_amount"])} for m in merchant_stats
            ],
            "userGrowth": user_growth,
        }

    except Exception as e:
        logger.error(f"Error fetching banking metrics: {e}")
        import traceback

        logger.exception("An exception occurred")
        raise HTTPException(status_code=500, detail="Failed to fetch banking metrics")
