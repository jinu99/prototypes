"""SQLite database layer for feed relevance engine."""

import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "feed_engine.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL REFERENCES feeds(id),
            title TEXT NOT NULL,
            link TEXT UNIQUE,
            summary TEXT,
            published TEXT,
            embedding TEXT,
            relevance_score REAL DEFAULT 0.0,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS interest_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            keywords TEXT NOT NULL DEFAULT '[]',
            vector TEXT,
            feedback_count INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_articles_score
            ON articles(relevance_score DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_feed
            ON articles(feed_id);
    """)
    # Ensure interest_profile row exists
    conn.execute(
        "INSERT OR IGNORE INTO interest_profile (id, keywords) VALUES (1, '[]')"
    )
    conn.commit()
    conn.close()


def insert_feed(title: str, url: str) -> int | None:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO feeds (title, url) VALUES (?, ?)",
            (title, url),
        )
        conn.commit()
        return cur.lastrowid if cur.rowcount > 0 else None
    finally:
        conn.close()


def insert_article(
    feed_id: int,
    title: str,
    link: str | None,
    summary: str | None,
    published: str | None,
    embedding: list[float] | None = None,
) -> int | None:
    conn = get_conn()
    emb_json = json.dumps(embedding) if embedding else None
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles
               (feed_id, title, link, summary, published, embedding)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (feed_id, title, link, summary, published, emb_json),
        )
        conn.commit()
        return cur.lastrowid if cur.rowcount > 0 else None
    finally:
        conn.close()


def get_articles(limit: int = 200, offset: int = 0) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT a.id, a.title, a.link, a.summary, a.published,
                  a.relevance_score, a.feedback, f.title as feed_title
           FROM articles a JOIN feeds f ON a.feed_id = f.id
           ORDER BY a.relevance_score DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_article_count() -> int:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()
    return count


def get_article_embeddings() -> list[tuple[int, list[float]]]:
    """Return (id, embedding) pairs for all articles with embeddings."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, embedding FROM articles WHERE embedding IS NOT NULL"
    ).fetchall()
    conn.close()
    return [(r["id"], json.loads(r["embedding"])) for r in rows]


def update_scores(scores: dict[int, float]):
    conn = get_conn()
    conn.executemany(
        "UPDATE articles SET relevance_score = ? WHERE id = ?",
        [(score, aid) for aid, score in scores.items()],
    )
    conn.commit()
    conn.close()


def set_feedback(article_id: int, feedback: str):
    conn = get_conn()
    conn.execute(
        "UPDATE articles SET feedback = ? WHERE id = ?",
        (feedback, article_id),
    )
    conn.commit()
    conn.close()


def get_article_embedding(article_id: int) -> list[float] | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT embedding FROM articles WHERE id = ?", (article_id,)
    ).fetchone()
    conn.close()
    if row and row["embedding"]:
        return json.loads(row["embedding"])
    return None


def get_interest_profile() -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM interest_profile WHERE id = 1").fetchone()
    conn.close()
    if row:
        return {
            "keywords": json.loads(row["keywords"]),
            "vector": json.loads(row["vector"]) if row["vector"] else None,
            "feedback_count": row["feedback_count"],
        }
    return {"keywords": [], "vector": None, "feedback_count": 0}


def update_interest_profile(
    keywords: list[str] | None = None,
    vector: list[float] | None = None,
    feedback_count: int | None = None,
):
    conn = get_conn()
    updates = []
    params = []
    if keywords is not None:
        updates.append("keywords = ?")
        params.append(json.dumps(keywords))
    if vector is not None:
        updates.append("vector = ?")
        params.append(json.dumps(vector))
    if feedback_count is not None:
        updates.append("feedback_count = ?")
        params.append(feedback_count)
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        conn.execute(
            f"UPDATE interest_profile SET {', '.join(updates)} WHERE id = 1",
            params,
        )
        conn.commit()
    conn.close()
