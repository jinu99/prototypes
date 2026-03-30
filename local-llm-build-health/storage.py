"""SQLite storage for benchmark results."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "benchmarks.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            build_ok INTEGER NOT NULL,  -- 1=success, 0=fail
            error_msg TEXT,
            built_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bench_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            build_id INTEGER NOT NULL REFERENCES builds(id),
            tag TEXT NOT NULL,
            model TEXT NOT NULL,
            test_name TEXT NOT NULL,
            n_prompt INTEGER,
            n_gen INTEGER,
            tok_s_prompt REAL,
            tok_s_gen REAL,
            mem_mb REAL,
            raw_json TEXT,
            recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bench_tag ON bench_results(tag);
        CREATE INDEX IF NOT EXISTS idx_bench_recorded ON bench_results(recorded_at);
    """)


def save_build(conn: sqlite3.Connection, tag: str, success: bool, error_msg: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO builds (tag, build_ok, error_msg, built_at) VALUES (?, ?, ?, ?)",
        (tag, int(success), error_msg, datetime.now().isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def save_bench_result(conn: sqlite3.Connection, build_id: int, tag: str, result: dict):
    conn.execute(
        """INSERT INTO bench_results
           (build_id, tag, model, test_name, n_prompt, n_gen,
            tok_s_prompt, tok_s_gen, mem_mb, raw_json, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            build_id, tag,
            result.get("model", "unknown"),
            result.get("test", "default"),
            result.get("n_prompt", 0),
            result.get("n_gen", 0),
            result.get("tok_s_prompt", 0.0),
            result.get("tok_s_gen", 0.0),
            result.get("mem_mb", 0.0),
            json.dumps(result),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()


def get_history(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    rows = conn.execute("""
        SELECT tag, model, test_name, n_prompt, n_gen,
               tok_s_prompt, tok_s_gen, mem_mb, recorded_at
        FROM bench_results
        ORDER BY recorded_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_tags(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT tag FROM bench_results ORDER BY recorded_at"
    ).fetchall()
    return [r["tag"] for r in rows]


def get_results_by_tag(conn: sqlite3.Connection, tag: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM bench_results WHERE tag = ? ORDER BY recorded_at",
        (tag,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_builds(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM builds ORDER BY built_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]
