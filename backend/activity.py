"""
Centralized Activity Event Emitter + WebSocket Broadcast
Writes to the Postgres Outbox table for async Kafka → ClickHouse ingestion.
Also pushes events in real-time to connected WebSocket clients.
"""
import uuid
import datetime
from datetime import timezone, timedelta
import json
import asyncio
import re
from typing import Dict, Set
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from database import SessionLocal
from models.management import Outbox
from constants import (
    ACTIVITY_DETAILS_EMPTY,
    TRANSACTION_TYPE_TRANSFER,
    TRANSACTION_SIDE_DEBIT
)

# ─── WebSocket Connection Registry ──────────────────────────────────
# Maps user_id → set of connected WebSocket instances
_ws_connections: Dict[int, Set[WebSocket]] = {}


def ws_register(user_id: int, ws: WebSocket):
    """Register a WebSocket connection for a user."""
    if user_id not in _ws_connections:
        _ws_connections[user_id] = set()
    _ws_connections[user_id].add(ws)


def ws_unregister(user_id: int, ws: WebSocket):
    """Remove a WebSocket connection for a user."""
    if user_id in _ws_connections:
        _ws_connections[user_id].discard(ws)
        if not _ws_connections[user_id]:
            del _ws_connections[user_id]


async def broadcast_to_user(user_id: int, payload: dict):
    """Push an activity event to all connected WebSocket clients for a user."""
    connections = _ws_connections.get(user_id, set()).copy()
    dead = []
    for ws in connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    # Clean up dead connections
    for ws in dead:
        ws_unregister(user_id, ws)


# ─── PII Scrubbing Helpers ──────────────────────────────────────────

def _mask_email(match):
    """Regex callback to mask an email."""
    email = match.group(0)
    user, domain = email.split("@")
    if len(user) <= 1:
        return f"*@{domain}"
    return f"{user[0]}***@{domain}"

def _mask_pii(text: str) -> str:
    """Masks emails and potential names in a string."""
    if not text:
        return text
    # Mask emails
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    text = re.sub(email_pattern, _mask_email, text)
    return text

def _scrub_details(details: dict | None) -> dict:
    """Scrub PII from a details dictionary."""
    if not details:
        return json.loads(ACTIVITY_DETAILS_EMPTY)
    scrubbed = details.copy()
    for key in ["email", "recipient_email", "sender_email", "target_email", "first_name", "last_name", "full_name"]:
        if key in scrubbed and scrubbed[key] and isinstance(scrubbed[key], str):
            if "@" in scrubbed[key]:
                scrubbed[key] = f"{scrubbed[key][0]}***@{scrubbed[key].split('@')[1]}"
            else:
                scrubbed[key] = f"{scrubbed[key][0]}***"
    return scrubbed

def emit_activity(
    db: AsyncSession,
    user_id: int,
    category: str,
    action: str,
    title: str,
    details: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
):
    """
    Emit an activity event to the Outbox for async processing.
    Also broadcasts to connected WebSocket clients for instant UI updates.

    Categories: p2p, sub_account, scheduled, security, settings, cards
    Actions vary by category (e.g. sent, received, login, created, etc.)
    """
    event_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Scrub PII from title and details
    scrubbed_title = _mask_pii(title)
    scrubbed_details = _scrub_details(details)

    payload = {
        "event_id": event_id,
        "user_id": user_id,
        "category": category,
        "action": action,
        "event_time": now,
        "title": scrubbed_title,
        "details": json.dumps(scrubbed_details),
        "ip": ip,
        "user_agent": user_agent,
    }

    outbox_entry = Outbox(
        event_type="activity_event",
        payload=payload,
    )
    db.add(outbox_entry)
    # Don't commit here — caller is responsible for committing the transaction
    # so the activity event is atomic with the business operation.

    # Schedule WebSocket broadcast (fire-and-forget, non-blocking)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_to_user(user_id, payload))
    except RuntimeError:
        # No running event loop (e.g. called from sync context) — skip WS push
        pass


def emit_transaction_status_update(
    db: AsyncSession,
    transaction_id: str,
    account_id: int,
    status: str,
    amount: int, # Amount in cents
    category: str,
    merchant: str,
    transaction_type: str = TRANSACTION_TYPE_TRANSFER,
    transaction_side: str = TRANSACTION_SIDE_DEBIT,
    sender_email: str | None = None,
    recipient_email: str | None = None,
    internal_account_last_4: str | None = None,
    commentary: str | None = None,
    failure_reason: str | None = None,
):
    """
    Emits a status update for an existing transaction to the Outbox.
    This creates a NEW row in ClickHouse with the same transaction_id but a new timestamp,
    preserving historical status changes as requested.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    payload = {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "amount": amount,
        "category": category,
        "merchant": merchant,
        "transaction_type": transaction_type,
        "transaction_side": transaction_side,
        "status": status,
        "timestamp": now,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "internal_account_last_4": internal_account_last_4,
        "commentary": commentary,
        "failure_reason": failure_reason,
    }

    outbox_entry = Outbox(
        event_type="transaction.status_update",
        payload=payload,
    )
    db.add(outbox_entry)
