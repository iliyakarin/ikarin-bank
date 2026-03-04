import json
import uuid
import os
import re
import datetime
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_
from decimal import Decimal
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from database import SessionLocal, Transaction, User, Account, Outbox, IdempotencyKey, ScheduledPayment, PaymentRequest, Contact

from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer
import clickhouse_connect
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI(title="Simple Bank API")

# Configuration
# Admins are defined by role="admin" in the database
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
    raise ValueError("SECRET_KEY environment variable is not set. Cannot start application securely.")
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
    backup_email: Optional[str] = None
    role: str

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    amount: Optional[float] = None
    created_at: datetime.datetime
    link: str

    class Config:
        from_attributes = True

class UserBackupUpdate(BaseModel):
    backup_email: str

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class P2PTransferRequest(BaseModel):
    recipient_email: str
    amount: Decimal
    idempotency_key: Optional[str] = None
    commentary: Optional[str] = None
    payment_request_id: Optional[int] = None

class PaymentRequestCreate(BaseModel):
    target_email: str
    amount: Decimal
    purpose: Optional[str] = None

class PaymentRequestCounter(BaseModel):
    amount: Decimal



class ScheduledTransferCreate(BaseModel):
    recipient_email: str
    amount: Decimal
    frequency: str
    frequency_interval: Optional[str] = None
    start_date: datetime.datetime
    end_condition: str
    end_date: Optional[datetime.datetime] = None
    target_payments: Optional[int] = None
    reserve_amount: bool = False
    idempotency_key: Optional[str] = None

class ScheduledPaymentResponse(BaseModel):
    id: int
    user_id: int
    recipient_email: str
    amount: float
    frequency: str
    frequency_interval: Optional[str] = None
    start_date: datetime.datetime
    end_condition: str
    end_date: Optional[datetime.datetime] = None
    target_payments: Optional[int] = None
    payments_made: int
    next_run_at: Optional[datetime.datetime] = None
    status: str
    reserve_amount: bool

    class Config:
        from_attributes = True


class ContactCreate(BaseModel):
    contact_name: str
    contact_email: str

class ContactResponse(BaseModel):
    id: int
    user_id: int
    contact_name: str
    contact_email: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

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
    if current_user.role != "admin":
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

