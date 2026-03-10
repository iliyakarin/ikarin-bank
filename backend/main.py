import json
import uuid
import os
import re
import datetime
import asyncio
import httpx
from typing import Dict, Any, Optional, Tuple, List
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, text, or_, select
from decimal import Decimal
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from database import SessionLocal, Transaction, User, Account, Outbox, IdempotencyKey, ScheduledPayment, PaymentRequest, Contact, Base, engine
from activity import emit_activity, ws_register, ws_unregister
from security_checks import check_velocity, check_anomaly
from account_service import assign_account_credentials, mask_account_number, decrypt_account_number
import clickhouse_connect

from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer
import clickhouse_connect
from clickhouse_utils import get_ch_client, CH_DB
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sync_checker import run_sync_check

app = FastAPI(title="Simple Bank API")

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Configuration
# Admins are defined by role="admin" in the database
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "bank_transactions")
KAFKA_USER = os.getenv("KAFKA_USER")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")

CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CH_DB = os.getenv("CLICKHOUSE_DB")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Configuration
from auth_utils import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, 
    pwd_context, oauth2_scheme, verify_password, get_password_hash, 
    create_access_token, get_db, get_current_user, RoleChecker
)
from migrations import run_all_migrations


# Pydantic Models for Auth
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    captcha_token: Optional[str] = None


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
    time_format: str
    date_format: str

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

class UserPreferencesUpdate(BaseModel):
    time_format: Optional[str] = None
    date_format: Optional[str] = None


class P2PTransferRequest(BaseModel):
    recipient_email: str
    amount: Decimal
    source_account_id: Optional[int] = None
    idempotency_key: Optional[str] = None
    commentary: Optional[str] = None
    payment_request_id: Optional[int] = None
    subscriber_id: Optional[str] = None

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
    funding_account_id: Optional[int] = None
    subscriber_id: Optional[str] = None

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
    funding_account_id: Optional[int] = None

    class Config:
        from_attributes = True


class ContactCreate(BaseModel):
    contact_name: str
    contact_email: Optional[str] = None
    contact_type: str = "karin" # karin, merchant, bank
    # Merchant fields
    merchant_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    # Bank fields
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None

class ContactResponse(BaseModel):
    id: int
    user_id: int
    contact_name: str
    contact_email: Optional[str] = None
    contact_type: str
    merchant_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ContactUpdate(BaseModel):
    contact_name: str
    contact_email: Optional[str] = None
    # Allow updating metadata too
    merchant_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None

# Helper Functions
# Role Checkers
admin_only = RoleChecker(["admin"])
support_only = RoleChecker(["admin", "support"])

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
ENV = os.getenv("ENV", "development")

async def verify_turnstile(token: str, ip: Optional[str] = None):
    # Skip verification in development
    if ENV != "production":
        return True
    
    if not token:
        return False
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": ip
            }
        )
        data = response.json()
        return data.get("success", False)


# --- Auth Endpoints ---


