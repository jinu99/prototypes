"""SQLite cache for email metadata and classification results."""
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "email_classify.db"


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            sender_full TEXT,
            date TEXT,
            body_preview TEXT,
            thread_id TEXT,
            fetched_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS classifications (
            message_id TEXT PRIMARY KEY,
            category TEXT,
            importance INTEGER,
            summary TEXT,
            classified_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (message_id) REFERENCES emails(message_id)
        );
        CREATE INDEX IF NOT EXISTS idx_thread ON emails(thread_id);
        CREATE INDEX IF NOT EXISTS idx_importance ON classifications(importance);
    """)


def upsert_email(conn: sqlite3.Connection, msg_id: str, subject: str,
                 sender: str, date: str, body_preview: str, thread_id: str,
                 sender_full: str = ""):
    conn.execute("""
        INSERT INTO emails (message_id, subject, sender, sender_full, date, body_preview, thread_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            subject=excluded.subject, sender=excluded.sender,
            sender_full=excluded.sender_full,
            date=excluded.date, body_preview=excluded.body_preview,
            thread_id=excluded.thread_id
    """, (msg_id, subject, sender, sender_full, date, body_preview, thread_id))
    conn.commit()


def upsert_classification(conn: sqlite3.Connection, msg_id: str,
                          category: str, importance: int, summary: str):
    conn.execute("""
        INSERT INTO classifications (message_id, category, importance, summary)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            category=excluded.category, importance=excluded.importance,
            summary=excluded.summary, classified_at=datetime('now')
    """, (msg_id, category, importance, summary))
    conn.commit()


def get_classification(conn: sqlite3.Connection, msg_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM classifications WHERE message_id = ?", (msg_id,)
    ).fetchone()
    return dict(row) if row else None


def get_digest(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute("""
        SELECT e.message_id, e.subject, e.sender, e.sender_full, e.date, e.body_preview,
               c.category, c.importance, c.summary
        FROM emails e
        LEFT JOIN classifications c ON e.message_id = c.message_id
        ORDER BY c.importance DESC, e.date DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_thread_messages(conn: sqlite3.Connection, thread_id: str) -> list[dict]:
    rows = conn.execute("""
        SELECT e.message_id, e.subject, e.sender, e.date, e.body_preview,
               c.summary
        FROM emails e
        LEFT JOIN classifications c ON e.message_id = c.message_id
        WHERE e.thread_id = ?
        ORDER BY e.date ASC
    """, (thread_id,)).fetchall()
    return [dict(r) for r in rows]


def find_thread_by_message(conn: sqlite3.Connection, msg_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT thread_id FROM emails WHERE message_id = ?", (msg_id,)
    ).fetchone()
    return row["thread_id"] if row else None
