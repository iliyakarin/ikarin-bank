import logging
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from config import settings
from clickhouse_utils import get_ch_client
from constants import (
    NULL_UUID,
    TRANSACTION_TYPE_EXPENSE,
    TRANSACTION_STATUS_PENDING,
    ACTIVITY_DETAILS_EMPTY
)

logger = logging.getLogger(__name__)
PREPARED_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

def parse_iso_timestamp(ts_str: str) -> datetime:
    """Standardized ISO timestamp parsing with 'Z' support."""
    if not isinstance(ts_str, str):
        return ts_str
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

async def flush_batch_to_clickhouse(table: str, column_names: List[str], data: List[List[Any]]) -> bool:
    """Generic batch flusher for ClickHouse."""
    if not data:
        return True

    try:
        start_time = time.time()
        client = get_ch_client()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.insert(
                f"{settings.CLICKHOUSE_DB}.{table}",
                data,
                column_names=column_names
            )
        )
        logger.info(f"🚀 Flush to {table} completed in {time.time() - start_time:.2f}s ({len(data)} rows)")
        return True
    except Exception as e:
        logger.error(f"❌ ClickHouse flush to {table} failed: {e}")
        return False

def prepare_transaction_data(batch: List[Dict[str, Any]]) -> List[List[Any]]:
    """Transform transaction dicts into ClickHouse row format."""
    return [
        [
            msg["transaction_id"],
            msg.get("parent_id") or NULL_UUID,
            msg["account_id"],
            msg.get("sender_email") or "",
            msg.get("recipient_email") or "",
            msg["amount"],
            msg["category"],
            msg["merchant"],
            msg.get("transaction_type") or TRANSACTION_TYPE_EXPENSE,
            msg.get("transaction_side") or "",
            parse_iso_timestamp(msg["timestamp"]),
            msg.get("internal_account_last_4") or "",
            msg.get("subscriber_id"),
            msg.get("failure_reason"),
            msg.get("status") or TRANSACTION_STATUS_PENDING,
        ]
        for msg in batch
    ]

def prepare_activity_data(batch: List[Dict[str, Any]]) -> List[List[Any]]:
    """Transform activity dicts into ClickHouse row format."""
    return [
        [
            msg["event_id"],
            msg["user_id"],
            msg["category"],
            msg["action"],
            parse_iso_timestamp(msg["event_time"]),
            msg["title"],
            msg.get("details", ACTIVITY_DETAILS_EMPTY),
        ]
        for msg in batch
    ]

TRANSACTION_COLUMNS = [
    "transaction_id", "parent_id", "account_id", "sender_email", "recipient_email",
    "amount", "category", "merchant", "transaction_type", "transaction_side",
    "event_time", "internal_account_last_4", "subscriber_id", "failure_reason", "status"
]

ACTIVITY_COLUMNS = [
    "event_id", "user_id", "category", "action", "event_time", "title", "details"
]
