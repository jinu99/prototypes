"""SQLite audit log for all transaction attempts."""

import sqlite3
import time
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            api_pattern TEXT NOT NULL,
            method TEXT NOT NULL,
            url TEXT NOT NULL,
            amount REAL,
            currency TEXT,
            decision TEXT NOT NULL,
            reason TEXT,
            pii_detected TEXT,
            request_body TEXT,
            response_status INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def log_transaction(
    api_pattern: str,
    method: str,
    url: str,
    amount: float | None,
    currency: str | None,
    decision: str,
    reason: str = "",
    pii_detected: list[str] | None = None,
    request_body: str = "",
    response_status: int | None = None,
):
    conn = get_connection()
    conn.execute(
        """INSERT INTO transactions
           (timestamp, api_pattern, method, url, amount, currency,
            decision, reason, pii_detected, request_body, response_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            time.time(),
            api_pattern,
            method,
            url,
            amount,
            currency,
            decision,
            reason,
            json.dumps(pii_detected) if pii_detected else None,
            request_body,
            response_status,
        ),
    )
    conn.commit()
    conn.close()


def get_daily_total() -> float:
    """Get total approved spending for today."""
    conn = get_connection()
    today_start = time.time() - (time.time() % 86400)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM transactions "
        "WHERE decision = 'approved' AND timestamp >= ?",
        (today_start,),
    ).fetchone()
    conn.close()
    return row["total"]


def get_monthly_total() -> float:
    """Get total approved spending for this month."""
    conn = get_connection()
    import datetime
    now = datetime.datetime.now()
    month_start = datetime.datetime(now.year, now.month, 1).timestamp()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM transactions "
        "WHERE decision = 'approved' AND timestamp >= ?",
        (month_start,),
    ).fetchone()
    conn.close()
    return row["total"]


def get_recent_transactions(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize DB on import
init_db()
