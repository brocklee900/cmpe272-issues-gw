"""
Minimal persistence layer for processed webhook deliveries.

Uses SQLite so a delivery survives a restart and dedupe works across
process reloads. Dedupe key = GitHub's delivery id + action, so
redelivering the same event (GitHub retries on timeout/5xx) is a no-op.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "events.db"
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_events (
            dedupe_key TEXT PRIMARY KEY,
            delivery_id TEXT,
            event TEXT NOT NULL,
            action TEXT,
            issue_number INTEGER,
            payload TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )
    return conn


class EventStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                dedupe_key TEXT PRIMARY KEY,
                delivery_id TEXT,
                event TEXT NOT NULL,
                action TEXT,
                issue_number INTEGER,
                payload TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def already_processed(self, dedupe_key: str) -> bool:
        with _lock:
            cur = self._conn.execute(
                "SELECT 1 FROM webhook_events WHERE dedupe_key = ?", (dedupe_key,)
            )
            return cur.fetchone() is not None

    def record(
        self,
        dedupe_key: str,
        delivery_id: Optional[str],
        event: str,
        action: Optional[str],
        issue_number: Optional[int],
        payload: dict,
    ) -> None:
        with _lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO webhook_events
                    (dedupe_key, delivery_id, event, action, issue_number, payload, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dedupe_key,
                    delivery_id,
                    event,
                    action,
                    issue_number,
                    json.dumps(payload)[:5000],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()

    def recent(self, limit: int = 50) -> list[dict]:
        with _lock:
            cur = self._conn.execute(
                """
                SELECT dedupe_key, event, action, issue_number, timestamp
                FROM webhook_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "event": row[1],
                "action": row[2],
                "issue_number": row[3],
                "timestamp": row[4],
            }
            for row in rows
        ]


_default_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    global _default_store
    if _default_store is None:
        _default_store = EventStore()
    return _default_store
