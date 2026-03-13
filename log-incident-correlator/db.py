"""SQLite storage for log templates, first-seen times, and deploy events."""

import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).parent / "correlator.db"


def get_connection(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS log_templates (
            cluster_id  INTEGER PRIMARY KEY,
            template    TEXT NOT NULL,
            first_seen  TEXT NOT NULL,
            last_seen   TEXT NOT NULL,
            count       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS deploy_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            commit_hash TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS correlations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            deploy_id       INTEGER REFERENCES deploy_events(id),
            cluster_id      INTEGER REFERENCES log_templates(cluster_id),
            time_delta_sec  REAL,
            window_minutes  INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_templates_first_seen ON log_templates(first_seen);
        CREATE INDEX IF NOT EXISTS idx_deploy_timestamp ON deploy_events(timestamp);
    """)
    conn.commit()


def upsert_template(conn: sqlite3.Connection, cluster_id: int, template: str,
                    timestamp: str) -> bool:
    """Insert or update a template. Returns True if it was first-seen (new)."""
    row = conn.execute(
        "SELECT cluster_id FROM log_templates WHERE cluster_id = ?",
        (cluster_id,)
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO log_templates (cluster_id, template, first_seen, last_seen, count) "
            "VALUES (?, ?, ?, ?, 1)",
            (cluster_id, template, timestamp, timestamp)
        )
        return True
    else:
        conn.execute(
            "UPDATE log_templates SET last_seen = ?, count = count + 1, template = ? "
            "WHERE cluster_id = ?",
            (timestamp, template, cluster_id)
        )
        return False


def insert_deploy_event(conn: sqlite3.Connection, timestamp: str,
                        commit_hash: str = "", description: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO deploy_events (timestamp, commit_hash, description) VALUES (?, ?, ?)",
        (timestamp, commit_hash, description)
    )
    return cur.lastrowid


def insert_correlation(conn: sqlite3.Connection, deploy_id: int,
                       cluster_id: int, time_delta_sec: float,
                       window_minutes: int) -> None:
    conn.execute(
        "INSERT INTO correlations (deploy_id, cluster_id, time_delta_sec, window_minutes) "
        "VALUES (?, ?, ?, ?)",
        (deploy_id, cluster_id, time_delta_sec, window_minutes)
    )


def get_all_templates(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT cluster_id, template, first_seen, last_seen, count FROM log_templates "
        "ORDER BY first_seen"
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_deploys(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, timestamp, commit_hash, description FROM deploy_events "
        "ORDER BY timestamp"
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_correlations(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT c.id, c.deploy_id, c.cluster_id, c.time_delta_sec, c.window_minutes,
               d.timestamp as deploy_time, d.commit_hash, d.description as deploy_desc,
               t.template, t.first_seen
        FROM correlations c
        JOIN deploy_events d ON c.deploy_id = d.id
        JOIN log_templates t ON c.cluster_id = t.cluster_id
        ORDER BY d.timestamp, t.first_seen
    """).fetchall()
    return [dict(r) for r in rows]
