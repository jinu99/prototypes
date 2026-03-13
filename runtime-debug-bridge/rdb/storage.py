"""SQLite storage for captured runtime data."""

import sqlite3
import json
import time
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".rdb" / "capture.db"


def get_db(db_path: Path | None = None, cross_thread: bool = False) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=not cross_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            pid INTEGER,
            stream TEXT NOT NULL,  -- 'stdout' or 'stderr'
            line TEXT NOT NULL,
            ts REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS http_traffic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            pid INTEGER,
            method TEXT,
            url TEXT,
            request_headers TEXT,
            request_body TEXT,
            status_code INTEGER,
            response_headers TEXT,
            response_body TEXT,
            ts REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_logs_session ON logs(session_id);
        CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
        CREATE INDEX IF NOT EXISTS idx_http_session ON http_traffic(session_id);
        CREATE INDEX IF NOT EXISTS idx_http_ts ON http_traffic(ts);
    """)


def insert_log(conn: sqlite3.Connection, session_id: str, pid: int,
               stream: str, line: str) -> None:
    conn.execute(
        "INSERT INTO logs (session_id, pid, stream, line, ts) VALUES (?, ?, ?, ?, ?)",
        (session_id, pid, stream, line, time.time()),
    )
    conn.commit()


def insert_http(conn: sqlite3.Connection, session_id: str, pid: int,
                method: str, url: str, req_headers: dict, req_body: str,
                status_code: int, resp_headers: dict, resp_body: str) -> None:
    conn.execute(
        """INSERT INTO http_traffic
           (session_id, pid, method, url, request_headers, request_body,
            status_code, response_headers, response_body, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, pid, method, url,
         json.dumps(req_headers), req_body,
         status_code, json.dumps(resp_headers), resp_body,
         time.time()),
    )
    conn.commit()


def get_recent_logs(conn: sqlite3.Connection, n: int = 50,
                    session_id: str | None = None,
                    stream: str | None = None) -> list[dict]:
    query = "SELECT * FROM logs WHERE 1=1"
    params: list = []
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if stream:
        query += " AND stream = ?"
        params.append(stream)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(n)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_recent_http(conn: sqlite3.Connection, n: int = 20,
                    session_id: str | None = None) -> list[dict]:
    query = "SELECT * FROM http_traffic WHERE 1=1"
    params: list = []
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(n)
    rows = conn.execute(query, params).fetchall()
    result = []
    for r in reversed(rows):
        d = dict(r)
        d["request_headers"] = json.loads(d["request_headers"]) if d["request_headers"] else {}
        d["response_headers"] = json.loads(d["response_headers"]) if d["response_headers"] else {}
        result.append(d)
    return result


def get_latest_session(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT session_id FROM logs ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    return row["session_id"] if row else None
