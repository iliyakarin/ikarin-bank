"""Main entry point for the KarinBank API.

This module initializes the FastAPI application, configures middleware,
manages external service connections (Kafka, Database), and includes
all API routers.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaProducer

from config import settings
from database import engine, SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction
from models.management import Outbox
from routers import (
    admin, transfers, dashboard, contacts, 
    vendors, auth, deposit, accounts
)
from activity import ws_register, ws_unregister, broadcast_to_user
from auth_utils import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from sqlalchemy import select

# Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global Kafka Producer
producer: AIOKafkaProducer | None = None

async def init_kafka():
    """Initialize the Kafka producer in the background."""
    global producer
    max_retries = 30
    retry_delay = 1
    
    for i in range(max_retries):
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
            logger.info("✅ Kafka producer connected successfully")
            return
        except Exception as e:
            logger.warning(f"⚠️ Kafka connection attempt {i+1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            
    logger.error("❌ Failed to connect to Kafka after multiple attempts. Application will continue without Kafka producer.")
    producer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application lifecycle.

    Handles startup (Kafka initialization) and shutdown (cleanup) tasks.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    # Startup
    logger.info("🚀 Starting KarinBank API...")
    
    # Initialize Kafka (non-blocking if we wrap it in a task, but lifespan is intended for blocking init)
    # We choose to block slightly to ensure Kafka is ready for the first request if possible.
    await init_kafka()
    
    yield
    
    # Shutdown
    if producer:
        await producer.stop()
        logger.info("🛑 Kafka producer stopped")
    
    await engine.dispose()
    logger.info("🛑 Database engine disposed")

# FastAPI App Initialization
app = FastAPI(
    title="KarinBank API",
    version="2.0.0",
    description="Secured and refactored KarinBank Core API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware for logging HTTP requests and responses.

    Args:
        request (Request): The incoming FastAPI request.
        call_next (Callable): The next call in the middleware chain.

    Returns:
        Response: The HTTP response from the application.
    """
    logger.info(f"➡️ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"⬅️ Response: {response.status_code}")
    return response

# Standard Health Check
@app.get("/health")
async def health_check():
    """Simple health check endpoint to verify service availability.

    Returns:
        dict: A status message and version number.
    """
    return {"status": "ok", "version": "2.0.0"}

# Include Routers with V1 Prefix
api_v1_prefix = "/v1"
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(accounts.router, prefix=api_v1_prefix)
app.include_router(admin.router, prefix=api_v1_prefix)
app.include_router(transfers.router, prefix=api_v1_prefix)
app.include_router(dashboard.router, prefix=api_v1_prefix)
app.include_router(contacts.router, prefix=api_v1_prefix)
app.include_router(vendors.router, prefix=api_v1_prefix)
app.include_router(deposit.router, prefix=api_v1_prefix)

# WebSocket Activity
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/activity/{token}")
async def ws_activity(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time activity updates."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            await websocket.close(code=4001)
            return

    await websocket.accept()
    ws_register(user.id, websocket)

    try:
        while True:
            # Wait for client messages or keepalive
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_unregister(user.id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
