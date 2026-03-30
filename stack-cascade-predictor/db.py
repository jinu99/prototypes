"""SQLite storage for status change history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).parent / "cascade.db"


def get_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS status_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id TEXT NOT NULL,
            old_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            source TEXT NOT NULL,       -- 'feed', 'simulation', 'cascade'
            cascade_from TEXT,          -- originating service (NULL if direct)
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_service
        ON status_events(service_id, timestamp)
    """)
    conn.commit()


def record_event(
    conn: sqlite3.Connection,
    service_id: str,
    old_status: str,
    new_status: str,
    source: str,
    cascade_from: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO status_events
           (service_id, old_status, new_status, source, cascade_from, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            service_id,
            old_status,
            new_status,
            source,
            cascade_from,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def get_recent_events(
    conn: sqlite3.Connection, limit: int = 50
) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM status_events ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
