"""Tiny persistent dedup ledger.

Recurring events (salary, rent, insurance) are keyed by a deterministic string
like "rent-2026-08" so a container restart mid-month never fires them twice.
This is local state for the simulator only - it is not part of karin-bank's
own idempotency-key system (backend/idempotency.py), which some of the calls
this service makes also go through independently.
"""
import datetime
import sqlite3
from pathlib import Path
from typing import List, Dict


class EventState:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS events (key TEXT PRIMARY KEY, done_at TEXT NOT NULL)"
        )
        self._conn.commit()

    def is_done(self, key: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM events WHERE key = ?", (key,)).fetchone()
        return row is not None

    def mark_done(self, key: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO events (key, done_at) VALUES (?, ?)",
            (key, datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        self._conn.commit()

    def recent(self, limit: int = 20) -> List[Dict[str, str]]:
        rows = self._conn.execute(
            "SELECT key, done_at FROM events ORDER BY done_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"key": k, "done_at": d} for k, d in rows]
