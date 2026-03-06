"""
Centralized Activity Event Emitter + WebSocket Broadcast
Writes to the Postgres Outbox table for async Kafka → ClickHouse ingestion.
Also pushes events in real-time to connected WebSocket clients.
"""
import uuid
import datetime
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from sqlalchemy.orm import Session
from database import Outbox

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


# ─── Activity Event Emitter ─────────────────────────────────────────

def emit_activity(
    db: Session,
    user_id: int,
    category: str,
    action: str,
    title: str,
    details: dict | None = None,
):
    """
    Emit an activity event to the Outbox for async processing.
    Also broadcasts to connected WebSocket clients for instant UI updates.

    Categories: p2p, sub_account, scheduled, security, settings, cards
    Actions vary by category (e.g. sent, received, login, created, etc.)
    """
    event_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "event_id": event_id,
        "user_id": user_id,
        "category": category,
        "action": action,
        "event_time": now,
        "title": title,
        "details": json.dumps(details or {}),
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
