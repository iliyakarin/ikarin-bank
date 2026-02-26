import json
import uuid
import os
import re
import datetime
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from decimal import Decimal
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from database import SessionLocal, Transaction, User, Account, Outbox, IdempotencyKey

from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer
import clickhouse_connect
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI(title="Simple Bank API")

# Configuration
ADMIN_EMAILS = os.getenv(
    "ADMIN_EMAILS", "ikarin@admin.com,ikarin2@admin.com"
).split(",")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "bank_transactions")
KAFKA_USER = os.getenv("KAFKA_USER", "admin")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")

CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Use a fallback for dev, but warn
    print("[WARN] SECRET_KEY not set in environment! Using insecure default.")
    SECRET_KEY = "[REDACTED]"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Pydantic Models for Auth
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


class P2PTransferRequest(BaseModel):
    recipient_email: str
    amount: Decimal
    idempotency_key: Optional[str] = None



# Helper Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def admin_only(current_user: User = Depends(get_current_user)):
    """Check if current user is an admin"""
    # Check for admin status via explicit list or RBAC role
    is_admin_flag = getattr(current_user, "is_admin", False)

    # Check if user has 'admin' role or is in the legacy admin email list
    # We prioritize the database role for RBAC
    if current_user.role != "admin" and not is_admin_flag and current_user.email not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=403, detail="Admin privileges required for this operation"
        )
    return current_user


# --- Auth Endpoints ---


@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Auto-create an account for the new user
    new_account = Account(user_id=new_user.id, balance=0.00)
    db.add(new_account)
    db.commit()

    return new_user


@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/accounts/{user_id}")
async def get_account_balance(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {"balance": float(account.balance), "user_id": user_id}


# --- Observability Endpoints ---


@app.get("/admin/stats")
async def get_stats(
    db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    # 1. Postgres Count
    pg_count = db.query(func.count(Transaction.id)).scalar()

    # 2. ClickHouse Count
    ch_client = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
    )
    ch_result = ch_client.query("SELECT count() FROM transactions")
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
        print(f"Error fetching Kafka metadata: {e}")
        lag = -1

    # 5. System Volume (24h)
    today = datetime.datetime.utcnow()
    yesterday = today - datetime.timedelta(days=1)
    system_volume = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.category == "P2P", Transaction.created_at >= yesterday)
        .scalar()
        or 0.0
    )

    return {
        "postgres_count": pg_count,
        "clickhouse_count": ch_count,
        "delta": delta,
        "kafka_lag": lag,
        "system_volume": float(system_volume),
        "sync_health": "in_sync" if delta < 5 else "syncing",
        "status": "healthy" if lag < 5000 and lag >= 0 else "degraded",
    }


