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
from sqlalchemy.exc import SQLAlchemyError
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
from confluent_kafka import Consumer, KafkaException
from clickhouse_utils import get_ch_client, CH_DB
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sync_checker import run_sync_check
from services.transfer_service import _validate_p2p_transfer, _execute_p2p_balances, _create_p2p_transactions, _create_p2p_outbox_entries, get_vendors, execute_vendor_payment_immediate, _calculate_next_run_at

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple Bank API")

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Configuration
# Admins are defined by role="admin" in the database
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_USER = os.getenv("KAFKA_USER")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")

CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")

CORS_ORIGINS = os.getenv("CORS_ORIGINS").split(",")

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


from schemas.users import UserCreate, Token, UserResponse, NotificationResponse, UserBackupUpdate, UserPasswordUpdate, UserPreferencesUpdate
from schemas.transfers import P2PTransferRequest, PaymentRequestCreate, PaymentRequestCounter, ScheduledTransferCreate, ScheduledPaymentResponse, TransferRequest
from schemas.contacts import ContactCreate, ContactResponse, ContactUpdate
from schemas.admin import SimulationRequest, QueryRequest

# For backward compatibility with existing tests
from routers.admin import *
from routers.transfers import *
from routers.dashboard import *
from routers.contacts import *
from routers.vendors import *
from services.transfer_service import *
















# Helper Functions
# Role Checkers
admin_only = RoleChecker(["admin"])
support_only = RoleChecker(["admin", "support"])

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
ENV = os.getenv("ENV")

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


@app.on_event("startup")
async def startup_event():
    # Ensure database tables and schema exist
    try:
        # 1. Base Metadata creation (ensures tables exist)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 2. Schema Migrations (ensures columns exist, etc.)
        await run_all_migrations()
        logger.info("Database tables verified/migrated successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

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
            logger.info("Kafka producer connected successfully")
            return
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Kafka connection attempt {retry_count}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.warning(f"Failed to connect to Kafka after {max_retries} attempts. Continuing without Kafka...")
                producer = None
                return


@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        await producer.stop()



from routers import accounts
app.include_router(accounts.router)
from routers import auth
app.include_router(auth.router)
from routers import admin
app.include_router(admin.router)
from routers import transfers
app.include_router(transfers.router)
from routers import dashboard
app.include_router(dashboard.router)
from routers import contacts, vendors
app.include_router(contacts.router)
app.include_router(vendors.router)

from routers import stripe
app.include_router(stripe.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
