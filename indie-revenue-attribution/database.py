"""SQLite database setup and models."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        stripe_payment_id TEXT UNIQUE NOT NULL,
        amount_cents INTEGER NOT NULL,
        currency TEXT DEFAULT 'usd',
        customer_email TEXT,
        customer_id TEXT,
        product_name TEXT,
        created_at TEXT NOT NULL,
        matched_session_id TEXT,
        matched_channel TEXT
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        visitor_id TEXT,
        utm_source TEXT,
        utm_medium TEXT,
        utm_campaign TEXT,
        utm_content TEXT,
        referrer TEXT,
        landing_page TEXT,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        country TEXT,
        device TEXT
    );

    CREATE TABLE IF NOT EXISTS channel_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel TEXT UNIQUE NOT NULL,
        ad_spend REAL DEFAULT 0,
        tool_cost REAL DEFAULT 0,
        hours_spent REAL DEFAULT 0,
        hourly_rate REAL DEFAULT 50,
        period TEXT DEFAULT '2026-03'
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON sessions(visitor_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
    CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at);
    """)
    conn.commit()
    conn.close()
