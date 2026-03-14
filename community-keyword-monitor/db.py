"""SQLite database layer for keyword monitor."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "monitor.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,       -- 'reddit' or 'rss'
            source_name TEXT NOT NULL,        -- subreddit name or feed URL
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            snippet TEXT,
            keyword TEXT NOT NULL,
            score INTEGER DEFAULT 0,         -- upvotes / engagement
            created_at TEXT NOT NULL,         -- ISO 8601
            collected_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(key, value)
        );

        CREATE INDEX IF NOT EXISTS idx_matches_created ON matches(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_matches_source ON matches(source_type);
    """)
    conn.commit()
    conn.close()


def insert_match(source_type: str, source_name: str, title: str,
                 url: str, snippet: str, keyword: str,
                 score: int, created_at: str) -> bool:
    """Insert a match, returns True if new, False if duplicate."""
    conn = get_conn()
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO matches
               (source_type, source_name, title, url, snippet, keyword, score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_type, source_name, title, url, snippet, keyword, score, created_at)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_matches(source_type: str | None = None,
                min_score: int = 0,
                keyword: str | None = None,
                limit: int = 100) -> list[dict]:
    conn = get_conn()
    query = "SELECT * FROM matches WHERE score >= ?"
    params: list = [min_score]

    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    if keyword:
        query += " AND keyword = ?"
        params.append(keyword)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_config(key: str) -> list[str]:
    conn = get_conn()
    rows = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchall()
    conn.close()
    return [r["value"] for r in rows]


def add_config(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def remove_config(key: str, value: str):
    conn = get_conn()
    conn.execute("DELETE FROM config WHERE key = ? AND value = ?", (key, value))
    conn.commit()
    conn.close()


def seed_defaults():
    """Seed default config if empty."""
    if not get_config("keyword"):
        for kw in ["python", "fastapi", "machine learning"]:
            add_config("keyword", kw)
    if not get_config("subreddit"):
        for sub in ["python", "programming", "machinelearning"]:
            add_config("subreddit", sub)
    if not get_config("rss_feed"):
        for feed in [
            "https://hnrss.org/newest?q=python",
            "https://news.ycombinator.com/rss",
        ]:
            add_config("rss_feed", feed)
