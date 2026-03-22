"""Shared outbox processing service used by both workers."""
import json
import asyncio
import logging
from cryptography.fernet import Fernet
from datetime import datetime, timezone
from typing import AsyncIterator

from aiokafka import AIOKafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import Outbox, Transaction

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = {
    "sender_email", "recipient_email", "target_email", "email", 
    "first_name", "last_name", "ip", "user_agent"
}

def encrypt_payload(payload: dict, key: str) -> dict:
    """Recursively encrypt sensitive fields in a dictionary."""
    cipher = Fernet(key.encode())
    encrypted_payload = payload.copy()
    
    for k, v in encrypted_payload.items():
        if k in SENSITIVE_FIELDS and v and isinstance(v, str):
            encrypted_payload[k] = f"enc_{cipher.encrypt(v.encode()).decode()}"
        elif isinstance(v, dict):
            encrypted_payload[k] = encrypt_payload(v, key)
            
    return encrypted_payload

class ProducerManager:
    _instance = None
    _initialized = False
    _producer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_producer(self) -> AIOKafkaProducer:
        if not self._initialized or self._producer is None:
            await self._create_producer()
        return self._producer

    async def _create_producer(self) -> None:
        from config import settings
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            enable_idempotence=True,
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="PLAIN",
            sasl_plain_username=settings.KAFKA_USER,
            sasl_plain_password=settings.KAFKA_PASSWORD,
            acks="all",
            request_timeout_ms=settings.KAFKA_REQUEST_TIMEOUT_MS,
            retry_backoff_ms=settings.KAFKA_RETRY_BACKOFF_MS or 100,
            retries=settings.KAFKA_MAX_RETRIES or 3,
        )
        await self._producer.start()
        self._initialized = True

    async def close(self) -> None:
        if self._producer is not None:
            try:
                await self._producer.stop(timeout=5)
            except Exception:
                pass
            self._producer = None
            self._initialized = False

_manager = ProducerManager()

async def send_to_kafka(session: AsyncSession, event: Outbox) -> bool:
    """Process a single outbox event."""
    from config import settings
    producer = await _manager.get_producer()

    try:
        target_topic = settings.KAFKA_ACTIVITY_TOPIC if event.event_type == "activity_event" else settings.KAFKA_TOPIC
        payload_data = event.payload or {}
        encrypted_payload = encrypt_payload(payload_data, settings.KAFKA_MESSAGE_ENCRYPTION_KEY)
        
        tx_id = payload_data.get("transaction_id")
        key = payload_data.get("outbox_id", f"{event.id}").encode("utf-8")

        message = json.dumps(encrypted_payload).encode("utf-8")
        future = producer.send_and_wait(
            target_topic, message,
            key=key if key and len(key) < 1000 else None
        )
        await asyncio.wait_for(future, timeout=settings.KAFKA_REQUEST_TIMEOUT_MS / 1000)

        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)

        if tx_id:
            tx = (await session.execute(select(Transaction).where(Transaction.id == tx_id))).scalars().first()
            if tx:
                tx.status = "sent_to_kafka"

        await session.commit()
        return True
    except Exception as e:
        await _fail_event(session, event, str(e))
        return False

async def _fail_event(session: AsyncSession, event: Outbox, reason: str) -> None:
    from config import settings
    dlq_topic = settings.KAFKA_DLQ_TOPIC
    if dlq_topic:
        producer = await _manager.get_producer()
        try:
            dlq_message = {
                "original_event_id": event.id, "event_type": event.event_type,
                "error": reason[:500], "payload": json.dumps(event.payload) if event.payload else None
            }
            key = str(event.id).encode("utf-8")
            await producer.send_and_wait(dlq_topic, json.dumps(dlq_message).encode("utf-8"), key=key)
        except Exception:
            pass

    event.status = "failed"
    event.error_message = reason[:500]
    await session.commit()

async def cleanup_producer() -> None:
    if _manager._producer is not None:
        await _manager.close()

__all__ = ["send_to_kafka", "cleanup_producer"]
