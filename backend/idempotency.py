"""Idempotency management for financial operations.

Two-phase protocol:
  Phase 1 — check_idempotency(db, key, user_id) → dict | None
    - First call:  inserts key with status='pending', returns None (proceed)
    - Repeat call: if status='completed', returns the saved response body
    - In-flight:   if status='pending', returns None (let caller decide)

  Phase 2 — complete_idempotency(db, key, response_body)
    - Marks the key as completed and stores the response so replays get it back
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.transaction import IdempotencyKey

logger = logging.getLogger(__name__)


async def check_idempotency(db: AsyncSession, key: str, user_id: int) -> Optional[dict]:
    """Phase 1: check whether this key has already been processed.

    Returns the saved response body if the operation completed previously,
    or None if the operation should proceed.
    """
    if not key:
        return None

    existing = (await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key).with_for_update()
    )).scalars().first()

    if existing:
        if existing.status == "completed" and existing.response_body is not None:
            logger.info(f"Idempotency hit: key '{key}' completed for user {user_id}. Returning saved response.")
            return existing.response_body
        logger.info(f"Idempotency hit: key '{key}' exists (status={existing.status}) for user {user_id}.")
        return None

    db.add(IdempotencyKey(key=key, user_id=user_id, status="pending"))
    return None


async def complete_idempotency(db: AsyncSession, key: str, response_body: dict) -> None:
    """Phase 2: mark the key as completed and store the response.

    Should be called after a successful operation so that replayed requests
    receive the original response.
    """
    if not key:
        return

    existing = (await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key).with_for_update()
    )).scalars().first()

    if existing:
        existing.status = "completed"
        existing.response_body = response_body
