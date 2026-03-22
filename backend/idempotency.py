"""Idempotency management for financial operations.

This module provides utilities to ensure that operations (like transfers or deposits)
are not processed multiple times if the same idempotency key is used.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.transaction import IdempotencyKey

logger = logging.getLogger(__name__)

async def check_idempotency(db: AsyncSession, key: str, user_id: int) -> bool:
    """Checks if an idempotency key already exists.

    If the key does not exist, it is created and associated with the user.
    If it exists, the operation should be considered a duplicate.

    Args:
        db (AsyncSession): The database session.
        key (str): The unique idempotency key.
        user_id (int): The ID of the user performing the operation.

    Returns:
        bool: True if the key already exists (skip), False otherwise.
    """
    if not key:
        return False
        
    existing = (await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key).with_for_update()
    )).scalars().first()
    
    if existing:
        logger.info(f"Idempotency check: key '{key}' already exists for user {user_id}. Skipping operation.")
        return True
        
    db.add(IdempotencyKey(key=key, user_id=user_id))
    return False