@app.post("/api/v1/users/me/backup", response_model=UserResponse)
async def update_backup_email(
    update_data: UserBackupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if this email is already used by someone else
    existing = db.query(User).filter(
        (User.email == update_data.backup_email) | 
        (User.backup_email == update_data.backup_email)
    ).first()
    
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="This email is already in use by another user")
        
    current_user.backup_email = update_data.backup_email
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.post("/api/v1/users/me/password")
async def update_password(
    password_data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    if len(password_data.new_password) < 8:
         raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")
         
    # Hash new password and save
    new_hashed_password = get_password_hash(password_data.new_password)
    current_user.password_hash = new_hashed_password
    db.commit()
    
    return {"status": "success"}


@app.get("/api/v1/users/me/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest 10 notifications (transactions & payment requests)."""
    notifications = []
    
    # 1. Transactions
    account_ids = [acc.id for acc in db.query(Account).filter(Account.user_id == current_user.id).all()]
    if account_ids:
        transactions = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.status != "cancelled"
        ).order_by(Transaction.created_at.desc()).limit(10).all()
        
        for tx in transactions:
            is_income = tx.amount > 0 and tx.transaction_side == "CREDIT"
            title = "Payment Received" if is_income else "Payment Sent"
            
            if tx.transaction_type == "transfer":
                if is_income:
                    msg = f"from {tx.merchant.replace('Received from ', '')}" if tx.merchant else "Transfer received"
                else:
                    msg = f"to {tx.merchant.replace('Transfer to ', '')}" if tx.merchant else "Transfer sent"
            else:
                msg = f"Merchant: {tx.merchant}" if tx.merchant else "Transaction processed"
                
            notifications.append({
                "id": f"tx_{tx.id}",
                "type": "transaction",
                "title": title,
                "message": msg,
                "amount": float(tx.amount) if tx.amount else None,
                "created_at": tx.created_at,
                "link": "/client/transactions"
            })
            
    # 2. Payment Requests
    requests = db.query(PaymentRequest).filter(
        or_(
            PaymentRequest.requester_id == current_user.id,
            PaymentRequest.target_email == current_user.email
        )
    ).order_by(PaymentRequest.created_at.desc()).limit(10).all()
    
    for req in requests:
        is_requester = req.requester_id == current_user.id
        if is_requester:
            title = "Request Sent"
            msg = f"You requested ${req.amount} from {req.target_email}"
        else:
            title = "Request Received"
            msg = f"Someone requested ${req.amount} from you"
            
        notifications.append({
            "id": f"pr_{req.id}",
            "type": "payment_request",
            "title": title,
            "message": msg,
            "amount": float(req.amount) if req.amount else None,
            "created_at": req.created_at,
            "link": "/client/send?tab=request"
        })
        
    # Sort by created_at desc
    notifications.sort(key=lambda x: x["created_at"], reverse=True)
    
    return notifications[:10]


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

    return {
        "balance": float(account.balance), 
        "reserved_balance": float(account.reserved_balance or 0.0),
        "user_id": user_id
    }


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
    """Get Kafka topics status (Admin only)."""
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


def _validate_p2p_transfer(
    transfer: P2PTransferRequest,
    current_user: User,
    db: Session
) -> User:
    """Validates the transfer request and returns the recipient user."""
    # Recipient Lookup
    recipient = db.query(User).filter(User.email == transfer.recipient_email).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    return recipient

def _execute_p2p_balances(
    db: Session,
    sender_id: int,
    recipient_id: int,
    amount: Decimal
) -> Tuple[Account, Account]:
    """Locks accounts and updates balances atomically."""
    # Order by ID to prevent deadlocks.
    # We query sequentially ensuring order based on ID to avoid deadlock if concurrent transfers happen in opposite directions.
    # Ideally we should grab locks in ID order.

    first_id, second_id = sorted([sender_id, recipient_id])

    # We must fetch them in order.
    # Note: original code fetched by user_id.
    # Since account:user is 1:1, we can query Account where user_id is X.

    # To properly lock, we need to find which account corresponds to which user ID first?
    # Or just rely on the fact that we sort the user IDs and query accounts for those user IDs in that order.

    acc1 = db.query(Account).filter(Account.user_id == first_id).with_for_update().first()
    acc2 = db.query(Account).filter(Account.user_id == second_id).with_for_update().first()

    if first_id == sender_id:
        sender_account = acc1
        recipient_account = acc2
    else:
        sender_account = acc2
        recipient_account = acc1

    if not sender_account or sender_account.balance < amount:
        raise HTTPException(
            status_code=400, detail="Insufficient funds for this transfer."
        )

    if not recipient_account:
        raise HTTPException(status_code=404, detail="Recipient account not found")

    sender_account.balance -= amount
    recipient_account.balance += amount

    return sender_account, recipient_account

def _create_p2p_transactions(
    db: Session,
    sender_account_id: int,
    recipient_account_id: int,
    amount: Decimal,
    recipient_email: str,
    sender_email: str,
    idempotency_key: Optional[str],
    client_ip: str,
    user_agent: str,
    commentary: Optional[str] = None,
    payment_request_id: Optional[int] = None
) -> Tuple[str, str, str]:
    """Creates transaction records for sender and recipient."""
    tx_id_parent = str(uuid.uuid4())
    tx_id_sender = str(uuid.uuid4())
    tx_id_recipient = str(uuid.uuid4())

    sender_tx = Transaction(
        id=tx_id_sender,
        parent_id=tx_id_parent,
        account_id=sender_account_id,
        amount=-amount,
        category="Transfer",
        merchant=f"Transfer to {recipient_email}",
        status="pending",
        transaction_type="transfer",
        transaction_side="DEBIT",
        idempotency_key=idempotency_key,
        ip_address=client_ip,
        user_agent=user_agent,
        commentary=commentary,
        payment_request_id=payment_request_id
    )

    recipient_tx = Transaction(
        id=tx_id_recipient,
        parent_id=tx_id_parent,
        account_id=recipient_account_id,
        amount=amount,
        category="Transfer",
        merchant=f"Received from {sender_email}",
        status="pending",
        transaction_type="transfer",
        transaction_side="CREDIT",
        idempotency_key=idempotency_key,
        ip_address=client_ip,
        user_agent=user_agent,
        commentary=commentary,
        payment_request_id=payment_request_id
    )

    db.add(sender_tx)
    db.add(recipient_tx)

    return tx_id_parent, tx_id_sender, tx_id_recipient

def _create_p2p_outbox_entries(
    db: Session,
    sender_account_id: int,
    recipient_account_id: int,
    amount: Decimal,
    sender_email: str,
    recipient_email: str,
    tx_id_parent: str,
    tx_id_sender: str,
    tx_id_recipient: str,
    commentary: Optional[str] = None
):
    """Creates outbox entries for Kafka processing."""
    sender_payload = {
        "transaction_id": tx_id_sender,
        "parent_id": tx_id_parent,
        "account_id": sender_account_id,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": -float(amount),
        "category": "Transfer",
        "merchant": f"Transfer to {recipient_email}",
        "transaction_type": "transfer",
        "transaction_side": "DEBIT",
        "status": "pending",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "commentary": commentary
    }

    recipient_payload = {
        "transaction_id": tx_id_recipient,
        "parent_id": tx_id_parent,
        "account_id": recipient_account_id,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": float(amount),
        "category": "Transfer",
        "merchant": f"Received from {sender_email}",
        "transaction_type": "transfer",
        "transaction_side": "CREDIT",
        "status": "pending",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "commentary": commentary
    }

    db.add(Outbox(event_type="p2p.sender", payload=sender_payload))
    db.add(Outbox(event_type="p2p.recipient", payload=recipient_payload))


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

    # 2. Validation & Recipient Lookup
    recipient = _validate_p2p_transfer(transfer, current_user, db)

    # Validate Payment Request if paying one
    payment_request = None
    if transfer.payment_request_id:
        payment_request = db.query(PaymentRequest).filter(PaymentRequest.id == transfer.payment_request_id).first()
        if not payment_request:
            raise HTTPException(status_code=404, detail="Payment request not found")
        # Ensure that the current_user is the target of the request
        if payment_request.target_email != current_user.email:
             raise HTTPException(status_code=403, detail="You are not the target of this payment request")
        if payment_request.status not in ["pending_target", "pending_requester"]:
             raise HTTPException(status_code=400, detail="Payment request is no longer active")
        # Ensure that the amount paid is at least the requested amount
        if transfer.amount < payment_request.amount:
            raise HTTPException(status_code=400, detail=f"Transfer amount must be at least the requested amount (${payment_request.amount})")

    try:
        # 3. Atomic Locking & Balance Verification (ACID)
        sender_account, recipient_account = _execute_p2p_balances(
            db, current_user.id, recipient.id, transfer.amount
        )

        # 4. Create Transaction Records
        tx_id_parent, tx_id_sender, tx_id_recipient = _create_p2p_transactions(
            db,
            sender_account.id,
            recipient_account.id,
            transfer.amount,
            recipient.email,
            current_user.email,
            transfer.idempotency_key,
            client_ip,
            user_agent,
            transfer.commentary,
            transfer.payment_request_id
        )

        # 5. Create Outbox Entries
        _create_p2p_outbox_entries(
            db,
            sender_account.id,
            recipient_account.id,
            transfer.amount,
            current_user.email,
            recipient.email,
            tx_id_parent,
            tx_id_sender,
            tx_id_recipient,
            transfer.commentary
        )

        # Mark payment request as paid if one was linked
        if payment_request:
            payment_request.status = "paid"
            payment_request.updated_at = datetime.datetime.utcnow()

        # 6. Finalize Idempotency Key
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


# --- Payment Requests Endpoints ---

@app.post("/api/v1/requests/create")
async def create_payment_request(
    request_data: PaymentRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    if request_data.target_email == current_user.email:
        raise HTTPException(status_code=400, detail="Cannot request money from yourself")
        
    target_user = db.query(User).filter(User.email == request_data.target_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    new_request = PaymentRequest(
        requester_id=current_user.id,
        target_email=request_data.target_email,
        amount=request_data.amount,
        purpose=request_data.purpose,
        status="pending_target"
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return {"status": "success", "request_id": new_request.id}


@app.get("/api/v1/requests")
async def get_payment_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch requests where user is requester or target
    requests = db.query(PaymentRequest).filter(
        (PaymentRequest.requester_id == current_user.id) | 
        (PaymentRequest.target_email == current_user.email)
    ).order_by(PaymentRequest.updated_at.desc()).all()
    
    # Enrich with requester info
    result = []
    for req in requests:
        requester = db.query(User).filter(User.id == req.requester_id).first()
        result.append({
            "id": req.id,
            "requester_id": req.requester_id,
            "requester_name": f"{requester.first_name} {requester.last_name}" if requester else "Unknown",
            "requester_email": requester.email if requester else "unknown",
            "target_email": req.target_email,
            "amount": float(req.amount),
            "purpose": req.purpose,
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "updated_at": req.updated_at.isoformat()
        })
        
    return result


@app.post("/api/v1/requests/{request_id}/counter")
async def counter_payment_request(
    request_id: int,
    counter_data: PaymentRequestCounter,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if counter_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Counter amount must be greater than 0")

    req = db.query(PaymentRequest).filter(PaymentRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found")

    is_requester = req.requester_id == current_user.id
    is_target = req.target_email == current_user.email
    
    if not is_requester and not is_target:
        raise HTTPException(status_code=403, detail="Not authorized to modify this request")
        
    if req.status not in ["pending_target", "pending_requester"]:
        raise HTTPException(status_code=400, detail=f"Request cannot be modified in state: {req.status}")

    # Enforce turns
    if is_target and req.status != "pending_target":
        raise HTTPException(status_code=400, detail="It is not your turn to counter-offer")
    if is_requester and req.status != "pending_requester":
        raise HTTPException(status_code=400, detail="It is not your turn to counter-offer")

    req.amount = counter_data.amount
    # Flip the status depending on who just countered
    req.status = "pending_requester" if is_target else "pending_target"
    req.updated_at = datetime.datetime.utcnow()
    
    db.commit()
    return {"status": "success", "request_id": req.id, "new_amount": float(req.amount), "new_status": req.status}


@app.post("/api/v1/requests/{request_id}/decline")
async def decline_payment_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(PaymentRequest).filter(PaymentRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found")

    if req.requester_id != current_user.id and req.target_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to modify this request")
        
    if req.status not in ["pending_target", "pending_requester"]:
        raise HTTPException(status_code=400, detail=f"Request cannot be modified in state: {req.status}")

    req.status = "declined"
    req.updated_at = datetime.datetime.utcnow()
    
    db.commit()
    return {"status": "success", "request_id": req.id, "new_status": req.status}
def _calculate_next_run_at(start_date: datetime.datetime, frequency: str, interval: str = None) -> datetime.datetime:
    # A simplified implementation for the immediate next execution
    # In a full system, this would apply cron-like interval math
    return start_date

@app.post("/api/v1/transfers/scheduled")
async def create_scheduled_transfer(
    transfer: ScheduledTransferCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Scheduled Limit check (e.g., max $5000 per scheduled transfer)
    if transfer.amount > 5000:
        raise HTTPException(status_code=400, detail="Amount exceeds maximum scheduled transfer limit of $5000.")

    # Validation: start date in future
    if transfer.start_date.date() <= datetime.datetime.utcnow().date():
        raise HTTPException(status_code=400, detail="Start date must be in the future.")

    ik = transfer.idempotency_key or str(uuid.uuid4())
    existing_key = db.query(IdempotencyKey).filter(
        IdempotencyKey.key == ik,
        IdempotencyKey.user_id == current_user.id
    ).first()
    if existing_key:
        return existing_key.response_body

    try:
        sender_account = db.query(Account).filter(Account.user_id == current_user.id).with_for_update().first()
        if not sender_account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Reserve balance logic
        if transfer.reserve_amount:
            if sender_account.balance < transfer.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds to reserve amount.")
            sender_account.balance -= transfer.amount
            sender_account.reserved_balance += transfer.amount

        next_run = _calculate_next_run_at(transfer.start_date, transfer.frequency, transfer.frequency_interval)

        new_scheduled_payment = ScheduledPayment(
            user_id=current_user.id,
            recipient_email=transfer.recipient_email,
            amount=transfer.amount,
            frequency=transfer.frequency,
            frequency_interval=transfer.frequency_interval,
            start_date=transfer.start_date,
            end_condition=transfer.end_condition,
            end_date=transfer.end_date,
            target_payments=transfer.target_payments,
            next_run_at=next_run,
            status="Active",
            idempotency_key=ik,
            reserve_amount=transfer.reserve_amount
        )
        db.add(new_scheduled_payment)
        
        response_body = {"status": "success", "message": "Transfer scheduled successfully."}
        db.add(IdempotencyKey(
            key=ik,
            user_id=current_user.id,
            response_code=200,
            response_body=response_body
        ))
        
        db.commit()
        db.refresh(new_scheduled_payment)
        
        return {"status": "success", "scheduled_payment_id": new_scheduled_payment.id}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Scheduled Transfer failed: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@app.get("/api/v1/transfers/scheduled", response_model=List[ScheduledPaymentResponse])
async def get_scheduled_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all scheduled payments for the current user."""
    payments = db.query(ScheduledPayment).filter(
        ScheduledPayment.user_id == current_user.id
    ).order_by(ScheduledPayment.id.desc()).all()
    
    return payments

@app.post("/api/v1/transfers/scheduled/{payment_id}/cancel")
async def cancel_scheduled_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a scheduled payment."""
    payment = db.query(ScheduledPayment).filter(
        ScheduledPayment.id == payment_id,
        ScheduledPayment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled payment not found")
        
    if payment.status != "Active":
        raise HTTPException(status_code=400, detail=f"Payment is already {payment.status}")
        
    payment.status = "Cancelled"
    db.commit()
    
    return {"status": "success", "message": "Scheduled payment cancelled"}


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


# --- Contacts Endpoints ---

@app.get("/api/v1/contacts", response_model=List[ContactResponse])
async def get_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contacts = db.query(Contact).filter(Contact.user_id == current_user.id).order_by(Contact.contact_name).all()
    return contacts

@app.post("/api/v1/contacts", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not contact_data.contact_name.strip() or not contact_data.contact_email.strip():
        raise HTTPException(status_code=400, detail="Name and Email are required")
        
    # Check if duplicate email exists for user
    existing = db.query(Contact).filter(
        Contact.user_id == current_user.id, 
        Contact.contact_email == contact_data.contact_email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this email already exists")

    new_contact = Contact(
        user_id=current_user.id,
        contact_name=contact_data.contact_name,
        contact_email=contact_data.contact_email
    )
    
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    return new_contact

@app.delete("/api/v1/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == current_user.id
    ).first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    db.delete(contact)
    db.commit()
    
    return {"status": "success"}

# --- Admin Endpoints ---


class QueryRequest(BaseModel):
    query: str
    params: Dict[str, Any] = {}


def _validate_sql_query(query: str):
    """Validates SQL query for safety."""
    query_upper = query.strip().upper()
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


def _execute_clickhouse_query(request: QueryRequest) -> Tuple[List, List]:
    """Executes a query against ClickHouse."""
    _validate_sql_query(request.query)

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
    # Only allow params that are used in actual placeholder syntax {param}
    # Note: clickhouse_connect supports parameter binding
    result = ch_client.query(request.query, parameters=request.params)
    return result.result_rows, result.column_names


def _execute_postgres_query(request: QueryRequest, db: Session) -> Tuple[List, List]:
    """Executes a query against PostgreSQL."""
    _validate_sql_query(request.query)

    # Execute PostgreSQL query with parameter binding to prevent SQL injection
    result = db.execute(text(request.query), request.params)
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

        if source == "clickhouse":
            data, columns = _execute_clickhouse_query(request)
        elif source == "postgres":
            data, columns = _execute_postgres_query(request, db)
        elif source == "kafka":
            data, columns = _execute_kafka_query(request)
        else:
            raise HTTPException(status_code=400, detail="Invalid data source specified")

        execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000

        return {
            "columns": columns,
            "data": data,
            "rowCount": len(data),
            "executionTime": round(execution_time, 2),
        }

    except HTTPException:
        raise
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
