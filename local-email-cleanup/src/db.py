"""SQLite database layer for email header caching."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "emails.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    uid TEXT PRIMARY KEY,
    mailbox TEXT NOT NULL,
    sender TEXT NOT NULL,
    sender_name TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    date TEXT,
    date_ts INTEGER,
    is_read INTEGER DEFAULT 0,
    size INTEGER DEFAULT 0,
    has_attachment INTEGER DEFAULT 0,
    list_unsubscribe TEXT DEFAULT '',
    x_mailer TEXT DEFAULT '',
    precedence TEXT DEFAULT '',
    content_type TEXT DEFAULT '',
    category TEXT DEFAULT '',
    fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sender ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_category ON emails(category);
CREATE INDEX IF NOT EXISTS idx_date_ts ON emails(date_ts);
CREATE INDEX IF NOT EXISTS idx_mailbox ON emails(mailbox);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def upsert_emails(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert or replace email records. Returns count inserted."""
    if not rows:
        return 0
    sql = """
    INSERT OR REPLACE INTO emails
        (uid, mailbox, sender, sender_name, subject, date, date_ts,
         is_read, size, has_attachment, list_unsubscribe, x_mailer,
         precedence, content_type, category)
    VALUES
        (:uid, :mailbox, :sender, :sender_name, :subject, :date, :date_ts,
         :is_read, :size, :has_attachment, :list_unsubscribe, :x_mailer,
         :precedence, :content_type, :category)
    """
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def update_category(conn: sqlite3.Connection, uid: str, category: str) -> None:
    conn.execute("UPDATE emails SET category = ? WHERE uid = ?", (category, uid))


def get_all_emails(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM emails ORDER BY date_ts DESC").fetchall()


def get_email_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]


def get_sender_stats(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Aggregate stats per sender."""
    sql = """
    SELECT
        sender,
        MAX(sender_name) as sender_name,
        COUNT(*) as total,
        SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
        ROUND(100.0 * SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as unread_pct,
        MAX(date) as last_date,
        SUM(size) as total_size,
        GROUP_CONCAT(DISTINCT category) as categories
    FROM emails
    GROUP BY sender
    ORDER BY total DESC
    """
    return conn.execute(sql).fetchall()


def get_category_summary(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    sql = """
    SELECT
        category,
        COUNT(*) as total,
        SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
        SUM(size) as total_size
    FROM emails
    GROUP BY category
    ORDER BY total DESC
    """
    return conn.execute(sql).fetchall()


def get_emails_by_category(conn: sqlite3.Connection, category: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM emails WHERE category = ? ORDER BY date_ts DESC",
        (category,),
    ).fetchall()


def get_cleanup_candidates(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get emails that are candidates for cleanup (newsletter, marketing, old)."""
    sql = """
    SELECT * FROM emails
    WHERE category IN ('newsletter', 'marketing', 'notification', 'old')
    ORDER BY category, sender, date_ts DESC
    """
    return conn.execute(sql).fetchall()


def delete_emails(conn: sqlite3.Connection, uids: list[str]) -> int:
    if not uids:
        return 0
    placeholders = ",".join("?" for _ in uids)
    conn.execute(f"DELETE FROM emails WHERE uid IN ({placeholders})", uids)
    conn.commit()
    return len(uids)
