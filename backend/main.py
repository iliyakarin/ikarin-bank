import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to Python path so v2 package is importable
# When running from backend/ directory, parent is the project root
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config import settings
from database import engine, SessionLocal
from models.user import User
from routers import (
    auth, accounts, admin, transfers, dashboard, contacts, vendors, deposit, fed_gateway_v2
)
from activity import ws_register, ws_unregister
from auth_utils import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from sqlalchemy import select

from v2.fed_gateway.transport.mq_client import MQClient
from v2.fed_gateway.engine.settlement import SettlementEngine
from v2.fed_gateway.gateway import FedGatewayHost

logger = logging.getLogger(__name__)

producer: AIOKafkaProducer = None
fed_gateway_host: FedGatewayHost = None
mq_client: MQClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer, fed_gateway_host, mq_client
    logger.info("Starting KarinBank API...")

    await init_kafka()

    mq_client = MQClient()
    await mq_client.start()

    settlement_engine = SettlementEngine()
    fed_gateway_host = FedGatewayHost(mq_client, settlement_engine)
    gateway_task = asyncio.create_task(fed_gateway_host.start())

    try:
        yield
    finally:
        logger.info("Shutting down KarinBank API...")
        await fed_gateway_host.stop()
        gateway_task.cancel()
        await mq_client.stop()
        if producer:
            await producer.stop()
            logger.info("Kafka producer stopped")
        await engine.dispose()
        logger.info("Database engine disposed")

async def init_kafka():
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
    logger.error("❌ Failed to connect to Kafka. Application will continue without Kafka producer.")
    producer = None

app = FastAPI(
    title="KarinBank API",
    version="2.0.0",
    description="Secured and refactored KarinBank Core API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

from middleware import CspNonceMiddleware
app.add_middleware(CspNonceMiddleware)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"➡️ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"⬅️ Response: {response.status_code}")
    return response

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0", "gateway_v2": "running"}

# Include V1 Routers
api_v1_prefix = "/v1"
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(accounts.router, prefix=api_v1_prefix)
app.include_router(admin.router, prefix=api_v1_prefix)
app.include_router(transfers.router, prefix=api_v1_prefix)
app.include_router(dashboard.router, prefix=api_v1_prefix)
app.include_router(contacts.router, prefix=api_v1_prefix)
app.include_router(vendors.router, prefix=api_v1_prefix)
app.include_router(deposit.router, prefix=api_v1_prefix)

# Include V2 Gateway Router
app.include_router(fed_gateway_v2.router, prefix="/v2")