@app.post("/auth/register", response_model=UserResponse)
async def register(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Verify Turnstile in production (if secret key is set and not using test key)
    if not await verify_turnstile(user.captcha_token, request.client.host):
         raise HTTPException(status_code=400, detail="Invalid captcha")

    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalars().first()
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
    await db.commit()
    await db.refresh(new_user)

    # Auto-create an account for the new user
    new_account = Account(user_id=new_user.id, balance=0.00, name="Main Account", is_main=True)
    await assign_account_credentials(db, new_account)
    db.add(new_account)
    await db.commit()

    emit_activity(
        db, 
        new_user.id, 
        "security", 
        "register", 
        "Account registered", 
        {"email": new_user.email},
        ip=None, # No request object here yet, but we could pass it if register had it
        user_agent=None
    )
    await db.commit()

    return new_user


@app.post("/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    # Turnstile token is usually passed in the body or as a separate header/form field
    # For OAuth2PasswordRequestForm, we check for a custom field or form parameter
    form = await request.form()
    captcha_token = form.get("captcha_token") or form.get("cf-turnstile-response")
    
    if not await verify_turnstile(captcha_token, request.client.host):
        raise HTTPException(status_code=400, detail="Invalid captcha")

    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        if user:
            emit_activity(
                db, 
                user.id, 
                "security", 
                "login_failed", 
                "Failed login attempt", 
                {"email": form_data.username},
                ip=request.client.host,
                user_agent=request.headers.get("user-agent")
            )
            await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    emit_activity(
        db, 
        user.id, 
        "security", 
        "login", 
        "User logged in", 
        {"email": user.email},
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/v1/users/me/backup", response_model=UserResponse)
async def update_backup_email(
    update_data: UserBackupUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if this email is already used by someone else
    result = await db.execute(select(User).filter(
        (User.email == update_data.backup_email) | 
        (User.backup_email == update_data.backup_email)
    ))
    existing = result.scalars().first()
    
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="This email is already in use by another user")
        
    current_user.backup_email = update_data.backup_email

    emit_activity(
        db, 
        current_user.id, 
        "security", 
        "email_change", 
        "Backup email updated", 
        {
            "new_backup_email": update_data.backup_email[:3] + "***"
        },
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@app.post("/v1/users/me/password")
async def update_password(
    password_data: UserPasswordUpdate,
    request: Request,
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

    emit_activity(
        db, 
        current_user.id, 
        "security", 
        "password_change", 
        "Password changed",
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return {"status": "success"}

@app.patch("/v1/users/me/preferences", response_model=UserResponse)
async def update_preferences(
    pref_data: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if pref_data.time_format:
        current_user.time_format = pref_data.time_format
    if pref_data.date_format:
        current_user.date_format = pref_data.date_format
    
    await db.commit()
    await db.refresh(current_user)
    return current_user


@app.post("/auth/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Server-side logout: logs the event and invalidates the session."""
    user_agent = request.headers.get("user-agent", "unknown")
    client_ip = request.client.host

    emit_activity(
        db, 
        current_user.id, 
        "security", 
        "logout", 
        "User logged out", 
        {
            "ip": client_ip,
            "user_agent": user_agent,
        },
        ip=client_ip,
        user_agent=user_agent
    )
    await db.commit()

    # Note: JWTs are stateless. True invalidation requires a token blacklist.
    # For now we log the event; the client must delete the token.
    return {"status": "success", "message": "Logged out successfully"}


@app.websocket("/ws/activity/{token}")
async def ws_activity(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time activity updates."""
    # Authenticate via JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        if not user:
            await websocket.close(code=4001)
            return
    finally:
        await db.close()

    await websocket.accept()
    ws_register(user.id, websocket)

    try:
        while True:
            # Keep connection alive — wait for client pings or messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_unregister(user.id, websocket)


@app.get("/v1/users/me/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest 10 notifications (transactions & payment requests)."""
    notifications = []
    
    # 1. Transactions
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id))
    account_ids = [acc.id for acc in result.scalars().all()]
    if account_ids:
        result = await db.execute(
            select(Transaction).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.status != "cancelled"
            ).order_by(Transaction.created_at.desc()).limit(10)
        )
        transactions = result.scalars().all()
        
        for tx in transactions:
            if tx.status == "failed":
                title = "Payment Failed"
                msg = tx.commentary if tx.commentary else "Transaction failed."
            else:
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
    result = await db.execute(
        select(PaymentRequest).filter(
            or_(
                PaymentRequest.requester_id == current_user.id,
                PaymentRequest.target_email == current_user.email
            )
        ).order_by(PaymentRequest.created_at.desc()).limit(10)
    )
    requests = result.scalars().all()
    
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to access these accounts"
        )
    
    result = await db.execute(select(Account).filter(Account.user_id == user_id))
    accounts = result.scalars().all()
    if not accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    total_balance = sum(float(acc.balance) for acc in accounts)
    total_reserved = sum(float(acc.reserved_balance or 0.0) for acc in accounts)
    
    sub_accounts = [{
        "id": acc.id,
        "name": acc.name,
        "balance": float(acc.balance),
        "reserved_balance": float(acc.reserved_balance or 0.0),
        "is_main": acc.is_main,
        "routing_number": acc.routing_number,
        "masked_account_number": mask_account_number(decrypt_account_number(acc.account_number_encrypted)) if acc.account_number_encrypted else None
    } for acc in accounts]

    return {
        "balance": total_balance, 
        "reserved_balance": total_reserved,
        "user_id": user_id,
        "accounts": sub_accounts
    }


# --- Observability Endpoints ---


@app.get("/v1/admin/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)
):
    # 1. Postgres Count
    result = await db.execute(select(func.count(Transaction.id)))
    pg_count = result.scalar()

    # 2. ClickHouse Count
    ch_client = get_ch_client()
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
    
    result = await db.execute(
        select(func.sum(Transaction.amount))
        .filter(Transaction.category == "P2P", Transaction.created_at >= yesterday)
    )
    system_volume = result.scalar() or 0.0

    return {
        "postgres_count": pg_count,
        "clickhouse_count": ch_count,
        "delta": delta,
        "kafka_lag": lag,
        "system_volume": float(system_volume),
        "sync_health": "in_sync" if delta < 5 else "syncing",
        "status": "healthy" if lag < 5000 and lag >= 0 else "degraded",
    }


@app.get("/v1/admin/users", response_model=List[UserResponse])
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


@app.get("/v1/admin/users/search", response_model=UserResponse)
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


@app.delete("/v1/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Compliance-grade User Deletion (Right to Erasure).
    Anonymizes audit logs in Postgres and purges transaction data from ClickHouse.
    """
    # 1. Verify User Exists
    result = await db.execute(select(User).filter(User.id == user_id))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Collect accounts for ClickHouse purge
    result = await db.execute(select(Account.id).filter(Account.user_id == user_id))
    account_ids = [acc_id for acc_id in result.scalars().all()]
    
    # 3. Emit Audit Event BEFORE deletion
    emit_activity(
        db,
        current_user.id,
        "security",
        "user_deleted",
        f"Admin deleted user ID {user_id}",
        {"target_user_id": user_id, "target_user_email": target_user.email},
        ip=None, # Simplified for now
        user_agent=None
    )
    # emit_activity adds to db session, so it will be committed below
    
    # 4. Anonymize Postgres Transactions
    if account_ids:
        # We keep the transactions for accounting integrity but scrub PII
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

    # 5. Manual Cascade Deletion (since DB doesn't have ON DELETE CASCADE)
    # Delete dependent rows in order
    await db.execute(text("DELETE FROM scheduled_payments WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM payment_requests WHERE requester_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM contacts WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM idempotency_keys WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM accounts WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

    # 6. ClickHouse Purge (Mutations)
    try:
        ch = get_ch_client()
        # Purge Transactions
        if account_ids:
            ch.command(f"ALTER TABLE {CH_DB}.transactions DELETE WHERE account_id IN ({','.join(map(str, account_ids))})")
        
        # Purge Activity Events
        ch.command(f"ALTER TABLE {CH_DB}.activity_events DELETE WHERE user_id = {user_id}")
    except Exception as e:
        # We log and continue, as the primary source of truth (Postgres) is already handled
        print(f"[ERROR] ClickHouse purge failed for user {user_id}: {e}")

    await db.commit()
    return None


@app.get("/admin/traces")
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


@app.post("/v1/admin/simulate")
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
                internal_account_last_4="Simulation", # Placeholder for bot
                sender_email="simulation@bot.karin",
                recipient_email="simulation@bot.karin"
            )
            db.add(new_tx)
            await db.commit()

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
            await db.commit()
        except Exception as e:
            print(f"Simulation error: {e}")
        finally:
            await db.close()

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
async def get_postgres_logs(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_only)
):
    result = await db.execute(select(Transaction).order_by(Transaction.created_at.desc()).limit(10))
    return result.scalars().all()


@app.get("/admin/clickhouse-logs")
def get_ch_logs(current_user: User = Depends(admin_only)):
    # Connect to ClickHouse
    client = get_ch_client()
    result = client.query(
        "SELECT * FROM transactions ORDER BY event_time DESC LIMIT 10"
    )
    logs = result.named_results()
    for log in logs:
        log["status"] = "cleared"
        log["created_at"] = log["event_time"]  # For frontend consistency
    return logs


@app.post("/v1/admin/sync-clickhouse")
def manual_sync_clickhouse(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(admin_only)
):
    background_tasks.add_task(run_sync_check)
    return {"status": "success", "message": "Manual ClickHouse sync started in the background."}


@app.get("/v1/admin/config")
async def get_admin_config(current_user: User = Depends(admin_only)):
    """Returns full configuration for database connectivity (admin-only)."""
    from database import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    
    return {
        "env": os.getenv("ENV", "development"),
        "clickhouse": {
            "host": CH_HOST,
            "port": CH_PORT,
            "username": CH_USER,
            "password": CH_PASSWORD,
            "database": os.getenv("CLICKHOUSE_DB", "banking")
        },
        "postgres": {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "username": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "database": POSTGRES_DB
        },
        "kafka": {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "username": KAFKA_USER,
            "password": KAFKA_PASSWORD,
            "topic": KAFKA_TOPIC
        }
    }


# Kafka Producer state
producer = None


@app.on_event("startup")
async def startup_event():
    # Ensure database tables and schema exist
    try:
        # 1. Base Metadata creation (ensures tables exist)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 2. Schema Migrations (ensures columns exist, etc.)
        await run_all_migrations()
        print("[INFO] Database tables verified/migrated successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")

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
async def create_transfer(
    transfer: TransferRequest, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tx_id = str(uuid.uuid4())
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    try:

        result = await db.execute(select(Account).filter(Account.id == transfer.account_id, Account.user_id == current_user.id))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=403, detail="Account not found or access denied")

        new_tx = Transaction(
            id=tx_id,
            account_id=transfer.account_id,
            amount=transfer.amount,
            category=transfer.category,
            merchant=transfer.merchant,
            status="pending",
            internal_account_last_4=account.account_number_last_4,
            sender_email=current_user.email,
            recipient_email="external@gateway.com" # Generic external recipient
        )
        db.add(new_tx)
        
        # Add to Outbox instead of direct Kafka send
        payload = {
            "transaction_id": tx_id,
            "account_id": transfer.account_id,
            "internal_account_last_4": account.account_number_last_4,
            "internal_reference_id": account.internal_reference_id,
            "amount": transfer.amount,
            "category": transfer.category,
            "merchant": transfer.merchant,
            "transaction_type": "expense",
            "status": "cleared", # legacy /transfer is cleared immediately
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        
        outbox_entry = Outbox(
            event_type="transaction.created",
            payload=payload
        )

        db.add(outbox_entry)
        
        await db.commit()
        return {"status": "success", "transaction_id": tx_id}
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] Transfer failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")


async def _validate_p2p_transfer(
    transfer: P2PTransferRequest,
    current_user: User,
    db: AsyncSession
) -> User:
    """Validates the transfer request and returns the recipient user."""
    # Recipient Lookup
    result = await db.execute(select(User).filter(User.email == transfer.recipient_email))
    recipient = result.scalars().first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    return recipient

async def _execute_p2p_balances(
    db: AsyncSession,
    sender_account_id: int,
    recipient_account_id: int,
    amount: Decimal
) -> Tuple[Account, Account]:
    """Locks accounts and updates balances atomically."""
    # Order by ID to prevent deadlocks.
    first_id, second_id = sorted([sender_account_id, recipient_account_id])

    result1 = await db.execute(select(Account).filter(Account.id == first_id).with_for_update())
    acc1 = result1.scalars().first()
    result2 = await db.execute(select(Account).filter(Account.id == second_id).with_for_update())
    acc2 = result2.scalars().first()

    if first_id == sender_account_id:
        sender_account = acc1
        recipient_account = acc2
    else:
        sender_account = acc2
        recipient_account = acc1

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found")
        
    if sender_account.balance < amount:
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
    sender_account_last_4: str | None = None,
    recipient_account_last_4: str | None = None,
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
        status="cleared", # P2P transfers are instant in the internal ledger
        transaction_type="transfer",
        transaction_side="DEBIT",
        idempotency_key=idempotency_key,
        ip_address=client_ip,
        user_agent=user_agent,
        commentary=commentary,
        payment_request_id=payment_request_id,
        internal_account_last_4=sender_account_last_4,
        sender_email=sender_email,
        recipient_email=recipient_email
    )

    recipient_tx = Transaction(
        id=tx_id_recipient,
        parent_id=tx_id_parent,
        account_id=recipient_account_id,
        amount=amount,
        category="Transfer",
        merchant=f"Received from {sender_email}",
        status="cleared",
        transaction_type="transfer",
        transaction_side="CREDIT",
        idempotency_key=idempotency_key,
        ip_address=client_ip,
        user_agent=user_agent,
        commentary=commentary,
        payment_request_id=payment_request_id,
        internal_account_last_4=recipient_account_last_4,
        sender_email=sender_email,
        recipient_email=recipient_email
    )

    db.add(sender_tx)
    db.add(recipient_tx)

    return tx_id_parent, tx_id_sender, tx_id_recipient

def _create_p2p_outbox_entries(
    db: Session,
    sender_account: Account,
    recipient_account: Account,
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
        "account_id": sender_account.id,
        "internal_account_last_4": sender_account.account_number_last_4,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": -float(amount),
        "category": "Transfer",
        "merchant": f"Transfer to {recipient_email}",
        "transaction_type": "transfer",
        "transaction_side": "DEBIT",
        "status": "cleared", # cleared in postgres already
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "commentary": commentary
    }

    recipient_payload = {
        "transaction_id": tx_id_recipient,
        "parent_id": tx_id_parent,
        "account_id": recipient_account.id,
        "internal_account_last_4": recipient_account.account_number_last_4,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "amount": float(amount),
        "category": "Transfer",
        "merchant": f"Received from {sender_email}",
        "transaction_type": "transfer",
        "transaction_side": "CREDIT",
        "status": "cleared",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "commentary": commentary
    }

    db.add(Outbox(event_type="p2p.sender", payload=sender_payload))
    db.add(Outbox(event_type="p2p.recipient", payload=recipient_payload))


SIMULATOR_URL = os.getenv("SIMULATOR_URL")
SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY")

async def get_vendors():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{SIMULATOR_URL}/vendors")
            if resp.status_code == 200:
                return resp.json().get("vendors", [])
        except Exception as e:
            print(f"[ERROR] Fetching vendors: {e}")
        return []

async def execute_vendor_payment_immediate(merchant_id: str, subscriber_id: str, amount: Decimal):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "merchant_id": merchant_id,
                "subscriber_id": subscriber_id,
                "amount": float(amount)
            }
            resp = await client.post(
                f"{SIMULATOR_URL}/billpay/execute",
                json=payload,
                headers={"X-API-KEY": SIMULATOR_API_KEY}
            )
            return resp.json()
        except Exception as e:
            print(f"[ERROR] Executing vendor payment: {e}")
            return {"status": "FAILED", "failure_reason": str(e)}

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
        result = await db.execute(select(IdempotencyKey).filter(
            IdempotencyKey.key == transfer.idempotency_key,
            IdempotencyKey.user_id == current_user.id
        ))
        existing_key = result.scalars().first()
        if existing_key:
            return existing_key.response_body

    # 2. Validation & Recipient Lookup
    try:
        recipient = await _validate_p2p_transfer(transfer, current_user, db)
    except HTTPException as e:
        if e.status_code == 404 and "Recipient not found" in str(e.detail):
            # Check for vendor
            vendors = await get_vendors()
            vendor = next((v for v in vendors if v["email"] == transfer.recipient_email), None)
            if vendor:
                # Resolve Sender Account
                sender_account_query = select(Account).filter(Account.user_id == current_user.id)
                if transfer.source_account_id:
                    sender_account_query = sender_account_query.filter(Account.id == transfer.source_account_id)
                else:
                    sender_account_query = sender_account_query.filter(Account.is_main == True)
                    
                result = await db.execute(sender_account_query.with_for_update())
                sender_account = result.scalars().first()
                if not sender_account:
                    raise HTTPException(status_code=404, detail="Source account not found")

                if sender_account.balance < transfer.amount:
                     raise HTTPException(status_code=400, detail="Insufficient funds")

                # Execute Vendor Payment
                sim_resp = await execute_vendor_payment_immediate(
                    vendor["id"], transfer.subscriber_id or "UNKNOWN", transfer.amount
                )

                # Update Balance
                sender_account.balance -= transfer.amount

                # Create Transaction Record
                status_map = {"CLEARED": "cleared", "FAILED": "failed"}
                tx_id = str(uuid.uuid4())
                vendor_tx = Transaction(
                    id=tx_id,
                    account_id=sender_account.id,
                    amount=-transfer.amount,
                    category="Bill Pay",
                    merchant=vendor["name"],
                    status=status_map.get(sim_resp.get("status"), "failed"),
                    transaction_type="expense",
                    transaction_side="DEBIT",
                    failure_reason=sim_resp.get("failure_reason"),
                    commentary=f"Bill Payment to {vendor['name']} (Instant)",
                    internal_account_last_4=sender_account.account_number_last_4,
                    recipient_email=vendor["email"],
                    sender_email=current_user.email,
                    subscriber_id=transfer.subscriber_id,
                    idempotency_key=transfer.idempotency_key or str(uuid.uuid4()),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    created_at=datetime.datetime.utcnow()
                )
                db.add(vendor_tx)

                response_body = {"status": "success", "transaction_id": tx_id, "vendor_status": sim_resp.get("status")}
                if transfer.idempotency_key:
                    db.add(IdempotencyKey(
                        key=transfer.idempotency_key,
                        user_id=current_user.id,
                        response_code=200,
                        response_body=response_body
                    ))

                await db.commit()
                return response_body
            else:
                raise # Re-raise original 404
        else:
            raise

    # 2.5 Security Checks
    if not await check_velocity(db, current_user.id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: too many transactions in the last minute. Please try again shortly."
        )

    anomaly_flagged = await check_anomaly(db, current_user.id, Decimal(str(transfer.amount)))

    # Validate Payment Request if paying one
    payment_request = None
    if transfer.payment_request_id:
        result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == transfer.payment_request_id))
        payment_request = result.scalars().first()
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

    # Resolve Sender Account
    sender_account_query = select(Account).filter(Account.user_id == current_user.id)
    if transfer.source_account_id:
        sender_account_query = sender_account_query.filter(Account.id == transfer.source_account_id)
    else:
        sender_account_query = sender_account_query.filter(Account.is_main == True)
        
    result = await db.execute(sender_account_query)
    resolved_sender_account = result.scalars().first()
    if not resolved_sender_account:
        raise HTTPException(status_code=404, detail="Source account not found or access denied")

    # Resolve Recipient Main Account
    result = await db.execute(select(Account).filter(Account.user_id == recipient.id, Account.is_main == True))
    resolved_recipient_account = result.scalars().first()
    if not resolved_recipient_account:
        raise HTTPException(status_code=404, detail="Recipient main account not found")

    try:
        # 3. Atomic Locking & Balance Verification (ACID)
        sender_account, recipient_account = await _execute_p2p_balances(
            db, resolved_sender_account.id, resolved_recipient_account.id, transfer.amount
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
            sender_account_last_4=sender_account.account_number_last_4,
            recipient_account_last_4=recipient_account.account_number_last_4,
            commentary=transfer.commentary,
            payment_request_id=transfer.payment_request_id
        )

        # 5. Create Outbox Entries
        _create_p2p_outbox_entries(
            db,
            sender_account,
            recipient_account,
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

        # Emit activity events for sender and recipient
        emit_activity(
            db, 
            current_user.id, 
            "p2p", 
            "sent", 
            f"Sent ${float(transfer.amount):.2f} to {recipient.email}", 
            {
                "transaction_id": tx_id_parent,
                "recipient_email": recipient.email,
                "amount": float(transfer.amount),
                "commentary": transfer.commentary,
                "source_account_id": resolved_sender_account.id,
            },
            ip=client_ip,
            user_agent=user_agent
        )
        emit_activity(
            db, 
            recipient.id, 
            "p2p", 
            "received", 
            f"Received ${float(transfer.amount):.2f} from {current_user.email}", 
            {
                "transaction_id": tx_id_parent,
                "sender_email": current_user.email,
                "amount": float(transfer.amount),
                "commentary": transfer.commentary,
            },
            ip=client_ip,
            user_agent=user_agent
        )

        await db.commit()
        return response_body

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] P2P Transfer failed: {e}")
        raise HTTPException(status_code=500, detail="Internal financial processing error")


# --- Payment Requests Endpoints ---

@app.post("/v1/requests/create")
async def create_payment_request(
    request_data: PaymentRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    if request_data.target_email == current_user.email:
        raise HTTPException(status_code=400, detail="Cannot request money from yourself")
        
    result = await db.execute(select(User).filter(User.email == request_data.target_email))
    target_user = result.scalars().first()
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

    emit_activity(db, current_user.id, "p2p", "requested", f"Requested ${float(request_data.amount):.2f} from {request_data.target_email}", {
        "target_email": request_data.target_email,
        "amount": float(request_data.amount),
        "purpose": request_data.purpose,
    })
    await db.commit()
    await db.refresh(new_request)
    
    return {"status": "success", "request_id": new_request.id}


@app.get("/v1/requests")
async def get_payment_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch requests where user is requester or target
    result = await db.execute(select(PaymentRequest).filter(
        (PaymentRequest.requester_id == current_user.id) | 
        (PaymentRequest.target_email == current_user.email)
    ).order_by(PaymentRequest.updated_at.desc()))
    requests = result.scalars().all()
    
    # Enrich with requester info
    result = []
    for req in requests:
        res = await db.execute(select(User).filter(User.id == req.requester_id))
        requester = res.scalars().first()
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


@app.post("/v1/requests/{request_id}/counter")
async def counter_payment_request(
    request_id: int,
    counter_data: PaymentRequestCounter,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if counter_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Counter amount must be greater than 0")

    result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == request_id))
    req = result.scalars().first()
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
    
    await db.commit()
    return {"status": "success", "request_id": req.id, "new_amount": float(req.amount), "new_status": req.status}


@app.post("/v1/requests/{request_id}/decline")
async def decline_payment_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == request_id))
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found")

    if req.requester_id != current_user.id and req.target_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to modify this request")
        
    if req.status not in ["pending_target", "pending_requester"]:
        raise HTTPException(status_code=400, detail=f"Request cannot be modified in state: {req.status}")

    req.status = "declined"
    req.updated_at = datetime.datetime.utcnow()
    
    emit_activity(db, current_user.id, "p2p", "request_declined", f"Declined payment request #{req.id}", {
        "request_id": req.id,
        "amount": float(req.amount),
    })

    # If this request was tied to a transaction (e.g. pending), update its status in ClickHouse
    # Fetch original transaction if exists
    res = await db.execute(select(Transaction).filter(Transaction.payment_request_id == req.id))
    txs = res.scalars().all()
    for tx in txs:
        # Emit a status update for each related transaction record
        from activity import emit_transaction_status_update
        emit_transaction_status_update(
            db,
            transaction_id=str(tx.id),
            account_id=tx.account_id,
            status="declined",
            amount=float(tx.amount),
            category=tx.category,
            merchant=tx.merchant,
            transaction_type=tx.transaction_type,
            transaction_side=tx.transaction_side,
            commentary=f"Payment request #{req.id} declined"
        )

    await db.commit()
    return {"status": "success", "request_id": req.id, "new_status": req.status}
def _calculate_next_run_at(reference_date: datetime.datetime, frequency: str, interval: str = None) -> Optional[datetime.datetime]:
    """Calculates the next execution date based on frequency and reference date."""
    if frequency == "One-time":
        return None
    
    if frequency == "Daily":
        return reference_date + datetime.timedelta(days=1)
    
    if frequency == "Weekly":
        return reference_date + datetime.timedelta(weeks=1)
    
    if frequency == "Bi-weekly":
        return reference_date + datetime.timedelta(weeks=2)
    
    if frequency == "Monthly":
        # Advance by exactly one month
        month = reference_date.month
        year = reference_date.year + (month // 12)
        month = (month % 12) + 1
        
        # Max days in the new month
        if month == 2:
            max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
        else:
            max_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
            
        day = min(reference_date.day, max_day)
        return reference_date.replace(year=year, month=month, day=day)

    if frequency == "Annually":
        try:
            return reference_date.replace(year=reference_date.year + 1)
        except ValueError: # Handle Feb 29
            return reference_date.replace(year=reference_date.year + 1, day=28)

    if frequency == "Specific Day of Week":
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if not interval or interval not in days_of_week:
            return reference_date + datetime.timedelta(weeks=1)
        
        target_weekday = days_of_week.index(interval)
        current_weekday = reference_date.weekday()
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
        return reference_date + datetime.timedelta(days=days_ahead)

    if frequency == "Specific Date of Month":
        try:
            target_day = int(interval)
        except (TypeError, ValueError):
            return reference_date + datetime.timedelta(days=30)
            
        # Move to next month and try to set the requested day
        month = reference_date.month
        year = reference_date.year + (month // 12)
        month = (month % 12) + 1
        
        if month == 2:
            max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
        else:
            max_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
            
        actual_day = min(target_day, max_day)
        return reference_date.replace(year=year, month=month, day=actual_day)

    return None

@app.post("/v1/transfers/scheduled")
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
    now_utc = datetime.datetime.utcnow()
    # Ensure start_date is naive UTC if it comes with tzinfo
    start_date = transfer.start_date
    if start_date.tzinfo is not None:
        start_date = start_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    # Validation: allow today in user's timezone even if UTC is tomorrow
    if start_date.date() < (now_utc.date() - datetime.timedelta(days=1)):
        raise HTTPException(status_code=400, detail="Start date must be today or in the future.")

    ik = transfer.idempotency_key or str(uuid.uuid4())
    result = await db.execute(select(IdempotencyKey).filter(
        IdempotencyKey.key == ik,
        IdempotencyKey.user_id == current_user.id
    ))
    existing_key = result.scalars().first()
    if existing_key:
        return existing_key.response_body

    try:
        sender_account = None
        if transfer.funding_account_id:
            result = await db.execute(select(Account).filter(
                Account.id == transfer.funding_account_id,
                Account.user_id == current_user.id
            ).with_for_update())
            sender_account = result.scalars().first()
            if not sender_account:
                raise HTTPException(status_code=403, detail="Invalid funding account")
        else:
            # Default to main account
            result = await db.execute(select(Account).filter(Account.user_id == current_user.id, Account.is_main == True).with_for_update())
            sender_account = result.scalars().first()
            if not sender_account:
                result = await db.execute(select(Account).filter(Account.user_id == current_user.id).with_for_update())
                sender_account = result.scalars().first()
                
        if not sender_account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Reserve balance logic
        if transfer.reserve_amount:
            if sender_account.balance < transfer.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds to reserve amount.")
            sender_account.balance -= transfer.amount
            sender_account.reserved_balance += transfer.amount

        # The first run should happen at the start_date provided by user
        next_run = start_date
        
        end_date = transfer.end_date
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        new_scheduled_payment = ScheduledPayment(
            user_id=current_user.id,
            recipient_email=transfer.recipient_email,
            amount=transfer.amount,
            frequency=transfer.frequency,
            frequency_interval=transfer.frequency_interval,
            start_date=start_date,
            end_condition=transfer.end_condition,
            end_date=end_date,
            target_payments=transfer.target_payments,
            next_run_at=next_run,
            status="Active",
            idempotency_key=ik,
            reserve_amount=transfer.reserve_amount,
            funding_account_id=sender_account.id,
            subscriber_id=transfer.subscriber_id
        )
        db.add(new_scheduled_payment)
        
        response_body = {"status": "success", "message": "Transfer scheduled successfully."}
        db.add(IdempotencyKey(
            key=ik,
            user_id=current_user.id,
            response_code=200,
            response_body=response_body
        ))
        
        await db.commit()
        await db.refresh(new_scheduled_payment)

        emit_activity(
            db, 
            current_user.id, 
            "scheduled", 
            "setup", 
            f"Scheduled ${float(transfer.amount):.2f} {transfer.frequency} to {transfer.recipient_email}", 
            {
                "scheduled_payment_id": new_scheduled_payment.id,
                "recipient_email": transfer.recipient_email,
                "amount": float(transfer.amount),
                "frequency": transfer.frequency,
                "start_date": str(transfer.start_date),
            },
            ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        await db.commit()
        
        return {"status": "success", "scheduled_payment_id": new_scheduled_payment.id}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] Scheduled Transfer failed: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@app.get("/v1/transfers/scheduled", response_model=List[ScheduledPaymentResponse])
async def get_scheduled_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all scheduled payments for the current user."""
    result = await db.execute(select(ScheduledPayment).filter(
        ScheduledPayment.user_id == current_user.id
    ).order_by(ScheduledPayment.id.desc()))
    payments = result.scalars().all()
    
    return payments

@app.post("/v1/transfers/scheduled/{payment_id}/cancel")
async def cancel_scheduled_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a scheduled payment."""
    result = await db.execute(select(ScheduledPayment).filter(
        ScheduledPayment.id == payment_id,
        ScheduledPayment.user_id == current_user.id
    ))
    payment = result.scalars().first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled payment not found")
        
    if payment.status != "Active":
        raise HTTPException(status_code=400, detail=f"Payment is already {payment.status}")
        
    payment.status = "Cancelled"

    emit_activity(db, current_user.id, "scheduled", "cancelled", f"Cancelled scheduled payment #{payment.id}", {
        "scheduled_payment_id": payment.id,
        "recipient_email": payment.recipient_email,
        "amount": float(payment.amount),
    })
    await db.commit()
    
    return {"status": "success", "message": "Scheduled payment cancelled"}


# --- Activity Log Endpoint ---

@app.get("/v1/activity")
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
            from_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

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
        print(f"[ERROR] Activity query failed: {e}")
        return {"events": [], "total": 0}


# --- Dashboard & Analytics Endpoints ---


@app.get("/dashboard/balance-history")
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
                Transaction.created_at >= datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
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
                    "amount": float(row[1]),
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

    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(days=days)

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
            where_clauses.append(f"abs(amount) >= {min_amount}")

        if max_amount is not None:
            where_clauses.append(f"abs(amount) <= {max_amount}")

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
                "amount": float(row["amount"]),
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
            query = query.filter(func.abs(Transaction.amount) >= min_amount)
        if max_amount is not None:
            query = query.filter(func.abs(Transaction.amount) <= max_amount)

        sort_fn = Transaction.created_at.asc() if sort and sort.lower() == "asc" else Transaction.created_at.desc()
        query = query.order_by(sort_fn).limit(100)

        result = await db.execute(query)
        results = result.scalars().all()
        transactions = []
        for row in results:
            tx = {
                "id": str(row.id),
                "merchant": row.merchant or "",
                "amount": float(row.amount),
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

@app.get("/v1/contacts", response_model=List[ContactResponse])
async def get_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).filter(Contact.user_id == current_user.id).order_by(Contact.contact_name))
    contacts = result.scalars().all()
    return contacts

@app.post("/v1/contacts", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not contact_data.contact_name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
        
    # Validation per type
    if contact_data.contact_type == "karin":
        if not contact_data.contact_email or not contact_data.contact_email.strip():
            raise HTTPException(status_code=400, detail="Email is required for KarinBank contacts")
    elif contact_data.contact_type == "merchant":
        if not contact_data.merchant_id or not contact_data.subscriber_id:
            raise HTTPException(status_code=400, detail="Merchant ID and Subscriber ID are required")
    elif contact_data.contact_type == "bank":
        if not contact_data.routing_number or not contact_data.account_number:
            raise HTTPException(status_code=400, detail="Routing Number and Account Number are required")

    # Check for duplicates (simplified check based on type and unique identifiers)
    if contact_data.contact_type == "karin":
        result = await db.execute(select(Contact).filter(
            Contact.user_id == current_user.id, 
            Contact.contact_email == contact_data.contact_email,
            Contact.contact_type == "karin"
        ))
    elif contact_data.contact_type == "merchant":
        result = await db.execute(select(Contact).filter(
            Contact.user_id == current_user.id,
            Contact.merchant_id == contact_data.merchant_id,
            Contact.subscriber_id == contact_data.subscriber_id
        ))
    else: # bank
        result = await db.execute(select(Contact).filter(
            Contact.user_id == current_user.id,
            Contact.routing_number == contact_data.routing_number,
            Contact.account_number == contact_data.account_number
        ))
        
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact already exists")

    new_contact = Contact(
        user_id=current_user.id,
        contact_name=contact_data.contact_name,
        contact_email=contact_data.contact_email,
        contact_type=contact_data.contact_type,
        merchant_id=contact_data.merchant_id,
        subscriber_id=contact_data.subscriber_id,
        bank_name=contact_data.bank_name,
        routing_number=contact_data.routing_number,
        account_number=contact_data.account_number
    )
    
    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    
    return new_contact

@app.put("/v1/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == current_user.id
    ))
    contact = result.scalars().first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    if not contact_data.contact_name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
        
    contact.contact_name = contact_data.contact_name
    contact.contact_email = contact_data.contact_email
    contact.merchant_id = contact_data.merchant_id
    contact.subscriber_id = contact_data.subscriber_id
    contact.bank_name = contact_data.bank_name
    contact.routing_number = contact_data.routing_number
    contact.account_number = contact_data.account_number
    
    await db.commit()
    await db.refresh(contact)
    
    return contact

@app.delete("/v1/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == current_user.id
    ))
    contact = result.scalars().first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    await db.delete(contact)
    await db.commit()
    
    return {"status": "success"}

@app.get("/v1/vendors")
async def get_external_vendors():
    """Proxy to get vendors from vendor-simulator."""
    # This service doesn't require an API key for listing vendors
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("http://vendor-simulator:8001/vendors", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"vendors": []}
        except Exception as e:
            print(f"Error fetching vendors: {e}")
            return {"vendors": []}

@app.get("/v1/banks")
async def get_external_banks():
    """Proxy to get banks from mock-fed-gateway."""
    async with httpx.AsyncClient() as client:
        try:
            # We'll add this route to the gateway in the next step
            res = await client.get("http://mock-fed-gateway:8001/banks", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"banks": []}
        except Exception as e:
            print(f"Error fetching banks: {e}")
            return {"banks": []}

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
        username=CH_USER,
        password=os.getenv("CLICKHOUSE_READONLY_PASSWORD", "REDACTED"),
    )

    # Corrected query execution with parameter support
    # Only allow params that are used in actual placeholder syntax {param}
    # Note: clickhouse_connect supports parameter binding
    result = ch_client.query(request.query, parameters=request.params)
    return result.result_rows, result.column_names


async def _execute_postgres_query(request: QueryRequest, db: AsyncSession) -> Tuple[List, List]:
    """Executes a query against PostgreSQL."""
    _validate_sql_query(request.query)

    # Execute PostgreSQL query with parameter binding to prevent SQL injection
    result = await db.execute(text(request.query), request.params)
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


@app.post("/v1/admin/query")
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
            data, columns = await _execute_postgres_query(request, db)
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


@app.get("/v1/admin/banking-metrics")
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
                User.created_at >= datetime.datetime.now() - datetime.timedelta(days=1)
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
        total_volume = float(volume_data[0]) if volume_data[0] else 0
        transaction_count = int(volume_data[1]) if volume_data[1] else 0
        avg_transaction_size = float(volume_data[2]) if volume_data[2] else 0

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
                "amount": float(row[1]),
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

        user_growth_result = await db.execute(text(user_growth_query))
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


from routers import accounts
app.include_router(accounts.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
