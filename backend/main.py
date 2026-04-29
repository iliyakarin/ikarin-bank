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
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from database import SessionLocal, Transaction, User, Account, Outbox, IdempotencyKey, ScheduledPayment, PaymentRequest, Contact, PaymentMethod, Base, engine
from activity import emit_activity, ws_register, ws_unregister
from security_checks import check_velocity, check_anomaly
from services.account_service import mask_account_number, decrypt_account_number
import clickhouse_connect

from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer, KafkaException
from clickhouse_utils import get_ch_client, CH_DB
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sync_checker import run_sync_check
from services.transfer_service import process_p2p_transfer, get_vendors, _calculate_next_run_at

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database migrations are managed during deployment via deploy.sh
    # to avoid race conditions between multiple API instances.
    logger.info("Database migrations managed by deployment script.")

    global producer
    max_retries = 30
    retry_count = 0
    retry_delay = 1  # seconds

    while retry_count < max_retries:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                enable_idempotence=True,
                security_protocol="SASL_PLAINTEXT",
                sasl_mechanism="PLAIN",
                sasl_plain_username=settings.KAFKA_USER,
                sasl_plain_password=settings.KAFKA_PASSWORD,
            )
            await producer.start()
            logger.info("Kafka producer connected successfully")
            break
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Kafka connection attempt {retry_count}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.warning(f"Failed to connect to Kafka after {max_retries} attempts. Continuing without Kafka...")
                producer = None
                break

    yield

    if producer:
        await producer.stop()
        logger.info("Kafka producer stopped")

app = FastAPI(title="KarinBank API", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


from config import settings

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")

    if request.url.path == "/v1/transactions" and response.status_code == 200:
        # We can't easily read the body here without exhausting it,
        # but we can log that we are returning transactions.
        pass
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Auth Configuration
from auth_utils import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    pwd_context, oauth2_scheme, verify_password, get_password_hash,
    create_access_token, get_db, get_current_user, RoleChecker
)


from schemas.users import UserCreate, Token, UserResponse, NotificationResponse, UserBackupUpdate, UserPasswordUpdate, UserPreferencesUpdate
from schemas.transfers import P2PTransferRequest, PaymentRequestCreate, PaymentRequestCounter, ScheduledTransferCreate, ScheduledPaymentResponse, TransferRequest
from schemas.contacts import ContactCreate, ContactResponse, ContactUpdate
from schemas.admin import SimulationRequest, QueryRequest

# Router Inclusions
from routers import admin, transfers, dashboard, contacts, vendors, auth, deposit, accounts

app.include_router(accounts.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
app.include_router(transfers.router, prefix="/v1")
app.include_router(dashboard.router, prefix="/v1")
app.include_router(contacts.router, prefix="/v1")
app.include_router(vendors.router, prefix="/v1")
app.include_router(deposit.router, prefix="/v1")
















# Helper Functions
# Role Checkers
admin_only = RoleChecker(["admin"])
support_only = RoleChecker(["admin", "support"])

from turnstile import verify_turnstile


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



# --- WebSocket Endpoint ---


# app already defined above



# Main entry point (moved router inclusions up)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
