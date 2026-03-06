"""
Centralized Activity Event Emitter
Writes to the Postgres Outbox table for async Kafka → ClickHouse ingestion.
"""
import uuid
import datetime
import json
from sqlalchemy.orm import Session
from database import Outbox


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