@app.get("/admin/traces")
async def get_traces(
    db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    # Get last 20 transactions from Postgres
    pg_txs = (
        db.query(Transaction).order_by(Transaction.created_at.desc()).limit(20).all()
    )
    tx_ids = [tx.id for tx in pg_txs]

    # Get matching records from ClickHouse
    ch_client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT)
    # Using IN clause for efficiency
    # Use parameterized query to prevent SQL injection
    query = "SELECT transaction_id, event_time FROM transactions WHERE transaction_id IN {tx_ids:Array(String)}"
    ch_txs = ch_client.query(query, parameters={'tx_ids': tx_ids}).named_results()

    ch_map = {row["transaction_id"]: row["event_time"] for row in ch_txs}

    traces = []
    for tx in pg_txs:
        ch_time = ch_map.get(tx.id)
        traces.append(
            {
                "id": tx.id,
                "merchant": tx.merchant,
                "postgres_at": tx.created_at.isoformat(),
                "kafka_at": (
                    tx.created_at + datetime.timedelta(milliseconds=50)
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


class SimulationRequest(BaseModel):
    tps: int
    count: int


@app.post("/admin/simulate")
async def simulate_traffic(
    req: SimulationRequest,
    background_tasks: BackgroundTasks,
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
                amount=10.0,
                category="Simulation",
                merchant=f"Bot-{i}",
                status="pending",
            )
            db.add(new_tx)
            db.commit()

            payload = {
                "transaction_id": tx_id,
                "account_id": 1,
                "amount": 10.0,
                "category": "Simulation",
                "merchant": f"Bot-{i}",
                "status": "pending",
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }
            if producer:
                await producer.send(KAFKA_TOPIC, json.dumps(payload).encode("utf-8"))

            # Update status to sent_to_kafka
            new_tx.status = "sent_to_kafka"
            db.commit()
        except Exception as e:
            print(f"Simulation error: {e}")
        finally:
            db.close()

        if i % tps == 0:
            await asyncio.sleep(1)  # Simple rate limiting
        else:
            await asyncio.sleep(delay)


# --- Original Endpoints ---


@app.get("/admin/kafka-status")
def get_kafka_status(current_user: User = Depends(admin_only)):
    admin = AdminClient(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        }
    )
    topics = admin.list_topics(timeout=10)
    return {"topics": list(topics.topics.keys())}


@app.get("/admin/postgres-logs")
def get_postgres_logs(
    db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    return db.query(Transaction).order_by(Transaction.created_at.desc()).limit(10).all()


@app.get("/admin/clickhouse-logs")
def get_ch_logs(current_user: User = Depends(admin_only)):
    # Connect to ClickHouse
    client = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
    )
    result = client.query(
        "SELECT * FROM transactions ORDER BY event_time DESC LIMIT 10"
    )
    logs = result.named_results()
    for log in logs:
        log["status"] = "cleared"
        log["created_at"] = log["event_time"]  # For frontend consistency
    return logs


# Kafka Producer state
producer = None


@app.on_event("startup")
async def startup_event():
    global producer
    max_retries = 30
    retry_count = 0
    retry_delay = 1  # seconds

    while retry_count < max_retries:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                enable_idempotence=True,
                security_protocol="SASL_PLAINTEXT",
                sasl_mechanism="PLAIN",
                sasl_plain_username=KAFKA_USER,
                sasl_plain_password=KAFKA_PASSWORD,
            )
            await producer.start()
            print(f"[INFO] Kafka producer connected successfully")
            return
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(
                    f"[WARN] Kafka connection attempt {retry_count}/{max_retries} failed: {e}. Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
            else:
                print(
                    f"[WARN] Failed to connect to Kafka after {max_retries} attempts. Continuing without Kafka..."
                )
                producer = None
                return


@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        await producer.stop()


class TransferRequest(BaseModel):
    account_id: int
    amount: float
    category: str
    merchant: str


@app.post("/transfer")
async def create_transfer(transfer: TransferRequest, db: Session = Depends(get_db)):
    tx_id = str(uuid.uuid4())
    try:

        new_tx = Transaction(
            id=tx_id,
            account_id=transfer.account_id,
            amount=transfer.amount,
            category=transfer.category,
            merchant=transfer.merchant,
            status="pending",
        )
        db.add(new_tx)
        
        # Add to Outbox instead of direct Kafka send
        payload = {
            "transaction_id": tx_id,
            "account_id": transfer.account_id,
            "amount": transfer.amount,
            "category": transfer.category,
            "merchant": transfer.merchant,
            "transaction_type": "expense",
            "status": "pending",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        
        outbox_entry = Outbox(
            event_type="transaction.created",
            payload=payload
        )

        db.add(outbox_entry)
        
        db.commit()
        return {"status": "success", "transaction_id": tx_id}
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Transfer failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")




@app.post("/p2p-transfer")
async def create_p2p_transfer(
    transfer: P2PTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    # 1. Idempotency Check
    if transfer.idempotency_key:
        existing_key = db.query(IdempotencyKey).filter(
            IdempotencyKey.key == transfer.idempotency_key,
            IdempotencyKey.user_id == current_user.id
        ).first()
        if existing_key:
            return existing_key.response_body

    # 2. Recipient Lookup
    recipient = db.query(User).filter(User.email == transfer.recipient_email).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    tx_id_parent = str(uuid.uuid4())
    tx_id_sender = str(uuid.uuid4())
    tx_id_recipient = str(uuid.uuid4())
    
    try:
        # 3. Atomic Locking & Balance Verification (ACID)
        # We must lock BOTH accounts to prevent deadlocks and race conditions.
        # Order by ID to prevent deadlocks.
        account_ids = sorted([current_user.id, recipient.id])
        
        # This is a slightly naive way to lock by user_id but since we have 1:1 account:user for now it works.
        # Ideally we fetch account IDs first, then lock them in ascending order.
        
        sender_account = db.query(Account).filter(Account.user_id == current_user.id).with_for_update().first()
        recipient_account = db.query(Account).filter(Account.user_id == recipient.id).with_for_update().first()

        if not sender_account or sender_account.balance < transfer.amount:
            raise HTTPException(
                status_code=400, detail="Insufficient funds for this transfer."
            )

        if not recipient_account:
            raise HTTPException(status_code=404, detail="Recipient account not found")

        # 4. Multi-sided Balance Mutation
        sender_account.balance -= transfer.amount
        recipient_account.balance += transfer.amount

        # 5. Double Entry Ledger (Immutable records)
        sender_tx = Transaction(
            id=tx_id_sender,
            parent_id=tx_id_parent,
            account_id=sender_account.id,
            amount=-transfer.amount,
            category="Transfer",
            merchant=f"Transfer to {recipient.email}",
            status="pending",
            transaction_type="transfer",
            transaction_side="DEBIT",
            idempotency_key=transfer.idempotency_key,
            ip_address=client_ip,
            user_agent=user_agent
        )

        recipient_tx = Transaction(
            id=tx_id_recipient,
            parent_id=tx_id_parent,
            account_id=recipient_account.id,
            amount=transfer.amount,
            category="Transfer",
            merchant=f"Received from {current_user.email}",
            status="pending",
            transaction_type="transfer",
            transaction_side="CREDIT",
            idempotency_key=transfer.idempotency_key,
            ip_address=client_ip,
            user_agent=user_agent
        )

        db.add(sender_tx)
        db.add(recipient_tx)

        # 6. Outbox entries for both sides (ensures ClickHouse is also in sync)
        sender_payload = {
            "transaction_id": tx_id_sender,
            "parent_id": tx_id_parent,
            "account_id": sender_account.id,
            "sender_email": current_user.email,
            "recipient_email": recipient.email,
            "amount": -float(transfer.amount),
            "category": "Transfer",
            "merchant": f"Transfer to {recipient.email}",
            "transaction_type": "transfer",
            "transaction_side": "DEBIT",
            "status": "pending",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        recipient_payload = {
            "transaction_id": tx_id_recipient,
            "parent_id": tx_id_parent,
            "account_id": recipient_account.id,
            "sender_email": current_user.email,
            "recipient_email": recipient.email,
            "amount": float(transfer.amount),
            "category": "Transfer",
            "merchant": f"Received from {current_user.email}",
            "transaction_type": "transfer",
            "transaction_side": "CREDIT",
            "status": "pending",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        db.add(Outbox(event_type="p2p.sender", payload=sender_payload))
        db.add(Outbox(event_type="p2p.recipient", payload=recipient_payload))

        # 7. Finalize Idempotency Key
        response_body = {"status": "success", "transaction_id": tx_id_parent}
        if transfer.idempotency_key:
            db.add(IdempotencyKey(
                key=transfer.idempotency_key,
                user_id=current_user.id,
                response_code=200,
                response_body=response_body
            ))

        db.commit()
        return response_body

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] P2P Transfer failed: {e}")
        raise HTTPException(status_code=500, detail="Internal financial processing error")




# --- Dashboard & Analytics Endpoints ---


@app.get("/dashboard/balance-history")
async def get_balance_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get balance history for a user for the given day range."""
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
        )

        # Query ClickHouse for balance trend
        query = f"""
        SELECT 
            toDate(event_time) as date,
            account_id,
            sum(amount) as daily_change
        FROM banking.transactions
        WHERE account_id = {account.id} 
            AND event_time >= now() - INTERVAL {days} DAY
        GROUP BY toDate(event_time), account_id
        ORDER BY date
        """

        result = ch_client.query(query).named_results()

        # Build cumulative balance history
        balance_history = []
        current_balance = float(account.balance)

        # Get start date
        start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        for row in result:
            balance_history.append(
                {
                    "date": row["date"].isoformat()
                    if hasattr(row["date"], "isoformat")
                    else str(row["date"]),
                    "balance": current_balance,
                    "daily_change": float(row["daily_change"])
                    if row["daily_change"]
                    else 0,
                }
            )

        return {
            "balance_history": balance_history,
            "current_balance": float(account.balance),
        }
    except Exception as e:
        print(f"Error querying ClickHouse: {e}")
        # Fallback: return just current balance
        return {"balance_history": [], "current_balance": float(account.balance)}


@app.get("/dashboard/recent-transactions")
async def get_recent_transactions(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recent transactions from the last N hours - user must be sender or recipient."""
    try:
        user_email = current_user.email.lower()
        
        # 1. Get PENDING transactions from Postgres (only outgoing ones exist here)
        user_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
        account_ids = [acc.id for acc in user_accounts]
        
        pg_transactions = (
            db.query(Transaction)
            .filter(Transaction.account_id.in_(account_ids))
            .filter(
                Transaction.created_at >= datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
            )
            .order_by(Transaction.created_at.desc())
            .limit(10)
            .all()
        )
        
        # 2. Get CLEARED/HISTORY transactions from ClickHouse (incoming AND outgoing)
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
        )
        
        # Join account IDs for ClickHouse query to ensure we only get transactions belonging to the user's specific accounts
        # This prevents duplicate entries for P2P transfers while ensuring both sender and recipient see their record.
        if not account_ids:
            return {"transactions": []}
            
        account_ids_str = ",".join([str(aid) for aid in account_ids])
        
        query = f"""
            SELECT 
                toString(transaction_id) as id,
                amount,
                category,
                merchant,
                sender_email,
                recipient_email,
                transaction_type,
                transaction_side,
                event_time
            FROM banking.transactions
            WHERE account_id IN ({account_ids_str})
            AND event_time >= now() - INTERVAL {hours} HOUR
            ORDER BY event_time DESC
            LIMIT 20
        """
        
        ch_results = ch_client.query(query).result_rows
        
        # 3. Merge and formatting
        # We prefer ClickHouse data (status='cleared'), but keep Postgres data if it's not in CH yet (status='pending')
        
        final_txs = []
        ch_ids = set()
        
        # Process ClickHouse results first (Confirmed transactions)
        for row in ch_results:
            tx_id = row[0]
            ch_ids.add(tx_id)
            final_txs.append({
                "id": tx_id,
                "amount": float(row[1]),
                "category": row[2],
                "merchant": row[3],
                "sender_email": row[4],
                "recipient_email": row[5],
                "transaction_type": row[6],
                "transaction_side": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "status": "cleared"
            })
            
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
                    "amount": float(tx.amount),
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
        print(f"[ERROR] Error fetching transactions: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to empty list or partial data if critical failure
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch transactions: {str(e)}"
        )


@app.get("/transactions")
async def get_all_transactions(
    days: int = 1,
    tx_type: str = None,  # 'incoming', 'outgoing', or None for all
    min_amount: float = None,
    max_amount: float = None,
    sort: str = "desc",  # 'asc' or 'desc'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all transactions with filtering by sender/recipient email, amount, date range, and sort direction."""
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    try:
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
        )

        # Visibility: user must see transactions exactly for THEIR account
        where_clauses = [
            f"account_id = {account.id}",
            f"event_time >= now() - INTERVAL {days} DAY",
        ]

        # Type filtering: incoming = positive/CREDIT, outgoing = negative/DEBIT
        if tx_type:
            if tx_type.lower() == "outgoing":
                where_clauses.append("amount < 0")
            elif tx_type.lower() == "incoming":
                where_clauses.append("amount > 0")

        # Amount range filtering (use absolute value so user-entered ranges apply to magnitude)
        if min_amount is not None:
            where_clauses.append(f"abs(amount) >= {min_amount}")

        if max_amount is not None:
            where_clauses.append(f"abs(amount) <= {max_amount}")

        where_clause = " AND ".join(where_clauses)

        # Sorting direction
        sort_dir = "ASC" if sort and sort.lower() == "asc" else "DESC"

        query = f"""
        SELECT
            transaction_id,
            sender_email,
            recipient_email,
            amount,
            category,
            merchant,
            transaction_type,
            transaction_side,
            event_time
        FROM banking.transactions
        WHERE {where_clause}
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
                "amount": float(row["amount"]),
                "category": row["category"],
                "merchant": row.get("merchant"),
                "transaction_type": row.get("transaction_type", "expense"),
                "transaction_side": row.get("transaction_side"),
                "timestamp": row["event_time"].isoformat()
                if hasattr(row["event_time"], "isoformat")
                else str(row["event_time"]),
                # Hardcode status as requested
                "status": "Cleared",
            }
            transactions.append(tx)

        return {"transactions": transactions, "total": len(transactions)}
    except Exception as e:
        print(f"Error querying ClickHouse transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transactions")


# --- Admin Endpoints ---


class QueryRequest(BaseModel):
    query: str
    params: Dict[str, Any] = {}


@app.post("/admin/query")
async def execute_admin_query(
    request: QueryRequest,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    """Execute admin query against ClickHouse, PostgreSQL, or Kafka"""
    try:
        source = request.params.get("source", "clickhouse")
        start_time = datetime.datetime.now()

        # SQL Validation for relational/analytical sources
        if source in ["clickhouse", "postgres"]:
            query_upper = request.query.strip().upper()
            if not query_upper.startswith("SELECT"):
                raise HTTPException(
                    status_code=400, detail="Only SELECT queries are allowed"
                )

            # Block forbidden keywords that could be used for injection or destructive actions
            forbidden = [
                "DROP",
                "DELETE",
                "UPDATE",
                "INSERT",
                "TRUNCATE",
                "ALTER",
                "CREATE",
                "GRANT",
                "REVOKE",
                "RENAME",
            ]
            for word in forbidden:
                if re.search(r"\b" + word + r"\b", query_upper):
                    raise HTTPException(
                        status_code=400, detail=f"Forbidden keyword '{word}' detected"
                    )

        if source == "clickhouse":
            # Connect to ClickHouse using readonly credentials for safety
            ch_client = clickhouse_connect.get_client(
                host=CH_HOST,
                port=CH_PORT,
                username=os.getenv("CLICKHOUSE_READONLY_USER", "readonly_admin"),
                password=os.getenv(
                    "CLICKHOUSE_READONLY_PASSWORD", "REDACTED"
                ),
            )

            # Corrected query execution with parameter support
            query = request.query
            # Only allow params that are used in actual placeholder syntax {param}
            # Note: clickhouse_connect supports parameter binding
            result = ch_client.query(query, parameters=request.params)
            data = result.result_rows
            columns = result.column_names


        elif source == "postgres":
            # Execute PostgreSQL query with parameter binding to prevent SQL injection
            result = db.execute(text(request.query), request.params)
            data = [dict(row._mapping) for row in result]
            columns = list(data[0].keys()) if data else []


        elif source == "kafka":
            # Handle Kafka-specific queries
            if request.query == "get_recent_messages":
                # Get recent messages from Kafka topic
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
                    data = messages

                except Exception as e:
                    consumer.close()
                    raise HTTPException(
                        status_code=500, detail=f"Kafka error: {str(e)}"
                    )

            elif request.query == "get_topic_stats":
                # Get topic statistics
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

                except Exception as e:
                    raise HTTPException(
                        status_code=500, detail=f"Failed to get topic stats: {str(e)}"
                    )

            else:
                raise HTTPException(status_code=400, detail="Unknown Kafka query type")

        else:
            raise HTTPException(status_code=400, detail="Invalid data source specified")

        execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000

        return {
            "columns": columns,
            "data": data,
            "rowCount": len(data),
            "executionTime": round(execution_time, 2),
        }

    except Exception as e:
        print(f"Admin query error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.get("/admin/banking-metrics")
async def get_banking_metrics(
    current_user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    """Get comprehensive banking metrics for admin dashboard"""
    try:
        # PostgreSQL queries for user/account data
        total_balance = db.query(func.sum(Account.balance)).scalar() or 0
        active_users_24h = (
            db.query(User)
            .filter(
                User.created_at >= datetime.datetime.now() - datetime.timedelta(days=1)
            )
            .count()
        )
        total_users = db.query(User).count()

        # ClickHouse queries for transaction data
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
        )

        # 24h transaction metrics
        volume_query = """
        SELECT 
            SUM(amount) as total_volume,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_transaction_size
        FROM banking.transactions 
        WHERE event_time >= now() - INTERVAL 1 DAY
        """


        volume_result = ch_client.query(volume_query)
        volume_data = volume_result.result_rows[0]
        total_volume = float(volume_data[0]) if volume_data[0] else 0
        transaction_count = int(volume_data[1]) if volume_data[1] else 0
        avg_transaction_size = float(volume_data[2]) if volume_data[2] else 0

        # Top transactions in last 24h
        top_transactions_query = """
        SELECT merchant, amount, account_id, event_time as created_at
        FROM banking.transactions 
        WHERE event_time >= now() - INTERVAL 1 DAY
        ORDER BY amount DESC 
        LIMIT 10
        """


        top_result = ch_client.query(top_transactions_query)
        top_transactions = [
            {
                "merchant": row[0],
                "amount": float(row[1]),
                "account_id": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in top_result.result_rows
        ]

        # Hourly volume for last 24h
        hourly_query = """
        SELECT 
            toHour(created_at) as hour,
            COUNT(*) as count,
            SUM(amount) as total
        FROM bank_transactions 
        WHERE created_at >= now() - INTERVAL 1 DAY
        GROUP BY hour 
        ORDER BY hour
        """

        hourly_result = ch_client.query(hourly_query)
        hourly_volume = [
            {
                "hour": int(row[0]),
                "count": int(row[1]),
                "total": float(row[2]) if row[2] else 0,
            }
            for row in hourly_result.result_rows
        ]

        # Top merchants by volume (7 days)
        merchant_query = """
        SELECT 
            merchant,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount
        FROM bank_transactions 
        WHERE created_at >= now() - INTERVAL 7 DAY
            AND merchant != ''
        GROUP BY merchant 
        ORDER BY total_amount DESC 
        LIMIT 10
        """

        merchant_result = ch_client.query(merchant_query)
        merchant_stats = [
            {
                "merchant": row[0],
                "transaction_count": int(row[1]),
                "total_amount": float(row[2]) if row[2] else 0,
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

        user_growth_result = db.execute(text(user_growth_query))
        user_growth = [
            {"date": str(row[0]), "count": int(row[1])} for row in user_growth_result
        ]

        return {
            "totalVolume": total_volume,
            "transactionCount": transaction_count,
            "totalBalance": float(total_balance),
            "activeUsers": active_users_24h,
            "avgTransactionSize": avg_transaction_size,
            "topTransactions": top_transactions,
            "hourlyVolume": hourly_volume,
            "merchantStats": merchant_stats,
            "userGrowth": user_growth,
        }

    except Exception as e:
        print(f"Error fetching banking metrics: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch banking metrics")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
