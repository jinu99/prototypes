"""SQLite-based lesson storage with deduplication."""
import sqlite3
import hashlib
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "lessons.db"


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            failure TEXT NOT NULL,
            resolution TEXT NOT NULL,
            rule TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            source_file TEXT,
            merge_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_fingerprint ON lessons(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_category ON lessons(category);
    """)


def _make_fingerprint(category: str, failure: str, resolution: str) -> str:
    raw = f"{category.lower().strip()}|{failure.lower().strip()}|{resolution.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def upsert_lesson(conn: sqlite3.Connection, lesson: dict) -> tuple[int, bool]:
    """Insert or merge a lesson. Returns (id, was_merged)."""
    fp = _make_fingerprint(lesson["category"], lesson["failure"], lesson["resolution"])
    existing = conn.execute(
        "SELECT id, merge_count, rule FROM lessons WHERE fingerprint = ?", (fp,)
    ).fetchone()

    if existing:
        new_count = existing["merge_count"] + 1
        merged_rule = lesson["rule"] if len(lesson["rule"]) > len(existing["rule"]) else existing["rule"]
        conn.execute(
            "UPDATE lessons SET merge_count = ?, rule = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_count, merged_rule, existing["id"]),
        )
        conn.commit()
        return existing["id"], True

    tags_json = json.dumps(lesson.get("tags", []), ensure_ascii=False)
    cur = conn.execute(
        """INSERT INTO lessons (fingerprint, category, failure, resolution, rule, tags, source_file)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (fp, lesson["category"], lesson["failure"], lesson["resolution"],
         lesson["rule"], tags_json, lesson.get("source_file", "")),
    )
    conn.commit()
    return cur.lastrowid, False


def get_all_lessons(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM lessons ORDER BY category, created_at"
    ).fetchall()
    return [dict(r) for r in rows]


def get_lesson_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
